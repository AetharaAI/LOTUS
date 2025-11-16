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
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ToolCategory(Enum):
    """Categories of tools"""
    INFORMATION = "information"
    COMPUTATION = "computation"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    MEMORY = "memory"
    DELEGATION = "delegation"
    SYSTEM = "system"


@dataclass
class Tool:
    """Tool definition"""
    name: str
    description: str
    category: ToolCategory
    function: Callable
    parameters: Dict[str, Any]
    requires_confirmation: bool = False
    is_dangerous: bool = False


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
    
    def __init__(self, message_bus, memory, logger, security_context=None):
        self.message_bus = message_bus
        self.memory = memory
        self.logger = logger
        self.security_context = security_context
        
        # Tool registry
        self.tools: Dict[str, Tool] = {}
        
        # Execution history
        self.execution_history: List[Dict[str, Any]] = []
        
        # Register built-in tools
        self._register_builtin_tools()
    
    def _register_builtin_tools(self) -> None:
        """Register built-in tools"""
        
        # Memory tools
        self.register(
            name="search_memory",
            description="Search through memory for information",
            category=ToolCategory.MEMORY,
            function=self._tool_search_memory,
            parameters={
                "query": {"type": "string", "required": True},
                "limit": {"type": "int", "default": 5}
            }
        )
        
        self.register(
            name="remember",
            description="Store information in memory",
            category=ToolCategory.MEMORY,
            function=self._tool_remember,
            parameters={
                "content": {"type": "string", "required": True},
                "importance": {"type": "float", "default": 0.5}
            }
        )
        
        # Information tools
        self.register(
            name="web_search",
            description="Search the web for current information",
            category=ToolCategory.INFORMATION,
            function=self._tool_web_search,
            parameters={
                "query": {"type": "string", "required": True},
                "limit": {"type": "int", "default": 5}
            }
        )
        
        # File system tools
        self.register(
            name="read_file",
            description="Read contents of a file",
            category=ToolCategory.FILE_SYSTEM,
            function=self._tool_read_file,
            parameters={
                "path": {"type": "string", "required": True}
            },
            requires_confirmation=False
        )
        
        self.register(
            name="write_file",
            description="Write content to a file",
            category=ToolCategory.FILE_SYSTEM,
            function=self._tool_write_file,
            parameters={
                "path": {"type": "string", "required": True},
                "content": {"type": "string", "required": True}
            },
            requires_confirmation=True,
            is_dangerous=True
        )
        
        # Computation tools
        self.register(
            name="execute_python",
            description="Execute Python code safely",
            category=ToolCategory.COMPUTATION,
            function=self._tool_execute_python,
            parameters={
                "code": {"type": "string", "required": True}
            },
            requires_confirmation=True,
            is_dangerous=True
        )
        
        self.logger.info(f"Registered {len(self.tools)} built-in tools")
    
    def register(self, name: str, description: str, category: ToolCategory,
                function: Callable, parameters: Dict[str, Any],
                requires_confirmation: bool = False,
                is_dangerous: bool = False) -> None:
        """
        Register a new tool
        
        Args:
            name: Tool name
            description: What the tool does
            category: Tool category
            function: Async function to execute
            parameters: Parameter schema
            requires_confirmation: Whether to ask user before execution
            is_dangerous: Whether tool can cause harm
        """
        tool = Tool(
            name=name,
            description=description,
            category=category,
            function=function,
            parameters=parameters,
            requires_confirmation=requires_confirmation,
            is_dangerous=is_dangerous
        )
        
        self.tools[name] = tool
        self.logger.debug(f"Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Tool]:
        """
        List available tools
        
        Args:
            category: Filter by category (optional)
        
        Returns:
            List of tools
        """
        tools = list(self.tools.values())
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        return tools
    
    def get_tool_descriptions(self) -> List[Dict[str, str]]:
        """Get tool descriptions for AI"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "parameters": json.dumps(tool.parameters)
            }
            for tool in self.tools.values()
        ]
    
    async def execute(self, tool_name: str, 
                     parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute a tool
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
        
        Returns:
            ToolResult with success/failure and result
        """
        import time
        
        start_time = time.time()
        
        # Get tool
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                result=None,
                error=f"Tool not found: {tool_name}"
            )
        
        # Log execution
        self.logger.info(f"Executing tool: {tool_name}")
        
        # Validate parameters
        try:
            validated_params = self._validate_parameters(tool, parameters)
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"Parameter validation failed: {e}"
            )
        
        # Check permissions
        if self.security_context and tool.is_dangerous:
            # TODO: Check permissions
            pass
        
        # Execute tool
        try:
            result = await tool.function(**validated_params)
            
            execution_time = time.time() - start_time
            
            # Record execution
            self.execution_history.append({
                'tool': tool_name,
                'parameters': validated_params,
                'success': True,
                'execution_time': execution_time,
                'timestamp': time.time()
            })
            
            return ToolResult(
                success=True,
                result=result,
                error=None,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.logger.error(f"Tool execution failed: {tool_name}: {e}")
            
            # Record failure
            self.execution_history.append({
                'tool': tool_name,
                'parameters': validated_params,
                'success': False,
                'error': str(e),
                'execution_time': execution_time,
                'timestamp': time.time()
            })
            
            return ToolResult(
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time
            )
    
    def _validate_parameters(self, tool: Tool, 
                           parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize parameters"""
        validated = {}
        
        for param_name, param_schema in tool.parameters.items():
            # Check required
            if param_schema.get('required', False):
                if param_name not in parameters:
                    raise ValueError(f"Required parameter missing: {param_name}")
            
            # Get value or default
            value = parameters.get(param_name, param_schema.get('default'))
            
            # Type checking
            expected_type = param_schema.get('type')
            if value is not None and expected_type:
                if expected_type == 'string' and not isinstance(value, str):
                    value = str(value)
                elif expected_type == 'int':
                    value = int(value)
                elif expected_type == 'float':
                    value = float(value)
            
            validated[param_name] = value
        
        return validated
    
    # Built-in tool implementations
    
    async def _tool_search_memory(self, query: str, limit: int = 5) -> List[Dict]:
        """Search memory tool"""
        try:
            results = await self.memory.search(query, limit=limit)
            return results
        except Exception as e:
            self.logger.error(f"Memory search failed: {e}")
            return []
    
    async def _tool_remember(self, content: str, importance: float = 0.5) -> str:
        """Store in memory tool"""
        try:
            await self.memory.store({
                'content': content,
                'importance': importance,
                'source': 'tool'
            })
            return "Stored in memory"
        except Exception as e:
            self.logger.error(f"Memory store failed: {e}")
            return f"Failed to store: {e}"
    
    async def _tool_web_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Web search tool"""
        # Publish search event
        await self.message_bus.publish("tool.web_search", {
            "query": query,
            "limit": limit
        })
        
        # TODO: Wait for results from web search module
        return [{"title": "Example", "url": "https://example.com", "snippet": "Example result"}]
    
    async def _tool_read_file(self, path: str) -> str:
        """Read file tool"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            raise Exception(f"Failed to read file: {e}")
    
    async def _tool_write_file(self, path: str, content: str) -> str:
        """Write file tool"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"File written: {path}"
        except Exception as e:
            raise Exception(f"Failed to write file: {e}")
    
    async def _tool_execute_python(self, code: str) -> str:
        """Execute Python code tool (DANGEROUS - needs proper sandboxing)"""
        # WARNING: This is a simplified version
        # Production needs proper sandboxing (e.g., RestrictedPython)
        
        try:
            # Create restricted globals
            restricted_globals = {
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'range': range,
                    'str': str,
                    'int': int,
                    'float': float,
                    'list': list,
                    'dict': dict,
                }
            }
            
            # Execute
            exec(code, restricted_globals)
            
            return "Code executed successfully"
        except Exception as e:
            raise Exception(f"Code execution failed: {e}")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics"""
        total_executions = len(self.execution_history)
        successful = sum(1 for e in self.execution_history if e['success'])
        failed = total_executions - successful
        
        return {
            'total_executions': total_executions,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total_executions if total_executions > 0 else 0
        }