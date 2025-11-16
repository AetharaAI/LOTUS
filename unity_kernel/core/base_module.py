"""
UnityKernel Base Module

Base class that all kernel modules inherit from.
Provides standard lifecycle, event handling, and health checks.
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from abc import ABC, abstractmethod
from datetime import datetime

from .types import Event, ModuleInfo, ModuleState, HealthCheck, Priority


class BaseModule(ABC):
    """
    Base class for all UnityKernel modules

    Provides:
    - Standard lifecycle (initialize, start, stop)
    - Event subscription/publishing
    - Health checks
    - Configuration access
    - State management
    """

    def __init__(self, info: ModuleInfo, config: any, event_bus: any):
        """
        Initialize base module

        Args:
            info: Module metadata
            config: Config manager reference
            event_bus: Event bus reference
        """
        self.info = info
        self.config = config
        self.event_bus = event_bus

        # State
        self.state = ModuleState.DISCOVERED
        self.running = False
        self.initialized = False

        # Event subscriptions
        self._subscriptions: List[tuple] = []  # [(pattern, handler)]

        # Tasks
        self._tasks: List[asyncio.Task] = []

        # Health
        self._last_health_check: Optional[datetime] = None
        self._health_status = "unknown"

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the module

        Override this to perform setup.
        Called once when module is loaded.
        """
        pass

    async def start(self) -> None:
        """
        Start the module

        Override this if you need custom start logic.
        """
        self.running = True
        self.state = ModuleState.RUNNING
        print(f"✓ Module started: {self.info.name}")

    async def stop(self) -> None:
        """
        Stop the module

        Override this to perform cleanup.
        """
        self.running = False
        self.state = ModuleState.UNLOADING

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Unsubscribe from events
        for pattern, handler in self._subscriptions:
            self.event_bus.unsubscribe(pattern, handler)

        print(f"✓ Module stopped: {self.info.name}")

    async def publish(self, event: Event, persist: bool = True) -> None:
        """
        Publish an event to the bus

        Args:
            event: Event to publish
            persist: Whether to persist to Redis Streams
        """
        # Set source if not already set
        if not event.source:
            event.source = self.info.name

        await self.event_bus.publish(event, persist=persist)

    def subscribe(self, event_pattern: str, handler: Callable) -> None:
        """
        Subscribe to events matching a pattern

        Args:
            event_pattern: Event type pattern (supports wildcards)
            handler: Function to call when event occurs
        """
        self.event_bus.subscribe(event_pattern, handler)
        self._subscriptions.append((event_pattern, handler))

    def create_task(self, coro) -> asyncio.Task:
        """
        Create a tracked background task

        Args:
            coro: Coroutine to run as task

        Returns:
            Created task
        """
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        return task

    async def health_check(self) -> HealthCheck:
        """
        Perform health check

        Override this to implement custom health checks.

        Returns:
            Health check result
        """
        self._last_health_check = datetime.utcnow()

        # Default: healthy if running
        status = "healthy" if self.running else "unhealthy"

        return HealthCheck(
            component=self.info.name,
            status=status,
            timestamp=self._last_health_check,
            metrics={
                'state': self.state.value,
                'tasks_running': len([t for t in self._tasks if not t.done()]),
                'subscriptions': len(self._subscriptions)
            }
        )

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value

        Args:
            key: Config key (supports dot notation)
            default: Default value if not found

        Returns:
            Configuration value
        """
        # Try module-specific config first
        module_key = f"modules.{self.info.name}.{key}"
        value = self.config.get(module_key)

        if value is None:
            # Fall back to global config
            value = self.config.get(key, default)

        return value

    async def _lifecycle_wrapper(self) -> None:
        """
        Internal wrapper for lifecycle management

        Don't override this.
        """
        try:
            # Initialize
            self.state = ModuleState.INITIALIZING
            await self.initialize()
            self.initialized = True
            self.state = ModuleState.LOADED

            # Start
            await self.start()

        except Exception as e:
            self.state = ModuleState.FAILED
            self.info.error = str(e)
            raise

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"name={self.info.name} "
            f"state={self.state.value}>"
        )
