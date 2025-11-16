import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.module import BaseModule
from lib.decorators import on_event, tool
from lib.utils import generate_id, timestamp_now


class ActionType(Enum):
    TOOL_CALL = "tool_call"
    DELEGATE = "delegate"
    RESPOND = "respond"
    QUERY_MEMORY = "query_memory"
    REQUEST_PERCEPTION = "request_perception"


@dataclass
class Thought:
    """Represents the AI's thought process"""
    understanding: str          # What does the user want?
    plan: List[str]            # Steps to accomplish it
    actions: List['Action']    # Specific actions to take
    reasoning: str             # Why these actions?
    is_complete: bool          # Is the task done?
    response: Optional[str]    # Response to user (if complete)
    confidence: float          # 0-1, confidence in this plan


@dataclass
class Action:
    """Represents an action to take"""
    type: ActionType
    tool: Optional[str] = None
    params: Dict[str, Any] = None
    task: Optional[Dict] = None
    content: Optional[str] = None


@dataclass
class Result:
    """Result of an action"""
    success: bool
    data: Any
    error: Optional[str] = None
    should_stop: bool = False


class ReasoningEngine(BaseModule):
    """
    The reasoning engine - LOTUS's brain
    
    Implements the ReAct loop for intelligent decision making
    """
    
    async def initialize(self):
        """Initialize the reasoning engine"""
        self.logger.info("Reasoning engine initializing...")
        
        # Active thinking sessions
        self.active_sessions = {}
        
        # Tool registry (populated from other modules)
        self.available_tools = {}
        
        # Thinking statistics
        self.stats = {
            "total_thoughts": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "tools_called": 0,
            "tasks_delegated": 0
        }
        
        # Configuration
        self.max_iterations = self.config.get("max_iterations", 10)
        self.thinking_temp = self.config.get("thinking_temperature", 0.7)
        self.enable_delegation = self.config.get("enable_delegation", True)
        
        self.logger.info("Reasoning engine ready")
    
    # ========================================
    # EVENT HANDLERS
    # ========================================
    

    @on_event("perception.user_input")
    async def on_user_input(self, event):
        """
        Handle user text input
    
        This is the main entry point for user requests
        """
        user_message = event.data.get("text", "")
        context = event.data.get("context", {})
    
        # Debug: log input + runtime types for critical components
        try:
            mem_type = type(self.memory).__name__ if self.memory is not None else "None"
        except Exception:
            mem_type = "<error-getting-memory>"
        try:
            llm_type = type(self.llm).__name__ if self.llm is not None else "None"
        except Exception:
            llm_type = "<error-getting-llm>"

        self.logger.info(f"User input received: {user_message[:100]}... | memory={mem_type} llm={llm_type}")

        # If memory is unexpectedly missing or a NoOp with missing methods, capture a debug dump
        try:
            # Attempt a light probe to detect missing APIs
            if self.memory is None:
                self.logger.warning("[debug] memory service is None")
            else:
                # Probe for common methods
                has_search = hasattr(self.memory, 'search')
                has_recall = hasattr(self.memory, 'recall')
                has_retrieve = hasattr(self.memory, 'retrieve')
                self.logger.debug(f"[debug] memory methods: search={has_search} recall={has_recall} retrieve={has_retrieve}")
        except Exception:
            self.logger.exception("[debug] error probing memory service")
    
        # --- START MODIFICATION ---
        self.logger.debug(f"[on_user_input] Attempting to build initial context.")
        full_context = {} # Initialize to empty dict for safety
        try:
            full_context = await self.build_context(user_message, context)
            self.logger.debug(f"[on_user_input] Initial context built successfully. Context keys: {list(full_context.keys())}")
        except Exception as e:
            self.logger.error(f"Failed to build initial context: {e}", exc_info=True)
            await self.publish("action.respond", {
                "content": f"I encountered an error while setting up my context: {str(e)}",
                "session_id": generate_id("error_session") # Use a new session ID for error response
            })
            return # Stop processing if context building fails
        
        self.logger.debug(f"[on_user_input] Starting ReAct loop session.")
        session_id = generate_id("session")
        self.active_sessions[session_id] = {
            "start_time": timestamp_now(),
            "user_message": user_message,
            "context": full_context,
            "iteration": 0
        }
    
        # Actually call the loop
        try:
            await self.think_act_loop(session_id, full_context)
        except Exception as e:
            self.logger.error(f"ReAct loop failed: {e}", exc_info=True)
            await self.publish("action.respond", {
                "content": f"I encountered an error during the reasoning process: {str(e)}",
                "session_id": session_id
            })
        # --- END MODIFICATION ---


    @on_event("perception.voice_input")
    async def on_voice_input(self, event):
        """Handle voice input (same as text input)"""
        # Convert to text input format
        text_event = {
            "data": {
                "text": event.data.get("transcript", ""),
                "context": {
                    **event.data.get("context", {}),
                    "modality": "voice"
                }
            }
        }
        # Assuming Event class can be instantiated like this, or pass event.data directly
        await self.on_user_input(type('Event', (), text_event)())
    
    @on_event("action.tool_result")
    async def on_tool_result(self, event):
        """Receive tool execution results"""
        # Find the session waiting for this result
        tool_name = event.data.get("tool")
        result = event.data.get("result")
        
        # Store in session for the ReAct loop to pick up
        # (In a real implementation, use asyncio Events or Queues)
        pass
    
    # ========================================
    # REACT LOOP - THE CORE
    # ========================================
    
    async def think_act_loop(self, session_id: str, initial_context: Dict):
        """
        The main ReAct loop
        
        THINK -> ACT -> OBSERVE -> LEARN -> LOOP
        """
        context = initial_context
        session = self.active_sessions.get(session_id) # Use .get for safety, though it should exist
        if not session:
            self.logger.error(f"Session {session_id} not found for ReAct loop.")
            return

        for iteration in range(self.max_iterations):
            session["iteration"] = iteration
            
            self.logger.info(f"ReAct iteration {iteration + 1}/{self.max_iterations} for session {session_id}")
            
            # ===== THINK =====
            self.logger.debug(f"[{session_id}] - Thinking phase...")
            thought = await self.think(context)
            self.stats["total_thoughts"] += 1
            
            # Publish thought for transparency
            await self.publish("cognition.thought", {
                "session_id": session_id,
                "iteration": iteration,
                "thought": thought.__dict__
            })
            
            # Check if we're done
            if thought.is_complete:
                self.logger.info(f"[{session_id}] - Thought indicates task complete. Responding.")
                await self.respond(thought.response, session_id)
                self.stats["successful_tasks"] += 1
                break
            
            # ===== ACT =====
            self.logger.debug(f"[{session_id}] - Acting phase with {len(thought.actions)} actions...")
            results = await self.act(thought.actions, session_id)
            self.stats["tools_called"] += sum(1 for a in thought.actions if a.type == ActionType.TOOL_CALL)
            self.stats["tasks_delegated"] += sum(1 for a in thought.actions if a.type == ActionType.DELEGATE)
            
            # ===== OBSERVE =====
            self.logger.debug(f"[{session_id}] - Observing results...")
            observations = await self.observe(results)
            
            # ===== LEARN =====
            self.logger.debug(f"[{session_id}] - Learning from results...")
            await self.learn(thought, results, session_id)
            
            # Update context for next iteration
            self.logger.debug(f"[{session_id}] - Updating context for next iteration...")
            context = await self.update_context(context, thought, observations)
            
            # Check if we should stop early
            if any(r.should_stop for r in results):
                self.logger.info(f"[{session_id}] - An action result requested early stop.")
                break
        else: # This block executes if the loop completes normally (i.e., reaches max_iterations)
            self.logger.warning(f"[{session_id}] - ReAct loop reached max_iterations ({self.max_iterations}) without completion.")
            await self.respond(f"I've reached my maximum thinking iterations and couldn't complete the task. Perhaps you could rephrase or provide more details?", session_id)


        # Clean up session
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        self.logger.info(f"[{session_id}] - ReAct loop completed or stopped. Session cleaned up.")
    
    async def think(self, context: Dict) -> Thought:
        """
        Reason about the situation
        
        Returns a Thought object containing:
        - understanding: What the user wants
        - plan: Steps to accomplish it
        - actions: Specific actions to take
        - reasoning: Why these actions
        """
        self.logger.debug(f"[think] - Starting thinking process for query: {context.get('query', '')[:50]}...")
        # Get relevant memories
        query = context.get("query", "")
        memories = []
        try:
            # Ensure memory service is available before calling it
            if self.memory and hasattr(self.memory, 'recall'):
                self.logger.debug(f"[think] - Calling self.memory.recall for query: {query[:50]}...")
                memories = await self.memory.recall(query, limit=5)
                self.logger.debug(f"[think] - Received {len(memories)} memories.")
            else:
                self.logger.warning("[think] - Memory service or recall method not available. Proceeding without memories.")
        except Exception as e:
            self.logger.error(f"[think] - Error recalling memories: {e}", exc_info=True)
            # Continue without memories if there's an error in recall
            memories = []

        # Get available tools
        tools = await self.get_available_tools()
        
        # Build reasoning prompt
        prompt = self._build_reasoning_prompt(context, memories, tools)
        self.logger.debug(f"[think] - Reasoning prompt built. First 500 chars: {prompt[:500]}...")

        # Ask LLM to reason
        try:
            # Ensure LLM service is available
            if not self.llm or not hasattr(self.llm, 'complete'):
                raise RuntimeError("LLM service or complete method not available for reasoning.")

            self.logger.debug(f"[think] - Calling LLM with provider: {self.config.providers.get('reasoning', 'claude-sonnet-4')}")
            response = await self.llm.complete(
                prompt=prompt,
                provider=self.config.providers.get("reasoning", "claude-sonnet-4"), # Ensure this config path is correct
                temperature=self.thinking_temp,
                max_tokens=2000
            )

            # Debug: log raw LLM/provider response object to aid tracing
            try:
                resp_type = type(response).__name__ if response is not None else "None"
                resp_preview = None
                if response is not None:
                    # Prefer .content or string conversion for preview
                    if hasattr(response, 'content'):
                        resp_preview = str(response.content)[:1000]
                    else:
                        resp_preview = str(response)[:1000]

                self.logger.debug(f"[llm] raw response type={resp_type} preview={resp_preview}")
            except Exception:
                # Never let debug logging break thinking
                self.logger.exception("[llm] error while logging raw response")
            
            # Parse response into structured Thought
            thought = self._parse_thought(response.content, context)
            self.logger.debug(f"[think] - Thought parsed. Is complete: {thought.is_complete}")
            
            return thought
            
        except Exception as e:
            self.logger.error(f"Thinking error: {e}", exc_info=True)
            # Return a simple fallback thought
            return Thought(
                understanding="I encountered an error while thinking",
                plan=["Respond with error"],
                actions=[Action(
                    type=ActionType.RESPOND,
                    content=f"I apologize, I had trouble processing that: {e}"
                )],
                reasoning="Error fallback",
                is_complete=True,
                response=f"I apologize, I had trouble processing that: {e}",
                confidence=0.0
            )
    
    async def act(self, actions: List[Action], session_id: str) -> List[Result]:
        """Execute planned actions"""
        results = []
        
        for action in actions:
            self.logger.info(f"Executing action: {action.type.value} for session {session_id}")
            
            try:
                if action.type == ActionType.TOOL_CALL:
                    result = await self.execute_tool(action, session_id)
                elif action.type == ActionType.DELEGATE:
                    result = await self.delegate_task(action, session_id)
                elif action.type == ActionType.RESPOND:
                    result = await self.respond_to_user(action, session_id)
                elif action.type == ActionType.QUERY_MEMORY:
                    result = await self.query_memory(action, session_id)
                else:
                    result = Result(success=False, data=None, error="Unknown action type")
                
                results.append(result)
                
                # Check if we should stop early
                if result.should_stop:
                    break
                    
            except Exception as e:
                self.logger.error(f"Action execution error: {e} for session {session_id}", exc_info=True)
                results.append(Result(
                    success=False,
                    data=None,
                    error=str(e)
                ))
        
        return results
    
    async def observe(self, results: List[Result]) -> List[Dict]:
        """Analyze the results of actions"""
        observations = []
        
        for result in results:
            observation = {
                "success": result.success,
                "has_error": result.error is not None,
                "data_type": type(result.data).__name__,
                "should_stop": result.should_stop
            }
            
            if not result.success:
                observation["error_message"] = result.error
            
            observations.append(observation)
        
        return observations
    
    async def learn(self, thought: Thought, results: List[Result], session_id: str):
        """
        Store successful patterns in memory
        
        Learn from both successes and failures
        """
        if not self.memory or not hasattr(self.memory, 'remember'):
            self.logger.warning(f"[{session_id}] - Memory service not available for learning.")
            return

        # Store the thought process
        await self.memory.remember(
            content=f"Thought: {thought.understanding}. Plan: {', '.join(thought.plan)}. Result: {'success' if all(r.success for r in results) else 'partial success'}",
            memory_type="procedural",
            importance=0.6 if all(r.success for r in results) else 0.3
        )
        
        # If all actions succeeded, this is a good pattern
        if all(r.success for r in results):
            pattern = {
                "query_type": thought.understanding[:100],
                "actions_taken": [a.type.value for a in thought.actions],
                "outcome": "success"
            }
            
            await self.memory.remember(
                content=json.dumps(pattern),
                memory_type="pattern",
                importance=0.8
            )
    
    # ========================================
    # ACTION EXECUTION
    # ========================================
    
    async def execute_tool(self, action: Action, session_id: str) -> Result:
        """Execute a tool call"""
        tool_name = action.tool
        params = action.params or {}
        
        self.logger.info(f"Calling tool: {tool_name} with params {params} for session {session_id}")
        
        # Publish tool call event
        await self.publish("cognition.tool_call", {
            "session_id": session_id,
            "tool": tool_name,
            "params": params
        })
        
        # In a real implementation, wait for tool result
        # For now, simulate success
        await asyncio.sleep(0.1) # Short delay to simulate work
        
        return Result(
            success=True,
            data={"tool": tool_name, "result": "executed"},
            error=None
        )
    
    async def delegate_task(self, action: Action, session_id: str) -> Result:
        """Delegate complex task to specialized LLM"""
        task = action.task
        
        # Select best provider for this task
        provider = self._select_provider_for_task(task)
        
        self.logger.info(f"Delegating task to {provider} for session {session_id}")
        
        await self.publish("cognition.delegate", {
            "session_id": session_id,
            "task": task,
            "provider": provider,
            "callback": f"reasoning.delegation_result.{session_id}"
        })
        
        # In real implementation, wait for result
        # For now, simulate
        await asyncio.sleep(0.2)
        
        return Result(
            success=True,
            data={"delegated": True, "provider": provider},
            error=None
        )
    
    async def respond_to_user(self, action: Action, session_id: str) -> Result:
        """Respond to the user"""
        content = action.content
        
        self.logger.info(f"Responding to user for session {session_id}: {content[:100]}...")
        await self.publish("action.respond", {
            "session_id": session_id,
            "content": content,
            "type": "text"
        })
        
        return Result(
            success=True,
            data={"responded": True},
            should_stop=True  # Stop the loop after responding
        )
    
    async def query_memory(self, action: Action, session_id: str) -> Result:
        """Query memory system"""
        query = action.params.get("query", "")
        self.logger.info(f"Querying memory for session {session_id}: {query[:100]}...")
        
        memories = []
        if self.memory and hasattr(self.memory, 'recall'):
            memories = await self.memory.recall(query, limit=5)
            self.logger.debug(f"Received {len(memories)} memories from query.")
        else:
            self.logger.warning(f"[{session_id}] - Memory service or recall method not available for querying.")
        
        return Result(
            success=True,
            data={"memories": [m.to_dict() for m in memories]},
            error=None
        )
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    async def build_context(self, query: str, additional_context: Dict = None) -> Dict:
        """Build full context for reasoning"""
        self.logger.debug(f"[build_context] - Starting for query: {query[:50]}...")
        context = {
            "query": query,
            "timestamp": timestamp_now(),
            "user_context": additional_context or {},
        }

        # Add relevant memories
        memories = []
        try:
            if self.memory and hasattr(self.memory, 'recall'):
                self.logger.debug(f"[build_context] - Calling self.memory.recall for query: {query[:50]}...")
                memories = await self.memory.recall(query, limit=3)
                self.logger.debug(f"[build_context] - Received {len(memories)} memories for context.")
            else:
                self.logger.warning("[build_context] - Memory service or recall method not available. No memories added to context.")
        except Exception as e:
            self.logger.error(f"[build_context] - Error recalling memories during context build: {e}", exc_info=True)
            # Allow context building to continue without memories if there's an error
            memories = []

        context["relevant_memories"] = [m.to_dict() for m in memories]

        # Add vision analysis if query mentions visual content
        vision_keywords = ["screenshot", "screen", "image", "picture", "photo", "what do you see", "what's on my screen", "show me", "look at"]
        if any(keyword in query.lower() for keyword in vision_keywords):
            self.logger.info("[build_context] - Query requires vision, checking for vision module...")
            # Note: Vision analysis would be triggered here if we had a screen capture
            # The vision module will respond to perception.screen_capture events
            context["requires_vision"] = True
            context["vision_hint"] = "User query mentions visual content - consider requesting screen analysis"
        else:
            context["requires_vision"] = False
        
        # Add system state
        # Ensure get_state method is available and properly implemented in BaseModule
        # Or that 'system' module is loaded and provides state.
        try:
            if hasattr(self, 'get_state') and callable(self.get_state): # self.get_state is from BaseModule
                system_state = await self.get_state("active") # Assuming get_state is an async method
                context["system_state"] = system_state or {}
                self.logger.debug(f"[build_context] - Added system state. Keys: {list(context['system_state'].keys()) if context['system_state'] else 'None'}")
            else:
                context["system_state"] = {}
                self.logger.warning("[build_context] - get_state method not available on ReasoningEngine instance.")
        except Exception as e:
            self.logger.error(f"[build_context] - Error getting system state: {e}", exc_info=True)
            context["system_state"] = {} # Fallback to empty state

        self.logger.debug(f"[build_context] - Context building complete.")
        return context
    
    async def update_context(self, context: Dict, thought: Thought, observations: List[Dict]) -> Dict:
        """Update context with new information"""
        context["previous_thought"] = thought.__dict__
        context["previous_observations"] = observations
        context["iteration"] = context.get("iteration", 0) + 1
        self.logger.debug(f"[update_context] - Context updated for iteration {context['iteration']}.")
        
        return context
    
    async def respond(self, content: str, session_id: str):
        """Send response to user"""
        self.logger.info(f"Sending final response for session {session_id}: {content[:100]}...")
        await self.publish("action.respond", {
            "session_id": session_id,
            "content": content,
            "type": "text"
        })
    
    async def get_available_tools(self) -> List[Dict]:
        """Get list of available tools from all modules"""
        # In real implementation, query module registry
        # For a genuine AI OS, this would likely query the Nucleus or a ToolManager module
        # that aggregates tools from all loaded modules.
        self.logger.debug("[get_available_tools] - Returning available tools including vision.")

        tools = [
            {"name": "search_web", "description": "Search the web for information"},
            {"name": "write_code", "description": "Write or generate code"},
            {"name": "read_file", "description": "Read contents of a file"},
            {"name": "write_file", "description": "Write content to a file"},
        ]

        # Add vision tools - these work via event bus (vision module responds to events)
        tools.extend([
            {"name": "analyze_screenshot", "description": "Analyze a screenshot with AI vision - get description, OCR, UI elements"},
            {"name": "read_screen_text", "description": "Extract all text from a screenshot (OCR)"},
            {"name": "detect_buttons", "description": "Find clickable UI elements in a screenshot"},
        ])

        return tools
    
    def _select_provider_for_task(self, task: Dict) -> str:
        """Select best LLM provider for task"""
        complexity = task.get("complexity", "medium")
        domain = task.get("domain", "general")
        
        # Route to appropriate model
        if complexity == "high" or domain == "architecture":
            selected_provider = "claude-opus-4"
        elif domain == "code":
            selected_provider = self.config.providers.get("reasoning", "claude-sonnet-4")
        elif complexity == "low":
            selected_provider = self.config.providers.get("simple", "gpt-4o-mini")
        else:
            selected_provider = self.config.providers.get("reasoning", "claude-sonnet-4")

        self.logger.debug(f"[select_provider] - Task complexity='{complexity}', domain='{domain}'. Selected provider: '{selected_provider}'.")
        return selected_provider
    
    def _build_reasoning_prompt(self, context: Dict, memories: List, tools: List[Dict]) -> str:
        """Build the prompt for reasoning"""
        prompt = f"""You are LOTUS, an AI assistant with a JARVIS-like personality - witty, intelligent, and helpful.

Current situation:
User query: {context['query']}
Timestamp: {context['timestamp']}

Relevant memories:
{self._format_memories(memories)}

Available tools:
{self._format_tools(tools)}

Your task:
1. Understand what the user wants
2. Break down the task into steps
3. Decide what actions to take
4. Provide your reasoning

Respond in JSON format:
{{
    "understanding": "brief description of what user wants",
    "plan": ["step 1", "step 2", ...],
    "actions": [
        {{"type": "tool_call", "tool": "tool_name", "params": {{}}}},
        {{"type": "respond", "content": "response to user"}}
    ],
    "reasoning": "why you chose these actions",
    "is_complete": true/false,
    "confidence": 0.0-1.0
}}

Think step by step."""
        self.logger.debug("[_build_reasoning_prompt] - Reasoning prompt assembled.")
        return prompt
    
    def _format_memories(self, memories: List) -> str:
        """Format memories for prompt"""
        if not memories:
            return "No relevant memories found."
        
        formatted = []
        for mem in memories[:3]:  # Limit to 3
            # Ensure 'content' exists and is a string, handle if m.to_dict() is used
            mem_content = mem.get("content", str(mem)) if isinstance(mem, dict) else (mem.content if hasattr(mem, 'content') else str(mem))
            formatted.append(f"- {mem_content[:200]}")
        
        return "\n".join(formatted)
    
    def _format_tools(self, tools: List[Dict]) -> str:
        """Format tools for prompt"""
        if not tools:
            return "No tools available."
        
        formatted = []
        for tool_item in tools: # Renamed 'tool' to 'tool_item' to avoid conflict with decorator
            formatted.append(f"- {tool_item['name']}: {tool_item['description']}")
        
        return "\n".join(formatted)
    
    def _parse_thought(self, response_text: str, context: Dict) -> Thought:
        """Parse LLM response into Thought object"""
        self.logger.debug(f"[_parse_thought] - Attempting to parse LLM response.")
        try:
            # Try to parse as JSON
            data = json.loads(response_text)
            self.logger.debug(f"[_parse_thought] - LLM response parsed as JSON.")
            
            # Parse actions
            actions = []
            for action_data in data.get("actions", []):
                action_type = ActionType(action_data.get("type", "respond"))
                
                action = Action(
                    type=action_type,
                    tool=action_data.get("tool"),
                    params=action_data.get("params", {}),
                    content=action_data.get("content")
                )
                actions.append(action)
            
            return Thought(
                understanding=data.get("understanding", ""),
                plan=data.get("plan", []),
                actions=actions,
                reasoning=data.get("reasoning", ""),
                is_complete=data.get("is_complete", False),
                response=data.get("response"),
                confidence=data.get("confidence", 0.5)
            )
            
        except json.JSONDecodeError:
            # Fallback: treat as simple response
            self.logger.warning("Failed to parse thought as JSON, using fallback. Response: %s[:500]", response_text[:500])
            return Thought(
                understanding=context.get('query', 'No query available'), # Use .get for safety
                plan=["Respond to user"],
                actions=[Action(
                    type=ActionType.RESPOND,
                    content=response_text
                )],
                reasoning="Direct response due to JSON parsing failure",
                is_complete=True,
                response=response_text,
                confidence=0.7
            )
        except Exception as e:
            self.logger.error(f"[_parse_thought] - Unexpected error during thought parsing: {e}", exc_info=True)
            return Thought(
                understanding=context.get('query', 'No query available'),
                plan=["Respond with error during parsing"],
                actions=[Action(
                    type=ActionType.RESPOND,
                    content=f"I encountered an internal error while interpreting my thoughts: {str(e)}"
                )],
                reasoning="Error during thought parsing fallback",
                is_complete=True,
                response=f"I encountered an internal error while interpreting my thoughts: {str(e)}",
                confidence=0.0
            )

    # ========================================
    # TOOLS
    # ========================================
    
    @tool("think")
    async def think_tool(self, context: Dict) -> Dict:
        """Analyze a situation and determine next actions"""
        self.logger.debug(f"[think_tool] - Think tool called with context keys: {list(context.keys())}")
        thought = await self.think(context)
        return thought.__dict__
    
    # ========================================
    # SHUTDOWN
    # ========================================
    
    async def shutdown(self):
        """Clean shutdown"""
        self.logger.info("Reasoning engine shutting down...")
        self.logger.info(f"Stats: {self.stats}")