"""
LOTUS Reasoning Engine - ReAct Implementation

This is the brain of LOTUS. It implements the Reason-Act loop:
1. THINK: Analyze context and understand what needs to be done
2. PLAN: Break down the task and decide on actions
3. ACT: Execute tools, delegate tasks, take actions
4. OBSERVE: Monitor results and detect issues
5. LEARN: Store successful patterns in memory
6. LOOP: Continue until goal is achieved

This module coordinates all other modules to accomplish user goals.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.module import BaseModule
from lib.decorators import on_event, tool
from lib.utils import generate_id, timestamp_now
from lib.memory import MemoryItem, MemoryType, RetrievalConfig, RetrievalStrategy

# Import the ToolManager
from modules.core_modules.reasoning.tool_manager import ToolManager, ToolCategory, ToolResult


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
    
    def __init__(self, name: str, metadata: Dict, message_bus: Any, config: Any, logger: logging.Logger):
        super().__init__(name, metadata, message_bus, config, logger)
        self.logger = logging.getLogger(f"lotus.module.{self.name}")
        
        self.memory: Any = None # Will be set during _init from config.services.memory
        self.llm: Any = None    # Will be set during _init from config.services.llm
        self.tool_manager: Optional[ToolManager] = None # Will be initialized in .initialize()


    async def initialize(self):
        """Initialize the reasoning engine"""
        self.logger.info("Reasoning engine initializing...")
        
        # Ensure memory and LLM services are set up by Nucleus
        self.memory = self.config.get("services.memory")
        if not self.memory:
            self.logger.critical("Memory service not available to ReasoningEngine. Critical functions may fail.")
        self.llm = self.config.get("services.llm")
        if not self.llm:
            self.logger.critical("LLM provider service not available to ReasoningEngine. Critical functions may fail.")

        # Initialize the ToolManager
        self.tool_manager = ToolManager(self.message_bus, self.memory, self.logger)
        self.logger.info("ToolManager initialized within ReasoningEngine.")

        # Active thinking sessions
        self.active_sessions: Dict[str, Dict] = {} # {session_id: session_data}
        
        # Configuration
        self.max_iterations = self.config.get("reasoning.max_iterations", 10)
        self.thinking_temp = self.config.get("reasoning.thinking_temperature", 0.7)
        self.enable_delegation = self.config.get("reasoning.enable_delegation", True)

        self.logger.info("Reasoning engine ready")
    
    @on_event("cognition.orchestrated_input")
    async def on_orchestrated_input(self, event):
        """
        Handle orchestrated input from the ContextOrchestrator.
        This is the main entry point for user requests or significant perceptions.
        """
        summary = event.data.get("summary", "")
        memory_refs = event.data.get("memory_references", [])
        original_event_context = event.data.get("original_event_context", {})
        importance = event.data.get("importance", 0.5)
        user_query = event.data.get("user_query", "")
        source_module = event.data.get("source_module", "")
        
        initial_query = user_query if user_query else summary

        self.logger.info(f"Received orchestrated input from '{source_module}': {initial_query[:100]}... (refs: {len(memory_refs)})")

        mem_type = type(self.memory).__name__ if self.memory is not None else "None"
        llm_type = type(self.llm).__name__ if self.llm is not None else "None"
        self.logger.debug(f"ReasoningEngine dependencies: memory={mem_type} llm={llm_type}")

        self.logger.debug(f"[on_orchestrated_input] Attempting to build initial context for query: {initial_query[:50]}...")
        full_context = {}
        try:
            full_context = await self.build_context(initial_query, original_event_context, memory_refs)
            self.logger.debug(f"[on_orchestrated_input] Initial context built successfully. Context keys: {list(full_context.keys())}")
        except Exception as e:
            self.logger.error(f"Failed to build initial context for orchestrated input: {e}", exc_info=True)
            await self.publish("action.respond", {
                "content": f"I encountered an error while setting up my context for that input: {str(e)}",
                "session_id": generate_id("error_session"),
                "source_module": self.name
            })
            return
        
        self.logger.debug(f"[on_orchestrated_input] Starting ReAct loop session.")
        session_id = generate_id("session")
        self.active_sessions[session_id] = {
            "start_time": timestamp_now(),
            "user_message": initial_query,
            "context": full_context,
            "iteration": 0,
            "tool_results_queue": asyncio.Queue() # A dedicated queue for tool results for this session
        }
    
        try:
            await self.think_act_loop(session_id, full_context)
        except Exception as e:
            self.logger.error(f"ReAct loop failed: {e}", exc_info=True)
            await self.publish("action.respond", {
                "content": f"I encountered an error during the reasoning process: {str(e)}",
                "session_id": session_id,
                "source_module": self.name
            })

    # This is a crucial handler for asynchronous tool execution results
    @on_event("action.tool_result")
    async def on_tool_result(self, event):
        """Receive tool execution results and forward to the correct session."""
        session_id = event.data.get("session_id")
        tool_name = event.data.get("tool")
        result_data = event.data.get("result")
        error_data = event.data.get("error")

        if session_id and session_id in self.active_sessions:
            self.logger.debug(f"Received tool result for session {session_id}, tool: {tool_name}. Putting into queue.")
            session_queue = self.active_sessions[session_id]['tool_results_queue']
            await session_queue.put(ToolResult(
                success=error_data is None,
                result=result_data,
                error=error_data,
                execution_time=event.data.get("execution_time", 0.0)
            ))
        else:
            self.logger.warning(f"Received tool result for unknown or stale session {session_id}, tool: {tool_name}. Result: {result_data}")

    # ========================================
    # REACT LOOP - THE CORE
    # ========================================
    
    async def think_act_loop(self, session_id: str, initial_context: Dict):
        """
        The main ReAct loop
        """
        context = initial_context
        session = self.active_sessions.get(session_id)
        if not session:
            self.logger.error(f"Session {session_id} not found for ReAct loop, aborting.")
            return

        for iteration in range(self.max_iterations):
            session["iteration"] = iteration
            
            self.logger.info(f"ReAct iteration {iteration + 1}/{self.max_iterations} for session {session_id}")
            
            # ===== THINK =====
            self.logger.debug(f"[{session_id}] - Thinking phase...")
            thought = await self.think(context)
            self.stats["total_thoughts"] += 1
            
            await self.publish("cognition.thought", {
                "session_id": session_id,
                "iteration": iteration,
                "thought": thought.__dict__,
                "source_module": self.name
            })
            
            if thought.is_complete:
                self.logger.info(f"[{session_id}] - Thought indicates task complete. Responding.")
                await self.respond(thought.response, session_id)
                self.stats["successful_tasks"] += 1
                break
            
            # ===== ACT =====
            self.logger.debug(f"[{session_id}] - Acting phase with {len(thought.actions)} actions...")
            results = []
            for action in thought.actions: # Process actions sequentially for now
                action_result = await self.act_on_single_action(action, session_id)
                results.append(action_result)
                if action_result.should_stop: # Stop processing further actions if one requests it
                    self.logger.info(f"[{session_id}] - Action '{action.type.value}' requested early stop. Remaining actions skipped.")
                    break

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
            
            if any(r.should_stop for r in results):
                self.logger.info(f"[{session_id}] - An action result requested early stop, terminating loop.")
                break
        else:
            self.logger.warning(f"[{session_id}] - ReAct loop reached max_iterations ({self.max_iterations}) without completion.")
            await self.respond(f"I've reached my maximum thinking iterations and couldn't complete the task for '{initial_context.get('query', 'your request')[:50]}...'. Perhaps you could rephrase or provide more details?", session_id)


        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        self.logger.info(f"[{session_id}] - ReAct loop completed or stopped. Session cleaned up.")
    
    async def act_on_single_action(self, action: Action, session_id: str) -> Result:
        """Helper to execute a single action within the ReAct loop."""
        self.logger.info(f"[{session_id}] - Executing single action: {action.type.value}")
        try:
            if action.type == ActionType.TOOL_CALL:
                return await self.execute_tool(action, session_id)
            elif action.type == ActionType.DELEGATE:
                return await self.delegate_task(action, session_id)
            elif action.type == ActionType.RESPOND:
                return await self.respond_to_user(action, session_id)
            elif action.type == ActionType.QUERY_MEMORY:
                return await self.query_memory(action, session_id)
            else:
                return Result(success=False, data=None, error="Unknown action type", should_stop=True)
        except Exception as e:
            self.logger.exception(f"[{session_id}] - Error executing action '{action.type.value}': {e}")
            return Result(success=False, data=None, error=f"Action execution failed: {e}", should_stop=True)

    async def think(self, context: Dict) -> Thought:
        """
        Reason about the situation.
        """
        self.logger.debug(f"[think] - Starting thinking process for query: {context.get('query', '')[:50]}...")
        
        query = context.get("query", "")
        memories = []
        if self.memory and hasattr(self.memory, 'recall'):
            try:
                self.logger.debug(f"[think] - Calling self.memory.recall for query: {query[:50]}...")
                memories = await self.memory.recall(query, limit=5, strategy=RetrievalStrategy.COMPREHENSIVE.value)
                self.logger.debug(f"[think] - Received {len(memories)} memories.")
            except Exception as e:
                self.logger.error(f"[think] - Error recalling memories: {e}", exc_info=True)
                memories = []
        else:
            self.logger.warning("[think] - Memory service or recall method not available. Proceeding without memories.")

        tools = self.tool_manager.get_tool_descriptions() if self.tool_manager else []
        
        prompt = self._build_reasoning_prompt(context, memories, tools)
        self.logger.debug(f"[think] - Reasoning prompt built. First 500 chars: {prompt[:500]}...")

        try:
            if not self.llm or not hasattr(self.llm, 'complete'):
                raise RuntimeError("LLM service or complete method not available for reasoning.")

            self.logger.debug(f"[think] - Calling LLM with provider: {self.config.get('providers.reasoning_model', 'claude-sonnet-4')}")
            response = await self.llm.complete(
                prompt=prompt,
                provider=self.config.get("providers.reasoning_model", "claude-sonnet-4"),
                temperature=self.thinking_temp,
                max_tokens=2000
            )

            try:
                resp_type = type(response).__name__ if response is not None else "None"
                resp_preview = None
                if response is not None:
                    if hasattr(response, 'content'):
                        resp_preview = str(response.content)[:1000]
                    else:
                        resp_preview = str(response)[:1000]

                self.logger.debug(f"[llm] raw response type={resp_type} preview={resp_preview}")
            except Exception:
                self.logger.exception("[llm] error while logging raw response")
            
            thought = self._parse_thought(response.content, context)
            self.logger.debug(f"[think] - Thought parsed. Is complete: {thought.is_complete}")
            
            return thought
            
        except Exception as e:
            self.logger.error(f"Thinking error: {e}", exc_info=True)
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
        """Deprecated: Use act_on_single_action for sequential processing."""
        self.logger.warning("ReasoningEngine.act() is deprecated. Using act_on_single_action() for sequential processing.")
        results = []
        for action in actions:
            action_result = await self.act_on_single_action(action, session_id)
            results.append(action_result)
            if action_result.should_stop:
                break
        return results
    
    async def observe(self, results: List[Result]) -> List[Dict]:
        """Analyze the results of actions"""
        observations = []
        
        for result in results:
            observation = {
                "success": result.success,
                "has_error": result.error is not None,
                "data_type": type(result.data).__name__,
                "should_stop": result.should_stop,
                "result_preview": str(result.data)[:100]
            }
            
            if not result.success:
                observation["error_message"] = result.error
            
            observations.append(observation)
        self.logger.debug(f"Observed {len(observations)} results.")
        return observations
    
    async def learn(self, thought: Thought, results: List[Result], session_id: str):
        """
        Store successful patterns in memory
        Learn from both successes and failures
        """
        if not self.memory or not hasattr(self.memory, 'remember'):
            self.logger.warning(f"[{session_id}] - Memory service not available for learning.")
            return

        try:
            await self.memory.remember(
                content=f"Thought: {thought.understanding}. Plan: {', '.join(thought.plan)}. Result: {'success' if all(r.success for r in results) else 'partial success'}",
                memory_type=MemoryType.PROCEDURAL.value,
                importance=0.6 if all(r.success for r in results) else 0.3,
                metadata={"session_id": session_id, "actions_taken": [a.type.value for a in thought.actions]},
                source_module=self.name
            )
            
            if all(r.success for r in results):
                pattern = {
                    "query_type": thought.understanding[:100],
                    "actions_taken": [a.type.value for a in thought.actions],
                    "outcome": "success"
                }
                
                await self.memory.remember(
                    content=json.dumps(pattern),
                    memory_type=MemoryType.SEMANTIC.value,
                    importance=0.8,
                    metadata={"session_id": session_id, "pattern_type": "success"},
                    source_module=self.name
                )
            self.logger.debug(f"[{session_id}] - Learning step completed.")
        except Exception as e:
            self.logger.exception(f"[{session_id}] - Error during learning step.")
    
    # ========================================
    # ACTION EXECUTION
    # ========================================
    
    async def execute_tool(self, action: Action, session_id: str) -> Result:
        """Execute a tool call using the ToolManager."""
        tool_name = action.tool
        params = action.params or {}
        
        if not self.tool_manager:
            self.logger.critical("ToolManager not initialized, cannot execute tool.")
            return Result(success=False, data=None, error="ToolManager not available.", should_stop=True)

        self.logger.info(f"[{session_id}] - Executing tool via ToolManager: {tool_name} with params: {params}")
        
        try:
            # Execute the tool using the ToolManager
            tool_execution_result: ToolResult = await self.tool_manager.execute(tool_name, params)
            
            # Publish action result event for external observers
            await self.publish("action.tool_result", {
                "session_id": session_id,
                "tool": tool_name,
                "result": tool_execution_result.result,
                "error": tool_execution_result.error,
                "success": tool_execution_result.success,
                "execution_time": tool_execution_result.execution_time,
                "source_module": self.name
            })

            return Result(
                success=tool_execution_result.success,
                data=tool_execution_result.result,
                error=tool_execution_result.error,
                should_stop=False # Tools don't inherently stop the ReAct loop unless explicitly designed
            )
        except Exception as e:
            self.logger.exception(f"[{session_id}] - Unexpected error during tool execution of '{tool_name}': {e}")
            return Result(
                success=False,
                data=None,
                error=f"Unexpected error during tool '{tool_name}' execution: {e}",
                should_stop=True # Consider stopping on unexpected tool execution errors
            )
    
    async def delegate_task(self, action: Action, session_id: str) -> Result:
        """Delegate complex task to specialized LLM."""
        task = action.task
        if not task:
            self.logger.warning(f"[{session_id}] - Delegation action has no 'task' defined.")
            return Result(success=False, data=None, error="Delegation task not specified.")

        provider = self._select_provider_for_task(task)
        
        self.logger.info(f"[{session_id}] - Delegating task to {provider}: {task.get('description', '')[:50]}...")
        
        await self.publish("cognition.delegate", {
            "session_id": session_id,
            "task": task,
            "provider": provider,
            "callback": f"{self.name}.delegation_result.{session_id}",
            "source_module": self.name
        })
        
        # This is where we would await the actual result from the delegation.
        # For a truly robust system, the `cognition.delegate` event would trigger
        # a `TaskDelegator` module, which would then publish `action.delegation_result`
        # which this ReasoningEngine would pick up (e.g., via a dedicated asyncio.Queue
        # stored in the session, similar to how tool_results_queue is used).
        
        await asyncio.sleep(2) # Simulate delegation time
        
        return Result(
            success=True,
            data={"delegated": True, "provider": provider, "result": "delegated (simulated)"},
            error=None
        )
    
    async def respond_to_user(self, action: Action, session_id: str) -> Result:
        """Respond to the user."""
        content = action.content
        if not content:
            self.logger.warning(f"[{session_id}] - Respond action has no 'content'.")
            return Result(success=False, data=None, error="Response content not specified.")

        self.logger.info(f"[{session_id}] - Responding to user: {content[:100]}...")
        await self.publish("action.respond", {
            "session_id": session_id,
            "content": content,
            "type": "text",
            "source_module": self.name
        })
        
        return Result(
            success=True,
            data={"responded": True},
            should_stop=True
        )
    
    async def query_memory(self, action: Action, session_id: str) -> Result:
        """Query memory system."""
        query = action.params.get("query", "")
        if not query:
            self.logger.warning(f"[{session_id}] - Query memory action has no 'query' parameter.")
            return Result(success=False, data=None, error="Memory query not specified.")

        self.logger.info(f"[{session_id}] - Querying memory: {query[:100]}...")
        
        memories = []
        if self.memory and hasattr(self.memory, 'recall'):
            try:
                memories = await self.memory.recall(query, limit=action.params.get("limit", 5), strategy=RetrievalStrategy.COMPREHENSIVE.value)
                self.logger.debug(f"[{session_id}] - Received {len(memories)} memories from query.")
            except Exception as e:
                self.logger.error(f"[{session_id}] - Error during memory query: {e}", exc_info=True)
                return Result(success=False, data=None, error=f"Memory query failed: {str(e)}")
        else:
            self.logger.warning(f"[{session_id}] - Memory service or recall method not available for querying.")
            return Result(success=False, data=None, error="Memory service not available.")
        
        return Result(
            success=True,
            data={"memories": [m.to_dict() for m in memories]},
            error=None
        )
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    async def build_context(self, query: str, additional_context: Dict = None, memory_references: Optional[List[str]] = None) -> Dict:
        """Build full context for reasoning, incorporating memory references."""
        self.logger.debug(f"[build_context] - Starting for query: {query[:50]}... with {len(memory_references or [])} memory references.")
        context = {
            "query": query,
            "timestamp": timestamp_now(),
            "user_context": additional_context or {},
        }
        
        memories: List[MemoryItem] = []
        if self.memory and hasattr(self.memory, 'recall'):
            try:
                self.logger.debug(f"[build_context] - Calling self.memory.recall for query: {query[:50]}...")
                memories.extend(await self.memory.recall(query, limit=3, strategy=RetrievalStrategy.COMPREHENSIVE.value))
                self.logger.debug(f"[build_context] - Received {len(memories)} memories based on query.")
            except Exception as e:
                self.logger.error(f"[build_context] - Error recalling memories during context build based on query: {e}", exc_info=True)

        if memory_references and self.memory and hasattr(self.memory, 'get_memories_by_id'):
            try:
                referenced_memories = await self.memory.get_memories_by_id(memory_references)
                self.logger.debug(f"[build_context] - Retrieved {len(referenced_memories)} referenced memories by ID.")
                memories.extend(referenced_memories)
            except Exception as e:
                self.logger.error(f"[build_context] - Error retrieving specific memory references: {e}", exc_info=True)
        else:
             if memory_references:
                 self.logger.warning(f"[build_context] - Memory references provided, but self.memory.get_memories_by_id is not available.")


        unique_mem_map = {m.id: m for m in memories}
        sorted_memories = sorted(unique_mem_map.values(), key=lambda m: m.timestamp, reverse=True)

        context["relevant_memories"] = [m.to_dict() for m in sorted_memories]
        
        try:
            if hasattr(self, 'get_state') and callable(self.get_state):
                system_state = await self.get_state("active")
                context["system_state"] = system_state or {}
                self.logger.debug(f"[build_context] - Added system state. Keys: {list(context['system_state'].keys()) if context['system_state'] else 'None'}")
            else:
                context["system_state"] = {}
                self.logger.warning("[build_context] - get_state method not available on ReasoningEngine instance.")
        except Exception as e:
            self.logger.error(f"[build_context] - Error getting system state: {e}", exc_info=True)
            context["system_state"] = {}

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
            "type": "text",
            "source_module": self.name
        })
    
    def get_available_tools(self) -> List[Dict]:
        """
        Retrieves the list of available tools from the ToolManager,
        formatted for the LLM.
        """
        if self.tool_manager:
            return self.tool_manager.get_tool_descriptions()
        self.logger.warning("ToolManager not available, returning empty tool list.")
        return []
    
    def _select_provider_for_task(self, task: Dict) -> str:
        """Select best LLM provider for task"""
        complexity = task.get("complexity", "medium")
        domain = task.get("domain", "general")
        
        selected_provider = self.config.get("providers.reasoning_model", "claude-sonnet-4")

        if complexity == "high" or domain == "architecture":
            selected_provider = self.config.get("providers.high_complexity_model", "claude-opus-4")
        elif domain == "code":
            selected_provider = self.config.get("providers.code_model", "ollama:deepseek-coder")
        elif complexity == "low":
            selected_provider = self.config.get("providers.simple_model", "gpt-4o-mini")
        
        self.logger.debug(f"[select_provider] - Task complexity='{complexity}', domain='{domain}'. Selected provider: '{selected_provider}'.")
        return selected_provider
    
    def _build_reasoning_prompt(self, context: Dict, memories: List[MemoryItem], tools: List[Dict]) -> str:
        """Build the prompt for reasoning"""
        
        persona_name = self.config.get("system.name", "LOTUS")
        persona_description = self.config.get("system.personality_description", "an AI assistant")
        
        prompt = f"""You are {persona_name}, {persona_description} - witty, intelligent, and helpful.

