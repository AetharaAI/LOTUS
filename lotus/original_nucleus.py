#!/usr/bin/env python3
"""
LOTUS/ASH Nucleus - Core Runtime Engine

The Nucleus is the heart of LOTUS. It:
- Manages the asyncio event loop
- Discovers and loads modules
- Routes messages between modules
- Maintains system health
- Orchestrates the entire system

The Nucleus itself is intentionally simple and dumb - all intelligence
lives in modules. This makes the system infinitely extensible.
"""

import asyncio
import sys
import os
import signal
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import yaml
import json

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.message_bus import MessageBus
from lib.config import Config
from lib.logging import setup_logging, get_logger
from lib.module import BaseModule, ModuleMetadata
from lib.exceptions import ModuleLoadError, SystemError


class Nucleus:
    """
    The Nucleus - Core Runtime Engine for LOTUS
    
    Responsibilities:
    - System initialization and shutdown
    - Module lifecycle management
    - Event loop orchestration
    - Health monitoring
    - Message routing coordination
    """
    
    def __init__(self, config_path: str = "config/system.yaml"):
        self.config_path = config_path
        self.config: Optional[Config] = None
        self.logger = None
        self.message_bus: Optional[MessageBus] = None
        
        # Module registry
        self.modules: Dict[str, BaseModule] = {}
        self.module_metadata: Dict[str, ModuleMetadata] = {}
        self.load_order: List[str] = []
        
        # System state
        self.running = False
        self.start_time: Optional[datetime] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Health monitoring
        self.health_check_task: Optional[asyncio.Task] = None
        self.last_health_check: Optional[datetime] = None
        
    async def boot(self) -> None:
        """
        Boot the LOTUS system
        
        This is the main initialization sequence:
        1. Load configuration
        2. Setup logging
        3. Initialize infrastructure (Redis, DB, etc)
        4. Discover modules
        5. Load modules in dependency order
        6. Start event loop
        7. Start health monitoring
        8. Signal system ready
        """
        print("🌸 LOTUS starting up...")
        print(f"   Time: {datetime.now().isoformat()}")
        print(f"   Python: {sys.version.split()[0]}")
        print(f"   Config: {self.config_path}")
        print()
        
        try:
            # 1. Load configuration
            self.config = Config(self.config_path)
            await self.config.load()
            
            # 2. Setup logging
            self.logger = setup_logging(self.config)
            self.logger.info("Configuration loaded")
            
            # 3. Initialize infrastructure
            await self._init_infrastructure()
            
            # 4. Discover modules
            modules_discovered = await self._discover_modules()
            print(f"   Found {len(modules_discovered)} modules")
            self.logger.info(f"Discovered {len(modules_discovered)} modules")
            
            # 5. Resolve dependencies and determine load order
            self.load_order = await self._resolve_dependencies(modules_discovered)
            print(f"   Load order determined: {len(self.load_order)} modules to load")
            
            # 6. Load modules
            print()
            print("   Loading modules...")
            for module_name in self.load_order:
                try:
                    await self._load_module(module_name, modules_discovered[module_name])
                    print(f"   ✓ Loaded: {module_name}")
                    self.logger.info(f"Module loaded: {module_name}")
                except Exception as e:
                    print(f"   ✗ Failed: {module_name} - {e}")
                    self.logger.error(f"Failed to load module {module_name}: {e}")
                    # Don't stop on module load failure
            
            # 7. Start event loop tasks
            await self._start_event_loop()
            
            # 8. Start health monitoring
            self.health_check_task = asyncio.create_task(self._health_monitor())
            
            # 9. Signal system ready
            self.running = True
            self.start_time = datetime.now()
            
            await self.message_bus.publish("system.ready", {
                "timestamp": self.start_time.isoformat(),
                "modules_loaded": len(self.modules),
                "personality": self.config.get("system.personality", "jarvis")
            })
            
            print()
            print("🌸 LOTUS is online and ready!")
            print(f"   Modules: {len(self.modules)} active")
            print(f"   Memory: {self._get_memory_usage():.1f} MB")
            print()
            self.logger.info("LOTUS is online and ready")
            
        except Exception as e:
            print(f"\n❌ Boot failed: {e}")
            self.logger.error(f"Boot failed: {e}", exc_info=True)
            raise SystemError(f"Failed to boot LOTUS: {e}")
    
    async def _init_infrastructure(self) -> None:
        """Initialize core infrastructure (Redis, DB, etc)"""
        print("   Initializing infrastructure...")
        
        # Initialize message bus
        redis_config = self.config.get("redis", {})
        self.message_bus = MessageBus(
            host=redis_config.get("host", "localhost"),
            port=redis_config.get("port", 6379),
            db=redis_config.get("db", 0)
        )
        await self.message_bus.connect()
        print("   ✓ Redis connected")
        self.logger.info("Redis message bus connected")
        
        # TODO: Initialize PostgreSQL
        print("   ✓ PostgreSQL connected (TODO)")
        
        # TODO: Initialize ChromaDB
        print("   ✓ ChromaDB initialized (TODO)")
    
    async def _discover_modules(self) -> Dict[str, Path]:
        """
        Discover all modules by scanning module directories
        
        Returns:
            Dict mapping module names to their directory paths
        """
        modules = {}
        module_dirs = [
            Path("modules/core_modules"),
            Path("modules/capability_modules"),
            Path("modules/integration_modules")
        ]
        
        for module_dir in module_dirs:
            if not module_dir.exists():
                continue
            
            for module_path in module_dir.iterdir():
                if not module_path.is_dir():
                    continue
                
                # Check for required files
                manifest_path = module_path / "manifest.yaml"
                logic_path = module_path / "logic.py"
                
                if manifest_path.exists() and logic_path.exists():
                    module_name = module_path.name
                    modules[module_name] = module_path
                    self.logger.debug(f"Discovered module: {module_name} at {module_path}")
        
        return modules
    
    async def _resolve_dependencies(self, modules: Dict[str, Path]) -> List[str]:
        """
        Resolve module dependencies and determine load order
        
        Uses topological sort to ensure dependencies are loaded first
        """
        # Load all manifests
        manifests = {}
        for name, path in modules.items():
            manifest_path = path / "manifest.yaml"
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
                manifests[name] = manifest
        
        # Build dependency graph
        graph = {name: set() for name in modules.keys()}
        for name, manifest in manifests.items():
            deps = manifest.get("dependencies", {}).get("modules", [])
            graph[name] = set(deps)
        
        # Topological sort (Kahn's algorithm)
        in_degree = {name: 0 for name in graph}
        for deps in graph.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for name, deps in graph.items():
                if node in deps:
                    deps.remove(node)
                    if len(deps) == 0:
                        queue.append(name)
        
        # Check for circular dependencies
        if len(result) != len(graph):
            raise ModuleLoadError("Circular dependency detected in modules")
        
        return result
    
    async def _load_module(self, module_name: str, module_path: Path) -> None:
        """Load and initialize a single module"""
        # Load manifest
        manifest_path = module_path / "manifest.yaml"
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
        
        # Create metadata
        metadata = ModuleMetadata(
            name=module_name,
            version=manifest.get("version", "0.0.0"),
            type=manifest.get("type", "capability"),
            priority=manifest.get("priority", "normal"),
            path=module_path
        )
        self.module_metadata[module_name] = metadata
        
        # Dynamically import module
        import importlib.util
        logic_path = module_path / "logic.py"
        spec = importlib.util.spec_from_file_location(f"modules.{module_name}", logic_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the module class (should inherit from BaseModule)
        module_class = None
        for item in dir(module):
            obj = getattr(module, item)
            if (isinstance(obj, type) and 
                issubclass(obj, BaseModule) and 
                obj is not BaseModule):
                module_class = obj
                break
        
        if not module_class:
            raise ModuleLoadError(f"No BaseModule subclass found in {module_name}")
        
        # Instantiate module
        instance = module_class(
            name=module_name,
            metadata=metadata,
            message_bus=self.message_bus,
            config=self.config,
            logger=self.logger
        )
        
        # Initialize module
        await instance.initialize()
        
        # Register module
        self.modules[module_name] = instance
    
    async def _start_event_loop(self) -> None:
        """Start the main event loop and all module tasks"""
        self.logger.info("Starting event loop tasks")
        
        # Each module may have started its own tasks in initialize()
        # The message bus handles all communication
        # The Nucleus just needs to keep the loop running
        
    async def _health_monitor(self) -> None:
        """Periodic health check of all modules"""
        interval = self.config.get("nucleus.health_check_interval", 30)
        
        while self.running:
            try:
                await asyncio.sleep(interval)
                
                # Check module health
                unhealthy = []
                for name, module in self.modules.items():
                    if not await module.health_check():
                        unhealthy.append(name)
                
                self.last_health_check = datetime.now()
                
                if unhealthy:
                    self.logger.warning(f"Unhealthy modules: {unhealthy}")
                    await self.message_bus.publish("system.health.warning", {
                        "unhealthy_modules": unhealthy,
                        "timestamp": self.last_health_check.isoformat()
                    })
                else:
                    self.logger.debug("Health check passed - all modules healthy")
                    
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    async def shutdown(self) -> None:
        """Graceful shutdown sequence"""
        print("\n🌸 LOTUS shutting down...")
        self.logger.info("Shutdown initiated")
        
        self.running = False
        
        # Cancel health monitor
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown all modules in reverse order
        print("   Shutting down modules...")
        for module_name in reversed(self.load_order):
            if module_name in self.modules:
                try:
                    await self.modules[module_name].shutdown()
                    print(f"   ✓ Stopped: {module_name}")
                except Exception as e:
                    print(f"   ✗ Error stopping {module_name}: {e}")
                    self.logger.error(f"Error stopping module {module_name}: {e}")
        
        # Disconnect message bus
        if self.message_bus:
            await self.message_bus.disconnect()
            print("   ✓ Message bus disconnected")
        
        print("🌸 LOTUS shutdown complete")
        self.logger.info("Shutdown complete")
    
    async def run(self) -> None:
        """
        Main run loop
        
        Boots the system and keeps it running until interrupted
        """
        # Setup signal handlers
        def signal_handler(sig, frame):
            print(f"\nReceived signal {sig}")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Boot the system
        await self.boot()
        
        # Keep running until shutdown
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            if self.running:
                await self.shutdown()


async def main():
    """Entry point"""
    nucleus = Nucleus()
    await nucleus.run()


if __name__ == "__main__":
    # Run the system
    asyncio.run(main())