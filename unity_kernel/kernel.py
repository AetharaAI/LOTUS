"""
UnityKernel Main Runtime

The core kernel that orchestrates everything.
This is what users import and interact with.
"""

import asyncio
import signal
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from core import (
    AsyncEventBus,
    AsyncPriorityProcessor,
    ConfigManager,
    ModuleLoader,
    HealthMonitor,
    Event,
    EventType,
    SystemState,
    SystemMetrics,
    HealthCheck,
    Priority
)


class UnityKernel:
    """
    UnityKernel - Deterministic Async Event-Driven Runtime

    The "dumb" foundation that never breaks.
    Everything plugs into this.

    Usage:
        kernel = UnityKernel("config/system.yaml")
        await kernel.boot()
        # Kernel running, modules loaded
        await kernel.shutdown()
    """

    def __init__(self, config_path: str = "config/system.yaml"):
        """
        Initialize UnityKernel

        Args:
            config_path: Path to configuration file/directory
        """
        self.config_path = config_path

        # System state
        self.state = SystemState.STOPPED
        self.boot_time: Optional[datetime] = None

        # Core components (initialized during boot)
        self.config: Optional[ConfigManager] = None
        self.event_bus: Optional[AsyncEventBus] = None
        self.processor: Optional[AsyncPriorityProcessor] = None
        self.module_loader: Optional[ModuleLoader] = None
        self.health_monitor: Optional[HealthMonitor] = None

        # Shutdown handling
        self.shutdown_event = asyncio.Event()
        self._shutdown_handlers = []

    async def boot(self) -> None:
        """
        Boot the kernel

        This is the main initialization sequence:
        1. Load configuration
        2. Initialize event bus
        3. Initialize priority processor
        4. Initialize module loader
        5. Discover and load modules
        6. Start health monitor
        7. Signal system ready
        """
        print("\n" + "="*60)
        print("🚀 UnityKernel Booting")
        print("="*60)

        self.state = SystemState.INITIALIZING
        self.boot_time = datetime.utcnow()

        try:
            # 1. Load configuration
            print("\n[1/7] Loading configuration...")
            self.config = ConfigManager(self.config_path)
            await self.config.load()

            # Start config hot-reload if enabled
            if self.config.get('kernel.hot_reload_config', True):
                await self.config.start_watching()

            # 2. Initialize event bus
            print("[2/7] Initializing event bus...")
            redis_url = self.config.get('event_bus.redis_url')
            enable_streams = self.config.get('event_bus.enable_streams', True)

            self.event_bus = AsyncEventBus(redis_url, enable_streams)
            await self.event_bus.start()

            # 3. Initialize priority processor
            print("[3/7] Initializing priority processor...")
            self.processor = AsyncPriorityProcessor(self.event_bus)
            await self.processor.start()

            # 4. Initialize module loader
            print("[4/7] Initializing module loader...")
            self.module_loader = ModuleLoader(self.config, self.event_bus)

            # 5. Discover and load modules
            print("[5/7] Discovering modules...")
            await self.module_loader.discover()

            print("[6/7] Loading modules...")
            if self.config.get('modules.auto_load_core', True):
                await self.module_loader.load_all()

            # Start module hot-reload if enabled
            if self.config.get('modules.hot_reload', False):
                await self.module_loader.start_watching()

            # 6. Initialize health monitor
            print("[7/7] Starting health monitor...")
            self.health_monitor = HealthMonitor(
                self.config,
                self.event_bus,
                self.module_loader
            )
            await self.health_monitor.start()

            # System is ready
            self.state = SystemState.RUNNING

            # Publish system ready event
            await self.event_bus.publish(Event(
                event_type=EventType.SYSTEM_READY.value,
                source="kernel",
                data={
                    'boot_time': self.boot_time.isoformat(),
                    'modules_loaded': len(self.module_loader.modules),
                    'version': self.config.get('kernel.version', '0.1.0')
                },
                priority=Priority.HIGH
            ))

            print("\n" + "="*60)
            print("✅ UnityKernel Online")
            print("="*60)
            print(f"   Version: {self.config.get('kernel.version', '0.1.0')}")
            print(f"   Modules loaded: {len(self.module_loader.modules)}")
            print(f"   Event bus: {'Redis Streams' if self.event_bus.redis_connected else 'In-memory'}")
            print(f"   Workers: {sum(self.processor.worker_counts.values())}")
            print("="*60 + "\n")

        except Exception as e:
            self.state = SystemState.FAILED
            print(f"\n❌ Boot failed: {e}")
            raise

    async def shutdown(self) -> None:
        """
        Shutdown the kernel gracefully

        Stops all components in reverse order:
        1. Health monitor
        2. Modules
        3. Priority processor
        4. Event bus
        5. Config watcher
        """
        if self.state == SystemState.STOPPED:
            return

        print("\n" + "="*60)
        print("📴 UnityKernel Shutting Down")
        print("="*60)

        self.state = SystemState.SHUTTING_DOWN

        # Publish shutdown event
        if self.event_bus and self.event_bus.running:
            await self.event_bus.publish(Event(
                event_type=EventType.SYSTEM_SHUTDOWN.value,
                source="kernel",
                data={'timestamp': datetime.utcnow().isoformat()},
                priority=Priority.CRITICAL
            ))

        try:
            # Run shutdown handlers
            for handler in self._shutdown_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                except Exception as e:
                    print(f"⚠ Shutdown handler error: {e}")

            # 1. Stop health monitor
            if self.health_monitor:
                print("[1/5] Stopping health monitor...")
                await self.health_monitor.stop()

            # 2. Unload all modules
            if self.module_loader:
                print("[2/5] Unloading modules...")
                for module_name in list(self.module_loader.modules.keys()):
                    await self.module_loader.unload_module(module_name)

                await self.module_loader.stop_watching()

            # 3. Stop priority processor
            if self.processor:
                print("[3/5] Stopping priority processor...")
                await self.processor.stop()

            # 4. Stop event bus
            if self.event_bus:
                print("[4/5] Stopping event bus...")
                await self.event_bus.stop()

            # 5. Stop config watcher
            if self.config:
                print("[5/5] Stopping config watcher...")
                await self.config.stop_watching()

            self.state = SystemState.STOPPED

            print("\n" + "="*60)
            print("✅ UnityKernel Stopped")
            print("="*60 + "\n")

        except Exception as e:
            print(f"\n❌ Shutdown error: {e}")
            self.state = SystemState.FAILED
            raise

    async def run(self) -> None:
        """
        Boot and run kernel until interrupted

        This is the main entry point for running the kernel.
        Handles Ctrl+C gracefully.
        """
        # Setup signal handlers
        loop = asyncio.get_event_loop()

        def signal_handler():
            print("\n\nReceived interrupt signal...")
            self.shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        try:
            # Boot
            await self.boot()

            # Run forever (or until interrupted)
            print("Press Ctrl+C to shutdown\n")
            await self.shutdown_event.wait()

        except KeyboardInterrupt:
            print("\n\nKeyboard interrupt...")

        finally:
            # Shutdown
            await self.shutdown()

    # Public API methods

    async def publish(self, event: Event, persist: bool = True) -> None:
        """
        Publish an event to the bus

        Args:
            event: Event to publish
            persist: Whether to persist to Redis Streams
        """
        if not self.event_bus:
            raise RuntimeError("Kernel not booted")

        await self.event_bus.publish(event, persist=persist)

    def subscribe(self, event_pattern: str, handler: Callable) -> None:
        """
        Subscribe to events

        Args:
            event_pattern: Event pattern to match (supports wildcards)
            handler: Function to call when event occurs
        """
        if not self.event_bus:
            raise RuntimeError("Kernel not booted")

        self.event_bus.subscribe(event_pattern, handler)

    async def load_module(self, module_name: str) -> None:
        """
        Load a module by name

        Args:
            module_name: Name of module to load
        """
        if not self.module_loader:
            raise RuntimeError("Kernel not booted")

        await self.module_loader.load_module(module_name)

    async def unload_module(self, module_name: str) -> None:
        """
        Unload a module by name

        Args:
            module_name: Name of module to unload
        """
        if not self.module_loader:
            raise RuntimeError("Kernel not booted")

        await self.module_loader.unload_module(module_name)

    def get_health(self) -> Optional[HealthCheck]:
        """Get current system health"""
        if not self.health_monitor:
            return None

        return asyncio.create_task(self.health_monitor.check_health())

    def get_metrics(self) -> Optional[SystemMetrics]:
        """Get current system metrics"""
        if not self.health_monitor:
            return None

        return self.health_monitor.get_metrics()

    def get_status(self) -> dict:
        """Get comprehensive kernel status"""
        status = {
            'state': self.state.value,
            'boot_time': self.boot_time.isoformat() if self.boot_time else None,
            'uptime_seconds': (datetime.utcnow() - self.boot_time).total_seconds() if self.boot_time else 0
        }

        if self.module_loader:
            status['modules'] = self.module_loader.get_statistics()

        if self.event_bus:
            status['event_bus'] = self.event_bus.get_statistics()

        if self.processor:
            status['processor'] = self.processor.get_statistics()

        if self.health_monitor:
            status['health'] = self.health_monitor.get_health_summary()

        return status

    def on_shutdown(self, handler: Callable) -> None:
        """
        Register a shutdown handler

        Args:
            handler: Function to call during shutdown
        """
        self._shutdown_handlers.append(handler)
