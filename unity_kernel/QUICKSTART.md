# UnityKernel Quick Start

## Installation

```bash
cd unity_kernel
pip install psutil pyyaml redis  # Core dependencies
```

## Running the Kernel

```bash
python kernel_main.py
```

You should see:
```
🚀 UnityKernel Booting
...
✅ UnityKernel Online
   Version: 0.1.0
   Modules loaded: 2
   Event bus: In-memory
   Workers: 34
```

Press Ctrl+C to shutdown gracefully.

## What Just Happened?

1. **Kernel booted** - Initialized all core components
2. **Discovered modules** - Found example modules in `modules/examples/`
3. **Loaded modules** - Initialized heartbeat and monitor modules
4. **Started processing** - 34 workers started across 5 priority tiers
5. **Events flowing** - Heartbeat publishes, monitor subscribes

## Project Structure

```
unity_kernel/
├── config/
│   └── system.yaml          # Kernel configuration
├── core/
│   ├── types.py             # Core type system
│   ├── event_bus.py         # Async event bus + Redis Streams
│   ├── priority_queue.py    # 5-tier priority processor
│   ├── config.py            # Config manager (hot-reload)
│   ├── base_module.py       # Base class for modules
│   ├── module_loader.py     # Module discovery + lifecycle
│   └── health_monitor.py    # Health monitoring + auto-recovery
├── modules/
│   └── examples/
│       ├── heartbeat/       # Example: event publisher
│       └── monitor/         # Example: event subscriber
├── kernel.py                # Main kernel runtime
└── kernel_main.py           # Entry point
```

## Creating a Module

### 1. Create module directory

```bash
mkdir -p modules/my_module
```

### 2. Create manifest.yaml

```yaml
name: "my_module"
version: "1.0.0"
type: "core"
description: "My awesome module"

depends_on: []  # List of required modules

provides:  # Events this module publishes
  - "my_module.event"

consumes:  # Events this module subscribes to
  - "heartbeat.tick"

config:
  my_setting: "value"

priority: "normal"
hot_reload: true
auto_restart: true
```

### 3. Create module.py

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core import BaseModule, Event, Priority

class MyModule(BaseModule):
    async def initialize(self) -> None:
        """Called once when module loads"""
        self.subscribe("heartbeat.tick", self.on_heartbeat)
        print(f"✓ {self.info.name} initialized")

    async def on_heartbeat(self, event: Event) -> None:
        """Handle heartbeat events"""
        print(f"Received heartbeat: {event.data}")

        # Publish your own event
        await self.publish(Event(
            event_type="my_module.event",
            data={"message": "Hello from my module!"},
            priority=Priority.NORMAL
        ))
```

### 4. Restart kernel

The module will be auto-discovered and loaded.

## Configuration

Edit `config/system.yaml`:

```yaml
kernel:
  version: "0.1.0"
  log_level: "INFO"

event_bus:
  redis_url: "redis://localhost:6379/0"  # Optional
  enable_streams: true  # Persistence

modules:
  auto_discover: true
  discovery_paths:
    - "./modules"
  hot_reload: false  # true = auto-reload on file change

health:
  check_interval: 30  # Health check every 30s
  restart_failed_modules: true
```

## Redis Streams (Optional but Recommended)

### Why Redis Streams?

**Problem**: LLM processes event but crashes before responding.

**Solution**: Event persisted in Redis Stream. Model queries stream when it restarts. Nothing lost.

### Setup Redis

```bash
# Install Redis
docker run -d -p 6379:6379 redis:latest

# Enable in config
event_bus:
  redis_url: "redis://localhost:6379/0"
  enable_streams: true
```

### Replay Events

```python
# After crash, replay missed events
kernel = UnityKernel()
await kernel.boot()

# Replay from last checkpoint
events = await kernel.event_bus.replay_stream(
    "unity:events:sensor.camera",
    from_id="1234567890-0"  # Last processed ID
)
```

## API Usage

```python
from kernel import UnityKernel
from core import Event, Priority

# Create kernel
kernel = UnityKernel("config/system.yaml")
await kernel.boot()

# Publish event
await kernel.publish(Event(
    event_type="my.custom.event",
    data={"key": "value"},
    priority=Priority.HIGH
))

# Subscribe to events
def handler(event: Event):
    print(f"Received: {event}")

kernel.subscribe("my.custom.*", handler)

# Get system status
status = kernel.get_status()
print(status)

# Shutdown
await kernel.shutdown()
```

## Monitoring

### Health Check

```python
health = await kernel.get_health()
print(health.status)  # "healthy", "degraded", "unhealthy"
```

### System Metrics

```python
metrics = kernel.get_metrics()
print(f"Uptime: {metrics.uptime_seconds}s")
print(f"CPU: {metrics.cpu_usage}%")
print(f"Events processed: {metrics.events_processed}")
print(f"Modules running: {metrics.modules_running}")
```

### Event Bus Statistics

```python
stats = kernel.event_bus.get_statistics()
print(f"Published: {stats['events_published']}")
print(f"Delivered: {stats['events_delivered']}")
print(f"Failed: {stats['events_failed']}")
```

## Next Steps

- [ARCHITECTURE.md](ARCHITECTURE.md) - Deep dive into design
- Create your own modules
- Add Redis for persistence
- Build LLM bridge adapters
- Connect hardware sensors
- Deploy to production

## Troubleshooting

**Module not loading?**
- Check manifest.yaml syntax
- Ensure module.py has BaseModule subclass
- Check dependencies are loaded first

**Events not flowing?**
- Verify event_type matches subscription pattern
- Check event bus statistics for failures
- Enable debug logging in config

**High resource usage?**
- Check worker counts in config
- Monitor module health
- Review priority queue depths

---

**The kernel is running. Now plug anything into it.**
