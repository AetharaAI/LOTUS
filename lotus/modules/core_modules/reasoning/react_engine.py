"""
ReAct Engine - Reason + Act Loop

Implements the ReAct (Reason-Act) decision-making loop:
1. THINK: Analyze situation and understand goal
2. REASON: Break down task and plan actions
3. ACT: Execute actions using tools
4. OBSERVE: Monitor results and detect issues
5. LEARN: Store successful patterns
6. LOOP: Continue until goal achieved

This is the core intelligence loop of LOTUS.
"""

import asyncio
import json
import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ReActState(Enum):
    """States in the ReAct loop"""
    THINKING = "thinking"
    REASONING = "reasoning"
    ACTING = "acting"
    OBSERVING = "observing"
    LEARNING = "learning"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ReActStep:
    """Single step in ReAct loop"""
    iteration: int
    state: ReActState
    thought: str
    reasoning: str
    action: Optional[Dict[str, Any]]
    observation: Optional[str]
    timestamp: str


class ReActEngine:
    """
    ReAct Loop Engine
    
    Coordinates the think-reason-act cycle
    """
    
    def __init__(self, llm_provider, tool_manager, memory, logger):
        self.llm = llm_provider
        self.tools = tool_manager
        self.memory = memory
        self.logger = logger
        
        # Loop configuration
        self.max_iterations = 10
        self.thinking_temperature = 0.7
        self.reasoning_temperature = 0.5
        
        # Track loop history
        self.history: List[ReActStep] = []
    
    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the ReAct loop
        
        Args:
            context: Complete context with user input and relevant info
        
        Returns:
            Result dictionary with response and metadata
        """
        user_input = context.get('user_input', '')
        self.logger.info(f"Starting ReAct loop for: {user_input[:50]}...")
        
        iteration = 0
        goal_achieved = False
        final_response = None
        
        while iteration < self.max_iterations and not goal_achieved:
            iteration += 1
            self.logger.debug(f"ReAct iteration {iteration}/{self.max_iterations}")
            
            # THINK: What's the situation?
            thought = await self._think(context, iteration)
            
            # REASON: What should we do?
            reasoning = await self._reason(context, thought, iteration)
            
            # Decide on action
            action = await self._decide_action(reasoning)
            
            # ACT: Execute the action
            if action['type'] == 'respond':
                # Goal achieved, return response
                final_response = action['content']
                goal_achieved = True
                
                # Record step
                self._record_step(
                    iteration=iteration,
                    state=ReActState.COMPLETE,
                    thought=thought,
                    reasoning=reasoning,
                    action=action,
                    observation="Task completed"
                )
                
            elif action['type'] == 'tool_call':
                # Execute tool
                observation = await self._execute_tool(action)
                
                # Record step
                self._record_step(
                    iteration=iteration,
                    state=ReActState.ACTING,
                    thought=thought,
                    reasoning=reasoning,
                    action=action,
                    observation=observation
                )
                
                # Add observation to context for next iteration
                context['observations'] = context.get('observations', [])
                context['observations'].append({
                    'action': action,
                    'result': observation
                })
                
            elif action['type'] == 'delegate':
                # Delegate to specialized model
                observation = await self._delegate_task(action)
                
                # Record step
                self._record_step(
                    iteration=iteration,
                    state=ReActState.ACTING,
                    thought=thought,
                    reasoning=reasoning,
                    action=action,
                    observation=observation
                )
                
                # Add to context
                context['observations'] = context.get('observations', [])
                context['observations'].append({
                    'action': action,
                    'result': observation
                })
            
            # OBSERVE & LEARN
            await self._learn_from_step(thought, reasoning, action, observation if not goal_achieved else final_response)
        
        # Check if we ran out of iterations
        if not goal_achieved:
            final_response = await self._handle_max_iterations(context)
        
        return {
            'response': final_response,
            'iterations': iteration,
            'history': [self._step_to_dict(step) for step in self.history],
            'success': goal_achieved
        }
    
    async def _think(self, context: Dict[str, Any], iteration: int) -> str:
        """
        THINK phase: Analyze current situation
        
        Returns thought about what needs to be done
        """
        prompt = self._build_think_prompt(context, iteration)
        
        thought = await self.llm.complete(
            prompt=prompt,
            model="claude-sonnet-4",
            temperature=self.thinking_temperature,
            max_tokens=500
        )
        
        self.logger.debug(f"Thought: {thought[:100]}...")
        return thought
    
    async def _reason(self, context: Dict[str, Any], 
                     thought: str, iteration: int) -> str:
        """
        REASON phase: Plan what actions to take
        
        Returns reasoning about next actions
        """
        prompt = self._build_reason_prompt(context, thought, iteration)
        
        reasoning = await self.llm.complete(
            prompt=prompt,
            model="claude-sonnet-4",
            temperature=self.reasoning_temperature,
            max_tokens=800
        )
        
        self.logger.debug(f"Reasoning: {reasoning[:100]}...")
        return reasoning
    
    async def _decide_action(self, reasoning: str) -> Dict[str, Any]:
        """
        Decide on action based on reasoning
        
        Returns action dictionary
        """
        prompt = f"""Based on this reasoning:
{reasoning}

Decide on the next action. Respond with ONLY a JSON object (no markdown, no explanation):

