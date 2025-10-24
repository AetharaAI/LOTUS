"""
Tool Manager - Executes Tools for Reasoning Engine

Manages registration and execution of tools that the AI can use:
- Web search
- File operations
- Code execution
- Memory queries
- API calls
- Computer control
"""

import asyncio
import json
import time # For time.time()
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging # Import logging

class ToolCategory(Enum):
    """Categories of tools"""
    INFORMATION = "information"
    COMPUTATION = "computation"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    MEMORY = "memory"
    DELEGATION = "delegation"
    SYSTEM = "system"
    PERCEPTION = "perception" # Added for tools related to perception modules

@dataclass
class Tool:
    """Tool definition"""
    name: str
    description: str
    category: ToolCategory
    function: Callable # The actual async function to call
    parameters: Dict[str, Any] = field(default_factory=dict) # Ensure parameters default to dict
    requires_confirmation: bool = False
    is_dangerous: bool = False
    source_module: Optional[str] = None # New: Track which module registered the tool


@dataclass
class ToolResult:
    """Result of tool execution"""
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0


class ToolManager:
    """
    Manages tools that the reasoning engine can use
    
    Handles:
    - Tool registration
    - Tool discovery
    - Tool execution
    - Permission checking
    - Error handling
    """
    
    def __init__(self, message_bus: Any, memory: Any, logger: logging.Logger, security_context=None):
        self.message_bus = message_bus
        self.memory = memory
        self.logger = logger
        self.security_context = security_context
        
        self.tools: Dict[str, Tool] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        self._register_builtin_tools()
        self.logger.info(f"ToolManager initialized with {len(self.tools)} built-in tools.")
    
    def _register_builtin_tools(self) -> None:
        """Register built-in tools provided directly by ToolManager itself."""
        
        self.register(
            name="search_memory",
            description="Search through the long-term or short-term memory for information relevant to a query.",
            category=ToolCategory.MEMORY,
            function=self._tool_search_memory,
            parameters={
                "query": {"type": "string", "description": "The search query or keywords.", "required": True},
                "limit": {"type": "integer", "description": "Maximum number of memory items to return.", "default": 5},
                "strategy": {"type": "string", "description": "Retrieval strategy (e.g., 'comprehensive', 'semantic_search').", "default": "comprehensive"}
            },
            source_module="tool_manager" # Explicitly mark source
        )
        
        self.register(
            name="remember",
            description="Store important information in the memory system for future recall.",
            category=ToolCategory.MEMORY,
            function=self._tool_remember,
            parameters={
                "content": {"type": "string", "description": "The content of the memory to store.", "required": True},
                "memory_type": {"type": "string", "description": "Type of memory (episodic, semantic, procedural, working).", "default": "episodic"},
                "importance": {"type": "number", "description": "Importance of the memory (0.0-1.0).", "default": 0.5},
                "metadata": {"type": "object", "description": "Optional dictionary of additional metadata.", "default": {}}
            },
            source_module="tool_manager"
        )
        
        # Example of a web search tool (implementation would be in a separate module)
        self.register(
            name="web_search",
            description="Perform a web search to find current information, news, or answers to questions.",
            category=ToolCategory.INFORMATION,
            function=self._tool_web_search, # This will just publish an event for now
            parameters={
                "query": {"type": "string", "description": "The search query to use.", "required": True},
                "limit": {"type": "integer", "description": "Maximum number of search results to return.", "default": 3}
            },
            source_module="tool_manager"
        )
        
        self.logger.info(f"Registered {len(self.tools)} built-in tools from ToolManager.")

    def register(self, name: str, description: str, category: ToolCategory,
                function: Callable, parameters: Optional[Dict[str, Any]] = None, # Make parameters optional in signature
                requires_confirmation: bool = False,
                is_dangerous: bool = False,
                source_module: Optional[str] = None) -> None:
        """
        Register a new tool.

        Args:
            name: Unique tool name.
            description: Description for the AI.
            category: Category of the tool.
            function: The async Python callable that implements the tool's logic.
            parameters: JSON schema-like dictionary defining tool parameters.
            requires_confirmation: Whether to ask user before execution.
            is_dangerous: Whether tool can cause harm.
            source_module: The name of the module that provided this tool.
        """
        if parameters is None: # Ensure parameters is a dict if not provided
            parameters = {}

        if name in self.tools:
            self.logger.warning(f"Attempted to re-register tool '{name}'. Overwriting existing definition.")
        
        tool = Tool(
            name=name,
            description=description,
            category=category,
            function=function,
            parameters=parameters,
            requires_confirmation=requires_confirmation,
            is_dangerous=is_dangerous,
            source_module=source_module
        )
        
        self.tools[name] = tool
        self.logger.debug(f"Registered tool: '{name}' from module '{source_module or 'N/A'}'.")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Tool]:
        """List available tools, optionally filtered by category."""
        tools = list(self.tools.values())
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        return tools
    
    def get_tool_descriptions(self) -> List[Dict[str, Any]]: # Changed return type to Any for parameters
        """
        Get tool descriptions formatted for an AI's prompt.
        Parameters are returned as the original dict, not a JSON string.
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "parameters": tool.parameters # Pass as dict, LLM should understand JSON schema
            }
            for tool in self.tools.values()
        ]
    
    async def execute(self, tool_name: str, 
                     parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool.

        Args:
            tool_name: Name of tool to execute.
            parameters: Dictionary of tool parameters.

        Returns:
            ToolResult with success/failure, result, and execution time.
        """
        start_time = time.time()
        
        tool = self.get_tool(tool_name)
        if not tool:
            self.logger.error(f"Attempted to execute non-existent tool: '{tool_name}'.")
            return ToolResult(
                success=False,
                result=None,
                error=f"Tool not found: {tool_name}"
            )
        
        self.logger.info(f"Executing tool: '{tool_name}' from module '{tool.source_module or 'N/A'}' with params: {parameters}.")
        
        # Validate parameters
        try:
            validated_params = self._validate_parameters(tool, parameters)
        except ValueError as e:
            self.logger.error(f"Parameter validation failed for tool '{tool_name}': {e}.")
            return ToolResult(
                success=False,
                result=None,
                error=f"Parameter validation failed: {e}"
            )
        
        # Check permissions (TODO: Implement granular security context checks)
        if self.security_context and tool.is_dangerous:
            self.logger.warning(f"Dangerous tool '{tool_name}' executed without explicit permission check (security context placeholder).")
            # Example: if not self.security_context.has_permission(tool.name):
            #    return ToolResult(...)
        
        try:
            # Execute the tool's function
            result = await tool.function(**validated_params)
            
            execution_time = time.time() - start_time
            
            self.execution_history.append({
                'tool': tool_name,
                'parameters': validated_params,
                'success': True,
                'result_preview': str(result)[:200], # Log a preview
                'execution_time': execution_time,
                'timestamp': time.time(),
                'source_module': tool.source_module
            })
            self.logger.info(f"Tool '{tool_name}' executed successfully. Result preview: {str(result)[:100]}.")
            
            return ToolResult(
                success=True,
                result=result,
                error=None,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.logger.exception(f"Tool execution failed for '{tool_name}': {e}.")
            
            self.execution_history.append({
                'tool': tool_name,
                'parameters': validated_params,
                'success': False,
                'error': str(e),
                'execution_time': execution_time,
                'timestamp': time.time(),
                'source_module': tool.source_module
            })
            
            return ToolResult(
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time
            )
    
    def _validate_parameters(self, tool: Tool, 
                           parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize parameters against the tool's schema."""
        validated = {}
        
        for param_name, param_schema in tool.parameters.items():
            # Check if parameter is required
            if param_schema.get('required', False):
                if param_name not in parameters:
                    raise ValueError(f"Required parameter '{param_name}' missing for tool '{tool.name}'.")
            
            # Get value or default
            value = parameters.get(param_name, param_schema.get('default'))
            
            # Type checking and conversion
            expected_type_str = param_schema.get('type')
            if value is not None and expected_type_str:
                try:
                    if expected_type_str == 'string':
                        if not isinstance(value, str): value = str(value)
                    elif expected_type_str == 'integer': # Changed from 'int' to 'integer' for OpenAPI/JSON Schema compliance
                        if not isinstance(value, int): value = int(value)
                    elif expected_type_str == 'number': # Changed from 'float' to 'number'
                        if not isinstance(value, (int, float)): value = float(value)
                    elif expected_type_str == 'boolean':
                        if not isinstance(value, bool): # Attempt to convert string "true"/"false"
                            if isinstance(value, str):
                                if value.lower() == 'true': value = True
                                elif value.lower() == 'false': value = False
                                else: raise TypeError(f"Cannot convert '{value}' to boolean.")
                            else: raise TypeError(f"Cannot convert '{value}' to boolean.")
                    elif expected_type_str == 'array':
                        if not isinstance(value, list):
                            if isinstance(value, str): # Attempt to parse stringified list
                                try: value = json.loads(value)
                                except json.JSONDecodeError: raise TypeError(f"Cannot parse string '{value}' as array.")
                            else: raise TypeError(f"Expected list for parameter '{param_name}', got {type(value).__name__}.")
                    elif expected_type_str == 'object':
                        if not isinstance(value, dict):
                            if isinstance(value, str): # Attempt to parse stringified dict
                                try: value = json.loads(value)
                                except json.JSONDecodeError: raise TypeError(f"Cannot parse string '{value}' as object.")
                            else: raise TypeError(f"Expected dict for parameter '{param_name}', got {type(value).__name__}.")
                except (ValueError, TypeError, json.JSONDecodeError) as e:
                    raise ValueError(f"Parameter '{param_name}' has incorrect type. Expected '{expected_type_str}', got '{type(value).__name__}'. Conversion error: {e}")
            
            validated[param_name] = value
        
        return validated
    
    # Built-in tool implementations (should be minimal here, mostly delegation)
    
    async def _tool_search_memory(self, query: str, limit: int = 5, strategy: str = "comprehensive") -> List[Dict[str, Any]]:
        """Search memory tool implementation."""
        if not self.memory:
            self.logger.warning("Memory service not available for _tool_search_memory.")
            return [{"error": "Memory service not available."}]
        try:
            self.logger.debug(f"Tool: search_memory called with query: '{query[:50]}...'")
            results = await self.memory.recall(query, limit=limit, strategy=strategy)
            return [m.to_dict() for m in results] # Return as dicts as expected by ReasoningEngine
        except Exception as e:
            self.logger.exception(f"Tool 'search_memory' failed for query '{query[:50]}...'.")
            return [{"error": f"Memory search failed: {e}"}]
    
    async def _tool_remember(self, content: str, memory_type: str = "episodic", importance: float = 0.5, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Store in memory tool implementation."""
        if not self.memory:
            self.logger.warning("Memory service not available for _tool_remember.")
            return {"error": "Memory service not available."}
        try:
            self.logger.debug(f"Tool: remember called with content: '{content[:50]}...'")
            memory_id = await self.memory.remember(
                content=content,
                memory_type=memory_type,
                importance=importance,
                metadata=metadata,
                source_module="tool_manager" # Explicitly mark source
            )
            return {"status": "Stored in memory", "memory_id": memory_id}
        except Exception as e:
            self.logger.exception(f"Tool 'remember' failed for content '{content[:50]}...'.")
            return {"error": f"Failed to store memory: {e}"}
    
    async def _tool_web_search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Web search tool (placeholder).
        In a real system, this would publish to a `web_search_module` and await its results.
        """
        self.logger.warning(f"Tool 'web_search' called for query: '{query[:50]}...'. This is currently a simulated tool.")
        
        # Publish an event that a hypothetical web search module would listen to
        await self.message_bus.publish("action.request_web_search", {
            "query": query,
            "limit": limit,
            "callback_channel": "tool_manager.web_search_result" # Web search module would publish here
        })
        
        # For now, return a placeholder result. A real implementation would need
        # to store a Future/Queue associated with the callback_channel and await it.
        await asyncio.sleep(2) # Simulate network delay
        return [{"title": f"Simulated search result for '{query}'", "url": "https://simulated.example.com", "snippet": "This is a placeholder result from the simulated web search tool."}]
    
    async def _tool_read_file(self, path: str) -> Dict[str, Any]:
        """Read file tool implementation."""
        # This would ideally be handled by a dedicated 'file_system' module
        # with proper path validation and sandboxing.
        self.logger.warning(f"Tool 'read_file' called for path: '{path}'. This is a direct file access and should be sandboxed in production.")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"content": content, "path": path, "length": len(content)}
        except FileNotFoundError:
            self.logger.error(f"File not found: '{path}'.")
            raise Exception(f"File not found: {path}")
        except Exception as e:
            self.logger.exception(f"Failed to read file: '{path}'.")
            raise Exception(f"Failed to read file: {e}")
    
    async def _tool_write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write file tool implementation (DANGEROUS)."""
        self.logger.warning(f"DANGEROUS TOOL 'write_file' called for path: '{path}'. Needs strict sandboxing and user confirmation.")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"status": f"File written: {path}", "path": path, "length": len(content)}
        except Exception as e:
            self.logger.exception(f"Failed to write file: '{path}'.")
            raise Exception(f"Failed to write file: {e}")
    
    async def _tool_execute_python(self, code: str) -> Dict[str, Any]:
        """Execute Python code tool (DANGEROUS - needs proper sandboxing)."""
        self.logger.warning(f"DANGEROUS TOOL 'execute_python' called. Code execution must be sandboxed tightly in production. Code preview: '{code[:100]}...'")
        
        # This is a highly simplified, UNSAFE version for demonstration.
        # NEVER use `exec` directly in a production AI system without
        # extremely robust sandboxing (e.g., dedicated container, RestrictedPython,
        # or a secure microservice).
        try:
            # Create a very restricted environment for exec
            restricted_globals = {"__builtins__": {"print": print}} # Only allow print
            local_vars = {} # Local scope for execution
            
            exec(code, restricted_globals, local_vars)
            
            # Capture print output if possible, otherwise just indicate success
            # This would require redirecting stdout, which is complex for async.
            output_capture = local_vars.get('output', 'No explicit output captured (check print statements).')
            
            return {"status": "Code executed successfully", "output": output_capture, "code_preview": code[:100]}
        except Exception as e:
            self.logger.exception(f"Code execution failed for Python tool.")
            raise Exception(f"Python code execution failed: {e}")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        total_executions = len(self.execution_history)
        successful = sum(1 for e in self.execution_history if e['success'])
        failed = total_executions - successful
        
        return {
            'total_executions': total_executions,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total_executions if total_executions > 0 else 0,
            'last_5_executions': self.execution_history[-5:]
        }