Current situation:
User query: {context['query']}
Timestamp: {context['timestamp']}

Relevant memories:
{self._format_memories(memories)}

Available tools:
{self._format_tools(tools)}

Your task:
1. Understand what the user wants based on the current query and context.
2. Break down the task into logical, actionable steps.
3. Decide what specific actions to take using your available tools, delegation, or by directly responding.
4. Provide clear reasoning for your chosen actions.
5. If the task is complete, set "is_complete" to true and provide a "response".

Respond ONLY in valid JSON format, adhering strictly to the schema below. Do NOT include any conversational text or markdown outside the JSON.
{{
    "understanding": "brief description of what user wants",
    "plan": ["step 1", "step 2", ...],
    "actions": [
        {{"type": "tool_call", "tool": "tool_name", "params": {{"param_name": "value"}}}},
        {{"type": "delegate", "task": {{"description": "task to delegate", "complexity": "high", "domain": "coding"}}}},
        {{"type": "query_memory", "params": {{"query": "memory search query", "limit": 5}}}},
        {{"type": "respond", "content": "response to user"}}
    ],
    "reasoning": "why you chose these actions",
    "is_complete": true/false,
    "response": "Final response to the user if is_complete is true",
    "confidence": 0.0-1.0
}}

Think step by step."""
        
        return prompt
    
    def _format_memories(self, memories: List[MemoryItem]) -> str:
        """Format memories for prompt"""
        if not memories:
            return "No relevant memories found."
        
        return "\n".join([mem.to_short_string(max_len=150) for mem in memories[:5]]) # Limit to 5 for brevity
    
    def _format_tools(self, tools: List[Dict]) -> str:
        """Format tools for prompt"""
        if not tools:
            return "No tools available."
        
        formatted = []
        for tool_item in tools:
            params_str = ""
            if "parameters" in tool_item and isinstance(tool_item["parameters"], dict):
                # Convert parameter dict to a readable string for the LLM
                param_parts = []
                for p_name, p_schema in tool_item["parameters"].items():
                    param_type = p_schema.get("type", "any")
                    param_required = " (required)" if p_schema.get("required", False) else ""
                    param_parts.append(f"{p_name}:{param_type}{param_required}")
                params_str = ", ".join(param_parts)
            
            formatted.append(f"- {tool_item['name']}({params_str}): {tool_item['description']}")
        
        return "\n".join(formatted)
    
    def _parse_thought(self, response_text: str, context: Dict) -> Thought:
        """Parse LLM response into Thought object"""
        self.logger.debug(f"[_parse_thought] - Attempting to parse LLM response. Response: {response_text[:500]}...")
        try:
            clean_response_text = response_text
            if '```json' in clean_response_text:
                clean_response_text = clean_response_text.split('```json', 1)[1]
                if '```' in clean_response_text:
                    clean_response_text = clean_response_text.split('```', 1)[0]
            elif '```' in clean_response_text:
                 clean_response_text = clean_response_text.split('```', 1)[1]
                 if '```' in clean_response_text:
                    clean_response_text = clean_response_text.split('```', 1)[0]
            
            data = json.loads(clean_response_text.strip())
            self.logger.debug(f"[_parse_thought] - LLM response parsed as JSON.")
            
            actions = []
            for action_data in data.get("actions", []):
                action_type_str = action_data.get("type", "respond")
                try:
                    action_type = ActionType(action_type_str)
                except ValueError:
                    self.logger.warning(f"Invalid ActionType '{action_type_str}' encountered. Defaulting to RESPOND.")
                    action_type = ActionType.RESPOND
                
                action = Action(
                    type=action_type,
                    tool=action_data.get("tool"),
                    params=action_data.get("params", {}),
                    task=action_data.get("task", {}),
                    content=action_data.get("content")
                )
                actions.append(action)
            
            return Thought(
                understanding=data.get("understanding", "No understanding provided."),
                plan=data.get("plan", ["No plan provided."]),
                actions=actions,
                reasoning=data.get("reasoning", "No reasoning provided."),
                is_complete=data.get("is_complete", False),
                response=data.get("response"),
                confidence=data.get("confidence", 0.5)
            )
            
        except json.JSONDecodeError as jde:
            self.logger.error(f"Failed to parse thought as JSON: {jde}. Raw response: {response_text[:500]}...", exc_info=True)
            return Thought(
                understanding=f"Failed to parse LLM response as JSON: {jde}. Raw: {response_text[:200]}",
                plan=["Inform user of parsing error"],
                actions=[Action(
                    type=ActionType.RESPOND,
                    content=f"I apologize, I had an internal error processing my thoughts (JSON parse error). Please try again. (Details: {jde})"
                )],
                reasoning="LLM response was not valid JSON.",
                is_complete=True,
                response=f"I apologize, I had an internal error processing my thoughts (JSON parse error). Please try again.",
                confidence=0.0
            )
        except Exception as e:
            self.logger.exception(f"[_parse_thought] - Unexpected error during thought parsing for response: {response_text[:500]}...")
            return Thought(
                understanding=f"An unexpected error occurred during thought parsing: {e}. Raw: {response_text[:200]}",
                plan=["Inform user of internal error"],
                actions=[Action(
                    type=ActionType.RESPOND,
                    content=f"I encountered an internal error while interpreting my thoughts: {str(e)}. Please try again."
                )],
                reasoning="Internal error during thought parsing.",
                is_complete=True,
                response=f"I encountered an internal error while interpreting my thoughts: {str(e)}. Please try again.",
                confidence=0.0
            )
    
    # ========================================
    # SHUTDOWN
    # ========================================
    
    async def shutdown(self):
        """Clean shutdown"""
        self.logger.info("Reasoning engine shutting down...")
        self.logger.info(f"Stats: {self.stats}")
