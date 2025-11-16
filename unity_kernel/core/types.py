"""
UnityKernel Core Types

Enums and dataclasses that define the kernel's type system.
These are the fundamental building blocks.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import uuid


class SystemState(Enum):
    """Kernel lifecycle states"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"  # Running but some modules failed
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    FAILED = "failed"


class ModuleState(Enum):
    """Module lifecycle states"""
    DISCOVERED = "discovered"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"


class Priority(Enum):
    """Task priority levels for queue processing"""
    CRITICAL = 0    # System-critical (health checks, safety)
    HIGH = 1        # Time-sensitive (sensor data, user commands)
    NORMAL = 2      # Standard operations
    LOW = 3         # Background tasks
    DEFERRED = 4    # Can wait indefinitely


class EventType(Enum):
    """Core event types - extensible via registry"""
    # System events
    SYSTEM_BOOT = "system.boot"
    SYSTEM_READY = "system.ready"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_HEALTH_CHECK = "system.health_check"

    # Module events
    MODULE_DISCOVERED = "module.discovered"
    MODULE_LOADED = "module.loaded"
    MODULE_STARTED = "module.started"
    MODULE_FAILED = "module.failed"
    MODULE_STOPPED = "module.stopped"

    # Processing events
    TASK_QUEUED = "task.queued"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Configuration events
    CONFIG_CHANGED = "config.changed"
    CONFIG_RELOADED = "config.reloaded"

    # Custom events loaded from registry
    CUSTOM = "custom"


@dataclass
class Event:
    """
    Universal event structure

    Everything in the kernel is an event.
    Events are immutable once created.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""  # From EventType or custom registry
    source: str = "kernel"
    destination: Optional[str] = None  # None = broadcast
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: Priority = Priority.NORMAL
    correlation_id: Optional[str] = None  # For tracking related events
    parent_id: Optional[str] = None  # For event chains

    def __post_init__(self):
        """Ensure timestamp is set and add to metadata"""
        if not self.metadata:
            self.metadata = {}
        self.metadata['created_at'] = self.timestamp.isoformat()
        self.metadata['event_id'] = self.event_id


@dataclass
class QueueItem:
    """
    Item in the priority queue

    Wraps an event with processing metadata.
    """
    event: Event
    priority: Priority
    queued_at: datetime = field(default_factory=datetime.utcnow)
    retries: int = 0
    max_retries: int = 3
    handler: Optional[Callable] = None

    def __lt__(self, other: 'QueueItem') -> bool:
        """Compare for priority queue (lower priority value = higher priority)"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # If same priority, FIFO
        return self.queued_at < other.queued_at


@dataclass
class ModuleInfo:
    """
    Module metadata from manifest

    Standardized structure for all modules.
    """
    name: str
    version: str
    module_type: str  # "core", "adapter", "sensor", "model", "service"
    description: str = ""
    author: str = ""

    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    optional_depends: List[str] = field(default_factory=list)

    # Capabilities
    provides: List[str] = field(default_factory=list)  # What events it publishes
    consumes: List[str] = field(default_factory=list)  # What events it subscribes to

    # Configuration
    config_schema: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    # Runtime state
    state: ModuleState = ModuleState.DISCOVERED
    loaded_at: Optional[datetime] = None
    error: Optional[str] = None
    health_status: str = "unknown"

    # Resource management
    priority: Priority = Priority.NORMAL
    cpu_limit: Optional[float] = None  # Percentage
    memory_limit: Optional[int] = None  # MB

    # Hot-reload support
    hot_reload: bool = False
    auto_restart: bool = True


@dataclass
class SystemMetrics:
    """
    System health and performance metrics

    Updated continuously by the kernel.
    """
    uptime_seconds: float = 0.0
    events_processed: int = 0
    events_failed: int = 0
    modules_loaded: int = 0
    modules_running: int = 0
    modules_failed: int = 0
    queue_depth: int = 0
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    last_health_check: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'uptime_seconds': self.uptime_seconds,
            'events_processed': self.events_processed,
            'events_failed': self.events_failed,
            'modules_loaded': self.modules_loaded,
            'modules_running': self.modules_running,
            'modules_failed': self.modules_failed,
            'queue_depth': self.queue_depth,
            'cpu_usage': self.cpu_usage,
            'memory_usage_mb': self.memory_usage_mb,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None
        }


@dataclass
class HealthCheck:
    """Health check result from a module or system component"""
    component: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def is_healthy(self) -> bool:
        """Check if component is healthy"""
        return self.status == "healthy"
