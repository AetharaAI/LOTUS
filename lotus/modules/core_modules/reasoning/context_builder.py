"""
Context Builder for Reasoning Engine

Assembles context for the reasoning engine from:
- Current user input
- Recent memory
- Working memory
- Relevant long-term memories
- System state
- Available tools
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class Context:
    """Complete context for reasoning"""
    user_input: str
    user_intent: Optional[str]
    conversation_history: List[Dict[str, Any]]
    working_memory: List[Dict[str, Any]]
    relevant_memories: List[Dict[str, Any]]
    available_tools: List[Dict[str, str]]
    system_state: Dict[str, Any]
    constraints: List[str]
    timestamp: str


class ContextBuilder:
    """
    Builds context for the reasoning engine
    
    Gathers all relevant information to help the AI make decisions
    """
    
    def __init__(self, memory_system, message_bus, logger):
        self.memory = memory_system
        self.message_bus = message_bus
        self.logger = logger
        
        # Context configuration
        self.max_history_items = 10
        self.max_memory_items = 5
        self.memory_relevance_threshold = 0.5
    
    async def build(self, user_input: str, 
                   additional_context: Optional[Dict] = None) -> Context:
        """
        Build complete context for reasoning
        
        Args:
            user_input: Current user input
            additional_context: Additional context data
        
        Returns:
            Complete Context object
        """
        self.logger.debug(f"Building context for input: {user_input[:50]}...")
        
        # Parse user intent
        intent = await self._extract_intent(user_input)
        
        # Get conversation history
        history = await self._get_conversation_history()
        
        # Get working memory (recent context)
        working_mem = await self._get_working_memory()
        
        # Search for relevant memories
        relevant_mem = await self._search_relevant_memories(user_input, intent)
        
        # Get available tools
        tools = await self._get_available_tools()
        
        # Get system state
        state = await self._get_system_state()
        
        # Determine constraints
        constraints = self._determine_constraints(user_input, additional_context)
        
        context = Context(
            user_input=user_input,
            user_intent=intent,
            conversation_history=history,
            working_memory=working_mem,
            relevant_memories=relevant_mem,
            available_tools=tools,
            system_state=state,
            constraints=constraints,
            timestamp=datetime.now().isoformat()
        )
        
        self.logger.debug(
            f"Context built: {len(history)} history items, "
            f"{len(relevant_mem)} relevant memories, "
            f"{len(tools)} tools available"
        )
        
        return context
    
    async def _extract_intent(self, user_input: str) -> Optional[str]:
        """
        Extract user intent from input
        
        Uses simple heuristics - can be enhanced with ML
        """
        input_lower = user_input.lower()
        
        # Common intent patterns
        if any(word in input_lower for word in ['create', 'make', 'build', 'generate']):
            return 'create'
        elif any(word in input_lower for word in ['fix', 'debug', 'solve', 'error']):
            return 'debug'
        elif any(word in input_lower for word in ['explain', 'what', 'how', 'why']):
            return 'explain'
        elif any(word in input_lower for word in ['analyze', 'review', 'check']):
            return 'analyze'
        elif any(word in input_lower for word in ['search', 'find', 'look']):
            return 'search'
        elif any(word in input_lower for word in ['remember', 'recall', 'what did']):
            return 'recall'
        else:
            return 'general'
    
    async def _get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        try:
            # Get from working memory (L1)
            history = await self.memory.get_recent(
                type="conversation",
                limit=self.max_history_items
            )
            return history
        except Exception as e:
            self.logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def _get_working_memory(self) -> List[Dict[str, Any]]:
        """Get working memory (current session context)"""
        try:
            working_mem = await self.memory.get_working_memory()
            return working_mem
        except Exception as e:
            self.logger.error(f"Error getting working memory: {e}")
            return []
    
    async def _search_relevant_memories(self, query: str, 
                                       intent: Optional[str]) -> List[Dict[str, Any]]:
        """
        Search for relevant memories using semantic search
        
        Args:
            query: Search query (user input)
            intent: User intent for filtering
        
        Returns:
            List of relevant memories
        """
        try:
            # Search long-term memory (L3 - semantic search)
            memories = await self.memory.search(
                query=query,
                limit=self.max_memory_items,
                min_relevance=self.memory_relevance_threshold
            )
            
            # Filter by intent if provided
            if intent and intent != 'general':
                memories = [
                    m for m in memories 
                    if m.get('intent') == intent or not m.get('intent')
                ]
            
            return memories
        except Exception as e:
            self.logger.error(f"Error searching memories: {e}")
            return []
    
    async def _get_available_tools(self) -> List[Dict[str, str]]:
        """
        Get list of available tools
        
        Returns:
            List of tool definitions
        """
        # TODO: Query tool registry from other modules
        # For now, return basic tools
        return [
            {
                "name": "search_memory",
                "description": "Search through memory for information"
            },
            {
                "name": "web_search",
                "description": "Search the web for current information"
            },
            {
                "name": "execute_code",
                "description": "Execute Python code safely"
            },
            {
                "name": "file_operation",
                "description": "Read or write files"
            },
            {
                "name": "delegate_task",
                "description": "Delegate subtask to specialized model"
            }
        ]
    
    async def _get_system_state(self) -> Dict[str, Any]:
        """
        Get current system state
        
        Returns:
            Dictionary of system state info
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "active_modules": [],  # TODO: Get from nucleus
            "memory_usage": "unknown",
            "load": "normal"
        }
    
    def _determine_constraints(self, user_input: str, 
                              additional_context: Optional[Dict]) -> List[str]:
        """
        Determine constraints for the reasoning process
        
        Constraints guide what the AI should/shouldn't do
        """
        constraints = []
        
        # Time constraints
        if any(word in user_input.lower() for word in ['quick', 'fast', 'urgently']):
            constraints.append("Prioritize speed over thoroughness")
        
        # Safety constraints
        constraints.append("Do not execute dangerous operations")
        constraints.append("Ask for confirmation for file modifications")
        
        # Quality constraints
        if any(word in user_input.lower() for word in ['detailed', 'comprehensive', 'thorough']):
            constraints.append("Provide comprehensive response")
        
        # Additional context constraints
        if additional_context:
            if additional_context.get('no_web_search'):
                constraints.append("Do not use web search")
            if additional_context.get('local_only'):
                constraints.append("Use only local resources")
        
        return constraints
    
    def format_for_llm(self, context: Context) -> str:
        """
        Format context as string for LLM prompt
        
        Args:
            context: Context object
        
        Returns:
            Formatted context string
        """
        sections = []
        
        # User input
        sections.append(f"USER REQUEST:\n{context.user_input}\n")
        
        # Intent
        if context.user_intent:
            sections.append(f"DETECTED INTENT: {context.user_intent}\n")
        
        # Conversation history
        if context.conversation_history:
            sections.append("RECENT CONVERSATION:")
            for item in context.conversation_history[-3:]:  # Last 3 exchanges
                role = item.get('role', 'unknown')
                content = item.get('content', '')
                sections.append(f"{role.upper()}: {content}")
            sections.append("")
        
        # Working memory
        if context.working_memory:
            sections.append("WORKING MEMORY:")
            for item in context.working_memory:
                sections.append(f"- {item.get('content', item)}")
            sections.append("")
        
        # Relevant memories
        if context.relevant_memories:
            sections.append("RELEVANT MEMORIES:")
            for mem in context.relevant_memories:
                sections.append(f"- {mem.get('content', mem)}")
            sections.append("")
        
        # Available tools
        if context.available_tools:
            sections.append("AVAILABLE TOOLS:")
            for tool in context.available_tools:
                sections.append(f"- {tool['name']}: {tool['description']}")
            sections.append("")
        
        # Constraints
        if context.constraints:
            sections.append("CONSTRAINTS:")
            for constraint in context.constraints:
                sections.append(f"- {constraint}")
            sections.append("")
        
        return "\n".join(sections)
    
    def to_dict(self, context: Context) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "user_input": context.user_input,
            "user_intent": context.user_intent,
            "conversation_history": context.conversation_history,
            "working_memory": context.working_memory,
            "relevant_memories": context.relevant_memories,
            "available_tools": context.available_tools,
            "system_state": context.system_state,
            "constraints": context.constraints,
            "timestamp": context.timestamp
        }