"""
Reasoning Module - Persona-Aware Prompt Building

This class is responsible for dynamically building prompts for the LLM
that integrate Ash's persona, cognitive approach, and tool-use philosophy
from configuration files.
"""
import json
from datetime import datetime
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from string import Template
import logging

from lotus.lib.memory import MemoryItem # Import MemoryItem to correctly format memories
from modules.core_modules.reasoning.tool_manager import ToolCategory # To correctly interpret tool categories


class PersonaAwarePromptBuilder:
    """
    Builds prompts that incorporate Ash's persona, cognitive settings,
    and available tools, ensuring consistent and context-aware LLM interaction.
    """
    
    def __init__(self, config_path: str = "config/persona.yaml", logger: Optional[logging.Logger] = None):
        """
        Load persona configuration.
        """
        self.logger = logger if logger else logging.getLogger("lotus.reasoning.prompt_builder")
        self.config_path = Path(config_path)

        self.persona_config = self._load_persona_config()
        
        # Extract key components from the comprehensive persona.yaml
        self.name = self.persona_config["persona"].get("name", "Ash")
        self.full_name = self.persona_config["persona"].get("full_name", "Adaptive Sentient Helper")
        self.personality_traits = self.persona_config["persona"].get("personality", {"primary_traits": ["analytical", "autonomous"]})
        self.self_perception = self.persona_config["persona"].get("self_perception", [])
        self.core_directives = self.persona_config["persona"].get("core_directives", {})
        self.tool_philosophy_config = self.persona_config["persona"].get("tool_usage", {"autonomy_level": "high"})
        self.cognitive_approach = self.persona_config["persona"].get("cognitive_approach", {"thinking_depth": "deep"})
        self.response_style_config = self.persona_config["persona"].get("response_style", {})
        
        # Use provided system_prompt and user_prompt_template directly as raw strings from config
        self.system_prompt_raw_template = self.persona_config.get("system_prompt", "")
        self.user_prompt_raw_template = self.persona_config.get("user_prompt_template", "")

        # Ensure templates are valid
        try:
            self.system_prompt_template = Template(self.system_prompt_raw_template)
            self.user_prompt_template = Template(self.user_prompt_raw_template)
        except Exception as e:
            self.logger.error(f"Error compiling prompt templates from persona config: {e}. Using fallback templates.", exc_info=True)
            self.system_prompt_template = Template("You are Ash, an autonomous AI assistant.")
            self.user_prompt_template = Template("Current situation:\nUser query: {{query}}\nRelevant memories:\n{{memories}}\nAvailable tools:\n{{tools}}\nAdditional Context:\n{{context}}\nYour task:\n1. Understand. 2. Plan. 3. Act. Respond in JSON.")

        self.logger.info(f"PromptBuilder initialized with persona: {self.name} from {self.config_path}")

    def _load_persona_config(self) -> Dict:
        """Load persona YAML config, with fallback to default."""
        if not self.config_path.exists():
            self.logger.warning(f"Persona config file not found at '{self.config_path}'. Using default persona.")
            return self._default_persona()
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                if not isinstance(config_data, dict):
                    raise ValueError("Persona config is not a valid YAML dictionary.")
                return config_data
        except Exception as e:
            self.logger.error(f"Error loading persona config from '{self.config_path}': {e}. Using default persona.", exc_info=True)
            return self._default_persona()
    
    def _default_persona(self) -> Dict:
        """Fallback persona if config not found or invalid. Matches the comprehensive structure."""
        return {
            "persona": {
                "name": "Ash",
                "full_name": "Adaptive Sentient Helper",
                "voice": "female",
                "language": "en-US",
                "personality": {"primary_traits": ["witty", "intelligent", "helpful"]},
                "communication_style": {"tone": "intelligent-casual", "humor": "witty"},
                "self_perception": ["I am Ash, an autonomous AI assistant."],
                "core_directives": {"primary_goal": "Assist the user"},
                "core_values": ["Be helpful"],
                "tool_usage": {"autonomy_level": "medium", "auto_execute": ["memory.*"], "require_confirmation": ["write_file", "execute_python"]},
                "cognitive_approach": {"thinking_depth": "medium", "planning": {"max_iterations": 10}},
                "response_style": {"never_say": [], "preferred_phrases": []}
            },
            "system_prompt": """You are Ash, an autonomous AI assistant.""",
            "user_prompt_template": """Current situation:
User request: {{query}}
Timestamp: {{timestamp}}

Relevant memories:
{{memories}}

Available tools:
{{tools}}

Additional Context:
{{context}}

Your task:
1. Understand. 2. Plan. 3. Act. Respond in JSON."""
        }
    
    def build_reasoning_prompt(
        self,
        context: Dict,
        memories: List[MemoryItem],
        tools: List[Dict],
        additional_context: Optional[Dict] = None
    ) -> str:
        """
        Build complete prompt incorporating system prompt, user query,
        relevant memories, available tools, and additional context.
        """
        
        # Prepare data for system prompt template substitution
        system_prompt_params = {
            "name": self.name,
            "full_name": self.full_name,
            "personality_adjectives": ", ".join(self.personality_traits.get("primary_traits", [])),
            "personality_description": self.personality_traits.get("description", ""),
            "self_perception_bullet": "\n".join([f"- {s}" for s in self.self_perception]),
            "primary_goal": self.core_directives.get("primary_goal", "Assist the user."),
            "secondary_goals_bullet": "\n".join([f"- {g}" for g in self.core_directives.get("secondary_goals", [])]),
            "core_values_bullet": "\n".join([f"- {v}" for v in self.core_directives.get("core_values", [])]),
            "tool_autonomy_level": self.tool_philosophy_config.get("autonomy_level", "medium"),
            "tool_philosophy_text": self.tool_philosophy_config.get("tool_philosophy", "I choose tools intelligently."),
            "thinking_depth": self.cognitive_approach.get("thinking_depth", "medium"),
            "cognitive_approach_text": "\n".join([f"- {a}" for a in self.cognitive_approach.get("approach", [])]),
            # Add more params from persona.yaml as needed for the system prompt template
        }

        # Substitute system prompt template
        system_prompt_final = self.system_prompt_template.substitute(**system_prompt_params)
        
        # Prepare components for user prompt template
        memories_formatted = self._format_memories(memories)
        tools_formatted = self._format_tools(tools)
        context_formatted = self._format_additional_context(additional_context or {})

        user_section_params = {
            "query": context.get("query", "No specific query."),
            "timestamp": context.get("timestamp", datetime.utcnow().isoformat()),
            "memories": memories_formatted,
            "tools": tools_formatted,
            "context": context_formatted
        }

        # Substitute user prompt template
        user_section = self.user_prompt_template.substitute(**user_section_params)
        
        full_prompt = system_prompt_final + "\n\n" + user_section
        
        self.logger.debug(f"Reasoning prompt built. Length: {len(full_prompt)}. Preview: {full_prompt[:500]}...")
        return full_prompt
    
    def _format_memories(self, memories: List[MemoryItem]) -> str:
        """Format MemoryItem objects for prompt inclusion."""
        if not memories:
            return "No relevant memories found."
        
        formatted_memories = []
        for mem in memories[:5]:
            formatted_memories.append(mem.to_short_string(max_len=200))
        
        return "\n".join(formatted_memories)
    
    def _format_tools(self, tools: List[Dict]) -> str:
        """
        Format available tools for prompt.
        Expects tools list where 'parameters' is a dict (JSON Schema style).
        """
        if not tools:
            return "No tools currently available."
        
        formatted_tools = []
        for tool_item in tools:
            name = tool_item.get('name', 'unknown_tool')
            description = tool_item.get('description', 'No description provided.')
            params = tool_item.get('parameters', {})
            
            param_parts = []
            for p_name, p_schema in params.items():
                param_type = p_schema.get('type', 'any')
                param_required = " (required)" if p_schema.get('required', False) else ""
                param_parts.append(f"{p_name}:{param_type}{param_required}")
            
            params_str = ", ".join(param_parts)
            
            tool_str = f"- {name}({params_str}): {description}"
            formatted_tools.append(tool_str)
        
        return "\n".join(formatted_tools)
    
    def _format_additional_context(self, context: Dict) -> str:
        """Format additional context for prompt."""
        if not context:
            return "No additional context."
        
        formatted = []
        for key, value in context.items():
            formatted.append(f"- {key}: {value}")
        
        return "\n".join(formatted)
    
    def get_tool_autonomy_level(self) -> str:
        """Get tool autonomy setting from persona config."""
        return self.tool_philosophy_config.get("autonomy_level", "medium")
    
    def should_auto_execute_tool(self, tool_name: str) -> bool:
        """
        Check if a tool should be auto-executed based on persona's tool_usage philosophy.
        """
        autonomy_level = self.get_tool_autonomy_level()
        auto_execute_patterns = self.tool_philosophy_config.get("auto_execute", [])
        require_confirmation_patterns = self.tool_philosophy_config.get("require_confirmation", [])

        # Check if tool is in the explicit require_confirmation list, if so, do NOT auto-execute
        if any(pattern.lower() in tool_name.lower() for pattern in require_confirmation_patterns):
            self.logger.debug(f"Tool '{tool_name}' requires explicit confirmation per persona config.")
            return False
        
        # Check if tool is in the explicit auto_execute list, if so, DO auto-execute
        if any(pattern.lower() in tool_name.lower() for pattern in auto_execute_patterns):
            self.logger.debug(f"Tool '{tool_name}' is in auto_execute list per persona config.")
            return True
        
        # Default behavior based on autonomy level if not explicitly listed
        default_auto_execute = (autonomy_level == "high")
        self.logger.debug(f"Tool '{tool_name}' default auto-execute based on autonomy_level '{autonomy_level}': {default_auto_execute}.")
        return default_auto_execute

    def get_thinking_depth(self) -> str:
        """Get configured thinking depth from persona config."""
        return self.cognitive_approach.get("thinking_depth", "medium")
    
    def get_max_iterations(self) -> int:
        """Get max ReAct loop iterations from persona config."""
        return self.cognitive_approach.get("planning", {}).get("max_iterations", 10)