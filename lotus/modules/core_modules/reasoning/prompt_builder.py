"""
Reasoning Module - Prompt Building with Persona Integration

This updates the prompt building to use Ash's persona configuration
instead of hardcoded prompts.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any
from string import Template


class PersonaAwarePromptBuilder:
    """Builds prompts that incorporate Ash's persona configuration"""
    
    def __init__(self, config_path: str = "config/persona.yaml"):
        """Load persona configuration"""
        self.persona_config = self._load_persona_config(config_path)
        
        # Extract key components
        self.system_prompt = self.persona_config.get("system_prompt", "")
        self.user_prompt_template = Template(
            self.persona_config.get("user_prompt_template", "")
        )
        
        # Persona traits
        self.name = self.persona_config["persona"]["name"]
        self.personality = self.persona_config["persona"]["personality"]
        self.tool_philosophy = self.persona_config["persona"]["tool_usage"]
        self.cognitive_approach = self.persona_config["persona"]["cognitive_approach"]
    
    def _load_persona_config(self, config_path: str) -> Dict:
        """Load persona YAML config"""
        path = Path(config_path)
        if not path.exists():
            # Fall back to default
            return self._default_persona()
        
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def _default_persona(self) -> Dict:
        """Fallback persona if config not found"""
        return {
            "persona": {
                "name": "Ash",
                "personality": {"primary_traits": ["analytical", "autonomous"]},
                "tool_usage": {"autonomy_level": "high"},
                "cognitive_approach": {"thinking_depth": "deep"}
            },
            "system_prompt": "You are Ash, an autonomous AI assistant.",
            "user_prompt_template": "{query}"
        }
    
    def build_reasoning_prompt(
        self,
        context: Dict,
        memories: List,
        tools: List[Dict],
        additional_context: Dict = None
    ) -> str:
        """
        Build complete prompt incorporating:
        - System prompt (Ash's identity and directives)
        - User query
        - Relevant memories
        - Available tools
        - Context
        
        Returns formatted prompt ready for LLM
        """
        
        # Start with system prompt
        full_prompt = self.system_prompt + "\n\n"
        
        # Add user section with template
        user_section = self.user_prompt_template.substitute(
            query=context.get("query", ""),
            timestamp=context.get("timestamp", ""),
            memories=self._format_memories(memories),
            tools=self._format_tools(tools),
            context=self._format_context(additional_context or {})
        )
        
        full_prompt += user_section
        
        return full_prompt
    
    def _format_memories(self, memories: List) -> str:
        """Format memories for prompt inclusion"""
        if not memories:
            return "No relevant memories found."
        
        formatted_memories = []
        for mem in memories[:5]:  # Limit to 5 most relevant
            # Handle Memory objects or dicts
            if hasattr(mem, 'content'):
                content = mem.content
                mem_type = getattr(mem, 'type', 'unknown')
                importance = getattr(mem, 'importance', 0.5)
            else:
                content = mem.get('content', str(mem))
                mem_type = mem.get('type', 'unknown')
                importance = mem.get('importance', 0.5)
            
            # Truncate long memories
            content_preview = content[:200] + "..." if len(content) > 200 else content
            formatted_memories.append(
                f"- [{mem_type}] (importance: {importance:.2f}): {content_preview}"
            )
        
        return "\n".join(formatted_memories)
    
    def _format_tools(self, tools: List[Dict]) -> str:
        """Format available tools for prompt"""
        if not tools:
            return "No tools currently available."
        
        formatted_tools = []
        for tool in tools:
            name = tool.get('name', 'unknown')
            description = tool.get('description', 'No description')
            params = tool.get('parameters', {})
            
            tool_str = f"- {name}: {description}"
            if params:
                tool_str += f"\n  Parameters: {', '.join(params.keys())}"
            
            formatted_tools.append(tool_str)
        
        return "\n".join(formatted_tools)
    
    def _format_context(self, context: Dict) -> str:
        """Format additional context"""
        if not context:
            return "No additional context."
        
        formatted = []
        for key, value in context.items():
            formatted.append(f"- {key}: {value}")
        
        return "\n".join(formatted)
    
    def get_tool_autonomy_level(self) -> str:
        """Get tool autonomy setting"""
        return self.tool_philosophy.get("autonomy_level", "medium")
    
    def should_auto_execute_tool(self, tool_name: str) -> bool:
        """Check if tool should be executed without asking"""
        auto_execute = self.tool_philosophy.get("auto_execute", [])
        require_confirmation = self.tool_philosophy.get("require_confirmation", [])
        
        # Check if tool matches any auto-execute patterns
        for pattern in auto_execute:
            if pattern.lower() in tool_name.lower():
                # Double-check it's not in require_confirmation
                for req_pattern in require_confirmation:
                    if req_pattern.lower() in tool_name.lower():
                        return False
                return True
        
        return False
    
    def get_thinking_depth(self) -> str:
        """Get configured thinking depth"""
        return self.cognitive_approach.get("thinking_depth", "medium")
    
    def get_max_iterations(self) -> int:
        """Get max ReAct loop iterations"""
        planning = self.cognitive_approach.get("planning", {})
        return planning.get("max_iterations", 10)


# Usage in reasoning/logic.py
class ReasoningEngine(BaseModule):
    """Updated reasoning engine with persona awareness"""
    
    async def initialize(self):
        """Initialize with persona-aware prompt builder"""
        await super().initialize()
        
        # Load persona configuration
        self.prompt_builder = PersonaAwarePromptBuilder(
            config_path="config/persona.yaml"
        )
        
        self.logger.info(
            f"Reasoning engine initialized with persona: {self.prompt_builder.name}"
        )
        
        # Get persona-driven settings
        self.max_iterations = self.prompt_builder.get_max_iterations()
        self.thinking_depth = self.prompt_builder.get_thinking_depth()
        self.tool_autonomy = self.prompt_builder.get_tool_autonomy_level()
    
    async def think(self, context: Dict) -> "Thought":
        """Think with persona-aware prompting"""
        
        # Get relevant memories
        memories = await self.memory.recall(context["query"])
        
        # Get available tools
        tools = await self._get_available_tools()
        
        # Build prompt using persona configuration
        prompt = self.prompt_builder.build_reasoning_prompt(
            context=context,
            memories=memories,
            tools=tools,
            additional_context={
                "project": "LOTUS",
                "user": "Cory",
                "autonomy_mode": self.tool_autonomy
            }
        )
        
        # Select provider based on task complexity
        provider = self._select_provider_for_task(context)
        
        # Get LLM response
        response = await self.llm.complete(
            prompt=prompt,
            provider=provider,
            temperature=0.7
        )
        
        # Parse response into Thought object
        thought = self._parse_thought_response(response.content)
        
        return thought
    
    async def _execute_tool(self, tool_call: Dict) -> Any:
        """Execute tool with persona-aware autonomy"""
        tool_name = tool_call.get("tool")
        
        # Check if we should auto-execute or ask permission
        if self.prompt_builder.should_auto_execute_tool(tool_name):
            self.logger.info(f"Auto-executing tool: {tool_name}")
            # Just do it
            result = await self._call_tool(tool_name, tool_call.get("params", {}))
        else:
            # Ask for confirmation (in a real system, this would prompt user)
            self.logger.info(f"Requesting confirmation for tool: {tool_name}")
            # For now, assume approved
            result = await self._call_tool(tool_name, tool_call.get("params", {}))
        
        return result