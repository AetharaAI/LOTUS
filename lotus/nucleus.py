#!/usr/bin/env python3
"""
LOTUS/ASH Nucleus - Core Runtime Engine (FIXED VERSION)

This version includes proper error handling for malformed manifest files
and will help identify which module has the issue.
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
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
            print("   Initializing infrastructure...")
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
            print(f"   Loaded {len(self.modules)} modules successfully")
            print(f"   Personality: {self.config.get('system.personality', 'jarvis')}")
            print()
            print("   Press Ctrl+C to shutdown")
            print()
            
        except Exception as e:
            print(f"❌ Boot failed: {e}")
            self.logger.error(f"Boot failed: {e}")
            self.logger.debug(traceback.format_exc())
            raise SystemError(f"Failed to boot LOTUS: {e}")
    
    async def _init_infrastructure(self) -> None:
        """Initialize infrastructure components (Redis, DB, etc)"""
        import os
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        try:
            # Initialize message bus (Redis)
            self.message_bus = MessageBus(self.config)
            await self.message_bus.connect()
            print("   ✓ Redis connected")
            self.logger.info("Redis message bus connected")

            # Expose Redis client for modules
            self.config.set("services.redis", self.message_bus.redis)

            # Initialize PostgreSQL
            db_url = os.environ.get("DATABASE_URL_ASYNC") or os.environ.get("DATABASE_URL")
            if not db_url:
                raise RuntimeError("DATABASE_URL_ASYNC or DATABASE_URL is required")

            self.db_engine = create_async_engine(db_url, pool_pre_ping=True)

            # Quick liveness ping
            async with self.db_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            # Publish to config for modules
            self.config.set("services.db_engine", self.db_engine)
            print("   ✓ PostgreSQL connected")
            self.logger.info("PostgreSQL connected")

            # Initialize ChromaDB
            import chromadb
            from chromadb.config import Settings
            chroma_path = os.environ.get("CHROMA_PATH", "./var/chroma")
            self.chroma = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
            # Optional: create default collection
            self.chroma.get_or_create_collection("lotus_memory")
            self.config.set("services.chroma", self.chroma)
            print("   ✓ ChromaDB initialized")
            self.logger.info("ChromaDB initialized")

        except Exception as e:
            self.logger.error(f"Infrastructure init failed: {e}")
            raise
    
    async def _discover_modules(self) -> Dict[str, Path]:
        """
        Discover all available modules
        
        Modules can be in:
        - modules/core_modules/ (system critical)
        - modules/capabilities/ (optional features)
        - modules/integrations/ (external services)
        - modules/personalities/ (personality modules)
        """
        modules = {}
        base_path = Path(__file__).parent
        
        module_dirs = [
            base_path / "modules" / "core_modules",
            base_path / "modules" / "capabilities",
            base_path / "modules" / "integrations",
            base_path / "modules" / "personalities"
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
        # Load all manifests with validation
        manifests = {}
        for name, path in modules.items():
            manifest_path = path / "manifest.yaml"
            try:
                with open(manifest_path, 'r') as f:
                    manifest = yaml.safe_load(f)
                    
                    # CRITICAL FIX: Validate manifest structure
                    if manifest is None:
                        print(f"   ⚠️  WARNING: Empty manifest in {name} at {manifest_path}")
                        manifest = {}  # Use empty dict as default
                    elif isinstance(manifest, list):
                        print(f"   ⚠️  WARNING: Invalid manifest format in {name} at {manifest_path}")
                        print(f"      Manifest is a list but should be a dictionary (YAML mapping)")
                        print(f"      Please fix the manifest.yaml file to use proper YAML structure")
                        print(f"      Example structure:")
                        print(f"      name: {name}")
                        print(f"      version: 1.0.0")
                        print(f"      dependencies:")
                        print(f"        modules: []")
                        # Try to salvage if possible
                        manifest = {"name": name, "version": "0.0.0"}
                    elif not isinstance(manifest, dict):
                        print(f"   ⚠️  WARNING: Unexpected manifest type in {name}: {type(manifest)}")
                        manifest = {"name": name, "version": "0.0.0"}
                    
                    # Ensure manifest has required fields
                    if "name" not in manifest:
                        manifest["name"] = name
                    if "version" not in manifest:
                        manifest["version"] = "0.0.0"
                    if "dependencies" not in manifest:
                        manifest["dependencies"] = {}
                    
                    manifests[name] = manifest
                    
            except yaml.YAMLError as e:
                print(f"   ⚠️  WARNING: Failed to parse manifest for {name}: {e}")
                print(f"      File: {manifest_path}")
                print(f"      Using default manifest for this module")
                manifests[name] = {
                    "name": name,
                    "version": "0.0.0",
                    "dependencies": {}
                }
            except Exception as e:
                print(f"   ⚠️  WARNING: Unexpected error loading manifest for {name}: {e}")
                print(f"      File: {manifest_path}")
                manifests[name] = {
                    "name": name,
                    "version": "0.0.0",
                    "dependencies": {}
                }
        
        # Build dependency graph
        graph = {name: set() for name in modules.keys()}
        for name, manifest in manifests.items():
            # Safe navigation with defaults
            dependencies = manifest.get("dependencies", {})
            if isinstance(dependencies, dict):
                module_deps = dependencies.get("modules", [])
                if isinstance(module_deps, list):
                    # Only include dependencies that actually exist
                    valid_deps = [dep for dep in module_deps if dep in modules]
                    if len(module_deps) != len(valid_deps):
                        missing = set(module_deps) - set(valid_deps)
                        print(f"   ⚠️  WARNING: Module {name} has missing dependencies: {missing}")
                    graph[name] = set(valid_deps)
                else:
                    print(f"   ⚠️  WARNING: Invalid dependencies.modules in {name} (expected list)")
                    graph[name] = set()
            else:
                print(f"   ⚠️  WARNING: Invalid dependencies format in {name} (expected dict)")
                graph[name] = set()
        
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
            
            # Remove edges from this node
            for dependent in list(graph.keys()):
                if node in graph[dependent]:
                    graph[dependent].remove(node)
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # Check for circular dependencies
        if len(result) != len(modules):
            unresolved = set(modules.keys()) - set(result)
            raise ModuleLoadError(f"Circular dependency detected in modules: {unresolved}")
        
        return result
    
    async def _load_module(self, module_name: str, module_path: Path) -> None:
        """Load and initialize a single module"""
        # Load manifest
        manifest_path = module_path / "manifest.yaml"
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
            # Apply same validation as in _resolve_dependencies
            if not isinstance(manifest, dict):
                manifest = {"name": module_name, "version": "0.0.0"}
        
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
        if spec is None or spec.loader is None:
            raise ModuleLoadError(f"Failed to load module spec for {module_name}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"modules.{module_name}"] = module
        spec.loader.exec_module(module)
        
        # Find the Module class
        module_class = None
        for item_name in dir(module):
            item = getattr(module, item_name)
            if isinstance(item, type) and issubclass(item, BaseModule) and item != BaseModule:
                module_class = item
                break
        
        if not module_class:
            raise ModuleLoadError(f"No Module class found in {module_name}")
        
        # Instantiate and initialize
        instance = module_class(metadata.name, metadata, self.message_bus, self.config, self.logger)
        await instance._init()
        
        # Store module
        self.modules[module_name] = instance
        
        # Subscribe to patterns
        subscriptions = manifest.get("subscriptions", [])
        for sub in subscriptions:
            if isinstance(sub, dict) and "pattern" in sub and "handler" in sub:
                pattern = sub["pattern"]
                handler_name = sub["handler"]
                if hasattr(instance, handler_name):
                    handler = getattr(instance, handler_name)
                    await self.message_bus.subscribe(pattern, handler)
                    self.logger.debug(f"Module {module_name} subscribed to {pattern}")
    
    async def _start_event_loop(self) -> None:
        """Start the main event loop tasks"""
        self.event_loop = asyncio.get_running_loop()
        
        # Setup signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            self.event_loop.add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown())
            )
    
    async def _health_monitor(self) -> None:
        """Monitor system and module health"""
        while self.running:
            try:
                # Check each module
                for name, module in self.modules.items():
                    if hasattr(module, 'health_check'):
                        try:
                            health = await module.health_check()
                            # Handle both boolean and dict returns
                            if isinstance(health, dict):
                                if not health.get("healthy", True):
                                    self.logger.warning(f"Module {name} unhealthy: {health}")
                            elif isinstance(health, bool):
                                if not health:
                                    self.logger.warning(f"Module {name} unhealthy: returned False")
                            else:
                                self.logger.warning(f"Module {name} health check returned unexpected type: {type(health)}")
                        except Exception as e:
                            self.logger.error(f"Health check failed for {name}: {e}")
                
                self.last_health_check = datetime.now()
                
                # Sleep for health check interval
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)  # Retry after error
    
    async def shutdown(self) -> None:
        """Gracefully shutdown LOTUS"""
        print("\n📴 Shutting down LOTUS...")
        self.logger.info("Shutdown initiated")
        
        self.running = False
        
        # Cancel health monitoring
        if self.health_check_task:
            self.health_check_task.cancel()
        
        # Shutdown modules in reverse order
        for module_name in reversed(self.load_order):
            if module_name in self.modules:
                try:
                    await self.modules[module_name].shutdown()
                    self.logger.info(f"Module {module_name} shutdown")
                except Exception as e:
                    self.logger.error(f"Error shutting down {module_name}: {e}")
        
        # Disconnect infrastructure
        if self.message_bus:
            await self.message_bus.disconnect()

        # Dispose database engine
        if hasattr(self, "db_engine"):
            await self.db_engine.dispose()

        print("👋 LOTUS shutdown complete")
    
    async def run(self) -> None:
        """Run the nucleus until shutdown"""
        await self.boot()
        
        # Keep running until shutdown
        while self.running:
            await asyncio.sleep(1)
    
    def health(self) -> dict:
        """Get system health status"""
        return {
            "running": self.running,
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "modules_loaded": len(self.modules),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None
        }


# Entry point
async def main():
    nucleus = Nucleus()
    try:
        await nucleus.run()
    except KeyboardInterrupt:
        print("\n💔 Interrupted by user")
    finally:
        await nucleus.shutdown()


if __name__ == "__main__":
    asyncio.run(main())