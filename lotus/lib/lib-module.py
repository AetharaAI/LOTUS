"""
Base Module Class

All LOTUS modules inherit from BaseModule. This provides:
- Event subscription and publishing
- Tool registration
- Memory access
- LLM provider access
- Lifecycle management
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from pathlib import Path
import asyncio
from datetime import datetime


@dataclass
class ModuleMetadata:
    """Metadata about a module"""
    name: str
    version: str
    type: str  # core, capability, integration
    priority: str  # critical, high, normal, low
    path: Path


class BaseModule(ABC):
    """
    Base class for all LOTUS modules
    """

    def __init__(
        self,
        name: str,
        metadata: ModuleMetadata,
        message_bus,
        config,
        logger,
    ):
        self.name = name
        self.metadata = metadata
        self.message_bus = message_bus
        self.config = config
        self.logger = logger

        self._event_handlers: Dict[str, List[Callable]] = {}
        self._tools: Dict[str, Callable] = {}
        self._periodic_tasks: List[asyncio.Task] = []
        self._periodic_pending: List[tuple] = []

        self.enabled = True
        self.initialized = False
        self.last_heartbeat: Optional[datetime] = None

        # Register decorators
        self._register_decorators()

    def _register_decorators(self):
        for attr_name in dir(self):
            try:
                attr = getattr(self, attr_name)
            except Exception:
                continue

            if hasattr(attr, "_event_name"):
                event_name = attr._event_name
                self._event_handlers.setdefault(event_name, []).append(attr)

            if hasattr(attr, "_tool_name"):
                tool_name = attr._tool_name
                self._tools[tool_name] = attr

            if hasattr(attr, "_periodic_interval"):
                interval = attr._periodic_interval
                self._periodic_pending.append((attr, interval))

    async def _run_periodic(self, func: Callable, interval: int):
        while self.enabled:
            try:
                await asyncio.sleep(interval)
                res = func()
                if asyncio.iscoroutine(res):
                    await res
            except asyncio.CancelledError:
                break
            except Exception:
                try:
                    self.logger.exception("Periodic task error")
                except Exception:
                    pass

    @abstractmethod
    async def initialize(self):
        raise NotImplementedError()

    async def _init(self):
        await self.initialize()

        # subscribe after initialize
        for event_name in list(self._event_handlers.keys()):
            try:
                await self.message_bus.subscribe(event_name, self._handle_event)
            except Exception:
                try:
                    self.logger.exception(f"Failed to subscribe to {event_name}")
                except Exception:
                    pass

        # start periodic tasks
        for func, interval in list(self._periodic_pending):
            try:
                task = asyncio.create_task(self._run_periodic(func, interval))
                self._periodic_tasks.append(task)
            except Exception:
                try:
                    self.logger.exception("Failed to start periodic task")
                except Exception:
                    pass

        self.initialized = True
        self.last_heartbeat = datetime.now()

        try:
            await self.publish("system.module.ready", {"module": self.name, "version": getattr(self.metadata, 'version', ''), "type": getattr(self.metadata, 'type', '')})
        except Exception:
            pass

    async def _handle_event(self, event_name: str, data: Any):
        if event_name not in self._event_handlers:
            return
        for handler in list(self._event_handlers[event_name]):
            try:
                ev = Event(name=event_name, data=data, source=self.name)
                # Debug: log incoming event and handler mapping for tracing
                try:
                    self.logger.debug(f"[event] {self.name} handling {event_name} -> {handler.__name__} | data_keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
                except Exception:
                    print(f"[event-debug] {self.name} handling {event_name} -> {getattr(handler, '__name__', repr(handler))}")
                res = handler(ev)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                # Capture exception and include handler info
                try:
                    self.logger.exception(f"Error handling event {event_name} in {handler}")
                except Exception:
                    import traceback
                    print(f"[event-error] Error handling event {event_name} in {handler}: {traceback.format_exc()}")

    async def publish(self, channel: str, data: Any) -> None:
        try:
            # Debug: record publish attempts with top-level keys and source module
            try:
                summary = f"channel={channel} source={self.name} data_type={type(data)}"
                if isinstance(data, dict):
                    summary += f" keys={list(data.keys())}"
                self.logger.debug(f"[publish] {summary}")
            except Exception:
                print(f"[publish-debug] channel={channel} from={self.name}")

            await self.message_bus.publish(channel, data)
        except Exception:
            try:
                self.logger.exception(f"Failed to publish {channel}")
            except Exception:
                pass

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        if "." in tool_name:
            module_name, tool = tool_name.split(".", 1)
        else:
            module_name = self.name
            tool = tool_name

        response_channel = f"tool.response.{self.name}.{datetime.now().timestamp()}"
        await self.publish("tool.request", {"module": module_name, "tool": tool, "params": kwargs, "response_channel": response_channel})
        return None

    async def shutdown(self):
        self.enabled = False
        for task in list(self._periodic_tasks):
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        for event_name in list(self._event_handlers.keys()):
            try:
                await self.message_bus.unsubscribe(event_name, self._handle_event)
            except Exception:
                pass

        try:
            self.logger.info(f"[{self.name}] Shutdown complete")
        except Exception:
            pass

    async def health_check(self) -> bool:
        self.last_heartbeat = datetime.now()
        return self.enabled and self.initialized

    @property
    def llm(self):
        try:
            if hasattr(self, "config") and self.config is not None:
                return self.config.get("services.llm") or self.config.get("services.providers")
            return None
        except Exception:
            return None

    @property
    def memory(self):
        try:
            mem = None
            if hasattr(self, "config") and self.config is not None:
                mem = self.config.get("services.memory") or self.config.get("modules.memory")
            if mem and (hasattr(mem, "recall") or hasattr(mem, "remember") or hasattr(mem, "retrieve")):
                return mem

            class NoOpMemory:
                async def recall(self, *args, **kwargs):
                    return []

                async def remember(self, *args, **kwargs):
                    return None

                async def retrieve(self, *args, **kwargs):
                    return []

                async def get_stats(self):
                    return {}
                
                # Legacy compatibility helpers so callers that expect
                # `memory.search(...)`, `memory.store(...)`, or
                # `memory.get_recent(...)` won't crash when the real
                # memory service isn't available.
                async def search(self, *args, **kwargs):
                    return []

                async def store(self, *args, **kwargs):
                    return None

                async def get_recent(self, *args, **kwargs):
                    return []

                async def get_working_memory(self, *args, **kwargs):
                    return []

            return NoOpMemory()
        except Exception:
            return None


@dataclass
class Event:
    name: str
    data: Any
    source: str
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
