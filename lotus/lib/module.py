"""
LOTUS Module Base Class

Defines the BaseModule class that all LOTUS modules inherit from.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from .logging import get_logger
from .exceptions import ModuleLoadError


@dataclass
class ModuleMetadata:
    """
    Metadata about a module

    Contains information from manifest.yaml and runtime state
    """
    name: str
    type: str  # "core", "capability", "integration"
    version: str = "1.0.0"
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    description: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    priority: str = "normal"  # "high", "normal", "low"
    path: Optional[str] = None  # Filesystem path to module directory

    # Runtime state
    loaded: bool = False
    initialized: bool = False
    load_time: Optional[datetime] = None
    error: Optional[str] = None


class BaseModule:
    """
    Base class for all LOTUS modules

    Provides:
    - Event subscription and publishing via message bus
    - Lifecycle management (initialize, shutdown)
    - Configuration access
    - Logging
    - Tool registration
    - Periodic task scheduling
    """

    def __init__(self, name: str, metadata: ModuleMetadata, message_bus: Any, config: Any, logger: Any = None):
        """
        Initialize base module

        Args:
            name: Module name
            metadata: Module metadata
            message_bus: Message bus for pub/sub
            config: Configuration object
            logger: Logger instance (optional, will create if not provided)
        """
        self.config = config
        self.message_bus = message_bus
        self.metadata = metadata

        # Logging
        self.logger = logger if logger is not None else get_logger(name)

        # Event handlers registered via decorators
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Tools registered via decorators
        self._tools: Dict[str, Callable] = {}

        # Periodic tasks
        self._periodic_tasks: List[asyncio.Task] = []

        # Module state
        self._initialized = False
        self._running = False

    async def _init(self) -> None:
        """
        Internal initialization called by the kernel

        Calls the user-defined initialize() method
        """
        await self.initialize()
        self._initialized = True

    async def initialize(self) -> None:
        """
        Initialize the module

        Override this method in subclasses to perform initialization.
        This is called once when the module is loaded.
        """
        self.logger.info(f"Initializing {self.metadata.name}")

    async def shutdown(self) -> None:
        """
        Shutdown the module

        Override this method in subclasses to perform cleanup.
        This is called when the system is shutting down.
        """
        self.logger.info(f"Shutting down {self.metadata.name}")

        # Cancel all periodic tasks
        for task in self._periodic_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._running = False

    async def publish(self, event: str, data: Any = None) -> None:
        """
        Publish an event to the message bus

        Args:
            event: Event name (e.g., "perception.file_changed")
            data: Event data (must be JSON-serializable)
        """
        await self.message_bus.publish(event, {
            'source': self.metadata.name,
            'event': event,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        })

    async def subscribe(self, event: str, handler: Callable) -> None:
        """
        Subscribe to an event

        Args:
            event: Event name pattern (supports wildcards: "perception.*")
            handler: Async function to call when event occurs
        """
        await self.message_bus.subscribe(event, handler)

    def register_event_handler(self, event: str, handler: Callable) -> None:
        """
        Register an event handler (used by decorators)

        Args:
            event: Event name pattern
            handler: Handler function
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def register_tool(self, name: str, func: Callable) -> None:
        """
        Register a tool (used by decorators)

        Args:
            name: Tool name
            func: Tool function
        """
        self._tools[name] = func
        self.logger.debug(f"Registered tool: {name}")

    def register_periodic(self, interval: float, func: Callable) -> None:
        """
        Register a periodic task (used by decorators)

        Args:
            interval: Interval in seconds
            func: Function to call periodically
        """
        async def periodic_wrapper():
            while self._running:
                try:
                    await func(self)
                except Exception as e:
                    self.logger.error(f"Error in periodic task: {e}")
                await asyncio.sleep(interval)

        # Don't start the task yet - wait for module to be fully initialized
        self.logger.debug(f"Registered periodic task: {func.__name__} (every {interval}s)")

    async def start_periodic_tasks(self) -> None:
        """Start all registered periodic tasks"""
        self._running = True
        # Periodic tasks will be started by the decorator handling

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Call a registered tool

        Args:
            tool_name: Name of tool to call
            **kwargs: Tool arguments

        Returns:
            Tool result

        Raises:
            ValueError: If tool not found
        """
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found in {self.metadata.name}")

        tool_func = self._tools[tool_name]
        if asyncio.iscoroutinefunction(tool_func):
            return await tool_func(self, **kwargs)
        else:
            return tool_func(self, **kwargs)

    def get_tools(self) -> Dict[str, Callable]:
        """Get all registered tools"""
        return self._tools.copy()

    def get_event_handlers(self) -> Dict[str, List[Callable]]:
        """Get all registered event handlers"""
        return self._event_handlers.copy()

    @property
    def is_initialized(self) -> bool:
        """Check if module is initialized"""
        return self._initialized

    @property
    def is_running(self) -> bool:
        """Check if module is running"""
        return self._running

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.metadata.name} initialized={self._initialized}>"