{{
  "type": "respond" | "tool_call" | "delegate" | "query_memory",
  "tool": "tool_name if tool_call",
  "params": {{"param": "value"}} if tool_call,
  "task": "task description" if delegate,
  "content": "response content" if respond
}}"""
        
        action_json = await self.llm.complete(
            prompt=prompt,
            model="claude-sonnet-4",
            temperature=0.3,
            max_tokens=500
        )
        
        # Parse JSON
        try:
            # Remove markdown if present
            if '```' in action_json:
                action_json = action_json.split('```')[1]
                if action_json.startswith('json'):
                    action_json = action_json[4:]
                action_json = action_json.strip()
            
            action = json.loads(action_json)
            self.logger.debug(f"Decided action: {action['type']}")
            return action
        except Exception as e:
            self.logger.error(f"Failed to parse action JSON: {e}")
            # Fallback: respond with error
            return {
                'type': 'respond',
                'content': "I apologize, I'm having trouble deciding on the next action. Let me try a different approach."
            }
    
    async def _execute_tool(self, action: Dict[str, Any]) -> str:
        """Execute a tool and return observation"""
        tool_name = action.get('tool')
        params = action.get('params', {})
        
        self.logger.info(f"Executing tool: {tool_name}")
        
        try:
            result = await self.tools.execute(tool_name, params)
            observation = f"Tool {tool_name} executed successfully. Result: {result}"
        except Exception as e:
            observation = f"Tool {tool_name} failed with error: {str(e)}"
            self.logger.error(observation)
        
        return observation
    
    async def _delegate_task(self, action: Dict[str, Any]) -> str:
        """Delegate task to specialized model"""
        task = action.get('task', '')
        
        self.logger.info(f"Delegating task: {task[:50]}...")
        
        try:
            # Use more powerful model for complex tasks
            result = await self.llm.complete(
                prompt=task,
                model="claude-opus-4",  # More capable model
                temperature=0.7,
                max_tokens=2000
            )
            observation = f"Delegated task completed. Result: {result[:200]}..."
        except Exception as e:
            observation = f"Delegation failed: {str(e)}"
            self.logger.error(observation)
        
        return observation
    
    async def _learn_from_step(self, thought: str, reasoning: str,
                               action: Dict[str, Any], observation: str) -> None:
        """
        LEARN phase: Store successful patterns
        
        Saves to memory for future use
        """
        # Create memory entry
        memory_entry = {
            'type': 'reasoning_pattern',
            'thought': thought[:200],
            'reasoning': reasoning[:200],
            'action': action,
            'observation': observation[:200] if observation else None,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store in memory
        try:
            await self.memory.store(memory_entry)
        except Exception as e:
            self.logger.error(f"Failed to store learning: {e}")
    
    async def _handle_max_iterations(self, context: Dict[str, Any]) -> str:
        """Handle case where max iterations reached"""
        self.logger.warning(f"Max iterations ({self.max_iterations}) reached")
        
        # Generate summary response
        prompt = f"""I've been working on this task but reached my iteration limit.
User input: {context.get('user_input')}

Observations so far:
{context.get('observations', [])}

Please provide a helpful response summarizing what was accomplished and what remains."""
        
        response = await self.llm.complete(
            prompt=prompt,
            model="claude-sonnet-4",
            temperature=0.7,
            max_tokens=1000
        )
        
        return response
    
    def _build_think_prompt(self, context: Dict[str, Any], iteration: int) -> str:
        """Build prompt for thinking phase"""
        prompt = f"""You are in a reasoning loop (iteration {iteration}).

USER REQUEST: {context.get('user_input')}

CONTEXT:
- Intent: {context.get('user_intent', 'unknown')}
- Constraints: {context.get('constraints', [])}
"""
        
        if context.get('observations'):
            prompt += "\nPREVIOUS ACTIONS:\n"
            for obs in context['observations'][-3:]:  # Last 3
                prompt += f"- {obs}\n"
        
        prompt += "\nThink about the current situation. What needs to be done next?"
        
        return prompt
    
    def _build_reason_prompt(self, context: Dict[str, Any], 
                            thought: str, iteration: int) -> str:
        """Build prompt for reasoning phase"""
        return f"""SITUATION:
{thought}

USER REQUEST: {context.get('user_input')}

AVAILABLE TOOLS:
{context.get('available_tools', [])}

Based on the situation and available tools, reason about the best next action.
Should we:
1. Use a tool to gather information or perform an action?
2. Delegate a complex subtask to a specialized model?
3. Respond to the user with a final answer?

Explain your reasoning."""
    
    def _record_step(self, iteration: int, state: ReActState,
                    thought: str, reasoning: str, 
                    action: Optional[Dict], observation: Optional[str]) -> None:
        """Record a step in history"""
        from datetime import datetime
        
        step = ReActStep(
            iteration=iteration,
            state=state,
            thought=thought,
            reasoning=reasoning,
            action=action,
            observation=observation,
            timestamp=datetime.now().isoformat()
        )
        self.history.append(step)
    
    def _step_to_dict(self, step: ReActStep) -> Dict[str, Any]:
        """Convert step to dictionary"""
        return {
            'iteration': step.iteration,
            'state': step.state.value,
            'thought': step.thought,
            'reasoning': step.reasoning,
            'action': step.action,
            'observation': step.observation,
            'timestamp': step.timestamp
        }