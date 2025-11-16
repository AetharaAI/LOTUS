"""
UnityKernel Module Loader

Discovers, loads, and manages modules with hot-reload support.
Handles dependency resolution and lifecycle management.
"""

import asyncio
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import yaml

from .types import ModuleInfo, ModuleState, Event, EventType, Priority
from .base_module import BaseModule


class ModuleLoader:
    """
    Module discovery and lifecycle manager

    Features:
    - Auto-discovery from configured paths
    - Dependency resolution (topological sort)
    - Hot-reload support (watch for changes)
    - Graceful load/unload
    - Health-based auto-restart
    """

    def __init__(self, config: any, event_bus: any):
        """
        Initialize module loader

        Args:
            config: Config manager reference
            event_bus: Event bus reference
        """
        self.config = config
        self.event_bus = event_bus

        # Module registry
        self.modules: Dict[str, BaseModule] = {}
        self.module_info: Dict[str, ModuleInfo] = {}

        # Discovery
        self.discovery_paths: List[Path] = []
        self.discovered_modules: Dict[str, Path] = {}

        # Hot-reload
        self.watch_task: Optional[asyncio.Task] = None
        self.watching = False
        self.module_mtimes: Dict[str, float] = {}

    async def discover(self) -> List[str]:
        """
        Discover modules from configured paths

        Returns:
            List of discovered module names
        """
        self.discovery_paths = [
            Path(p) for p in self.config.get('modules.discovery_paths', ['./modules'])
        ]

        discovered = []

        for base_path in self.discovery_paths:
            if not base_path.exists():
                print(f"⚠ Module path not found: {base_path}")
                continue

            # Find all manifest.yaml files
            for manifest_path in base_path.rglob('manifest.yaml'):
                module_dir = manifest_path.parent

                try:
                    # Load manifest
                    info = await self._load_manifest(manifest_path)

                    # Register discovered module
                    self.discovered_modules[info.name] = module_dir
                    self.module_info[info.name] = info
                    discovered.append(info.name)

                    # Track modification time for hot-reload
                    logic_file = module_dir / 'module.py'
                    if logic_file.exists():
                        self.module_mtimes[info.name] = logic_file.stat().st_mtime

                except Exception as e:
                    print(f"⚠ Failed to load manifest {manifest_path}: {e}")

        print(f"✓ Discovered {len(discovered)} modules")
        return discovered

    async def _load_manifest(self, manifest_path: Path) -> ModuleInfo:
        """Load module info from manifest file"""
        with open(manifest_path, 'r') as f:
            data = yaml.safe_load(f)

        return ModuleInfo(
            name=data['name'],
            version=data.get('version', '1.0.0'),
            module_type=data.get('type', 'unknown'),
            description=data.get('description', ''),
            author=data.get('author', ''),
            depends_on=data.get('dependencies', {}).get('modules', []),
            optional_depends=data.get('optional_dependencies', {}).get('modules', []),
            provides=data.get('provides', []),
            consumes=data.get('consumes', []),
            config_schema=data.get('config_schema', {}),
            config=data.get('config', {}),
            priority=Priority[data.get('priority', 'NORMAL').upper()],
            hot_reload=data.get('hot_reload', False),
            auto_restart=data.get('auto_restart', True)
        )

    async def load_all(self) -> None:
        """Load all discovered modules in dependency order"""
        if not self.discovered_modules:
            await self.discover()

        # Resolve load order
        load_order = self._resolve_dependencies()

        # Load modules
        for module_name in load_order:
            try:
                await self.load_module(module_name)
            except Exception as e:
                print(f"❌ Failed to load module {module_name}: {e}")
                self.module_info[module_name].state = ModuleState.FAILED
                self.module_info[module_name].error = str(e)

    def _resolve_dependencies(self) -> List[str]:
        """
        Resolve module load order using topological sort

        Returns:
            List of module names in load order
        """
        # Build dependency graph
        graph: Dict[str, Set[str]] = {}

        for name, info in self.module_info.items():
            # Only include dependencies that exist
            deps = set(d for d in info.depends_on if d in self.module_info)
            graph[name] = deps

        # Topological sort (Kahn's algorithm)
        in_degree = {name: len(deps) for name, deps in graph.items()}
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Sort by priority before processing
            queue.sort(key=lambda n: self.module_info[n].priority.value)

            node = queue.pop(0)
            result.append(node)

            # Reduce in-degree for dependents
            for dependent in graph.keys():
                if node in graph[dependent]:
                    graph[dependent].remove(node)
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Check for circular dependencies
        if len(result) != len(graph):
            unresolved = set(graph.keys()) - set(result)
            raise RuntimeError(f"Circular dependency detected in modules: {unresolved}")

        return result

    async def load_module(self, module_name: str) -> BaseModule:
        """
        Load and initialize a single module

        Args:
            module_name: Name of module to load

        Returns:
            Loaded module instance
        """
        if module_name in self.modules:
            print(f"⚠ Module already loaded: {module_name}")
            return self.modules[module_name]

        info = self.module_info.get(module_name)
        if not info:
            raise ValueError(f"Module not discovered: {module_name}")

        module_dir = self.discovered_modules[module_name]

        # Update state
        info.state = ModuleState.LOADING

        try:
            # Add module directory to Python path
            sys.path.insert(0, str(module_dir))

            # Import module
            module_file = module_dir / 'module.py'
            if not module_file.exists():
                raise FileNotFoundError(f"No module.py found in {module_dir}")

            # Load Python module
            spec = importlib.util.spec_from_file_location(
                f"unity_modules.{module_name}",
                module_file
            )
            py_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(py_module)

            # Find module class (should inherit from BaseModule)
            module_class = None
            for item_name in dir(py_module):
                item = getattr(py_module, item_name)
                if (isinstance(item, type) and
                    issubclass(item, BaseModule) and
                    item is not BaseModule):
                    module_class = item
                    break

            if not module_class:
                raise ValueError(f"No BaseModule subclass found in {module_name}")

            # Instantiate module
            instance = module_class(info, self.config, self.event_bus)

            # Run lifecycle
            await instance._lifecycle_wrapper()

            # Register module
            self.modules[module_name] = instance
            info.state = ModuleState.RUNNING
            info.loaded_at = datetime.utcnow()

            # Publish event
            await self.event_bus.publish(Event(
                event_type=EventType.MODULE_LOADED.value,
                source="module_loader",
                data={
                    'module_name': module_name,
                    'module_type': info.module_type,
                    'version': info.version
                }
            ), persist=False)

            print(f"✓ Loaded module: {module_name} ({info.module_type})")
            return instance

        except Exception as e:
            info.state = ModuleState.FAILED
            info.error = str(e)

            # Publish failure event
            await self.event_bus.publish(Event(
                event_type=EventType.MODULE_FAILED.value,
                source="module_loader",
                data={
                    'module_name': module_name,
                    'error': str(e)
                },
                priority=Priority.HIGH
            ), persist=True)

            raise

    async def unload_module(self, module_name: str) -> None:
        """
        Unload a module gracefully

        Args:
            module_name: Name of module to unload
        """
        if module_name not in self.modules:
            print(f"⚠ Module not loaded: {module_name}")
            return

        module = self.modules[module_name]
        info = self.module_info[module_name]

        try:
            # Stop module
            await module.stop()

            # Remove from registry
            del self.modules[module_name]
            info.state = ModuleState.UNLOADED

            # Publish event
            await self.event_bus.publish(Event(
                event_type=EventType.MODULE_STOPPED.value,
                source="module_loader",
                data={'module_name': module_name}
            ), persist=False)

            print(f"✓ Unloaded module: {module_name}")

        except Exception as e:
            print(f"❌ Failed to unload module {module_name}: {e}")
            info.error = str(e)

    async def reload_module(self, module_name: str) -> None:
        """
        Hot-reload a module

        Args:
            module_name: Name of module to reload
        """
        print(f"🔄 Reloading module: {module_name}")

        # Unload
        if module_name in self.modules:
            await self.unload_module(module_name)

        # Clear import cache
        module_key = f"unity_modules.{module_name}"
        if module_key in sys.modules:
            del sys.modules[module_key]

        # Reload manifest (config might have changed)
        module_dir = self.discovered_modules[module_name]
        manifest_path = module_dir / 'manifest.yaml'
        new_info = await self._load_manifest(manifest_path)
        self.module_info[module_name] = new_info

        # Load
        await self.load_module(module_name)

        print(f"✓ Module reloaded: {module_name}")

    async def start_watching(self, interval: float = 1.0) -> None:
        """
        Start watching modules for changes (hot-reload)

        Args:
            interval: Check interval in seconds
        """
        self.watching = True
        self.watch_task = asyncio.create_task(self._watch_loop(interval))
        print(f"✓ Module hot-reload enabled (checking every {interval}s)")

    async def stop_watching(self) -> None:
        """Stop watching modules"""
        self.watching = False
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass

    async def _watch_loop(self, interval: float) -> None:
        """Background task that watches for module changes"""
        while self.watching:
            try:
                await asyncio.sleep(interval)

                # Check each loaded module
                for module_name, module_dir in self.discovered_modules.items():
                    info = self.module_info.get(module_name)

                    # Only hot-reload if enabled
                    if not info or not info.hot_reload:
                        continue

                    logic_file = module_dir / 'module.py'
                    if not logic_file.exists():
                        continue

                    current_mtime = logic_file.stat().st_mtime
                    last_mtime = self.module_mtimes.get(module_name, 0)

                    if current_mtime > last_mtime:
                        print(f"🔄 Detected change in {module_name}")
                        await self.reload_module(module_name)
                        self.module_mtimes[module_name] = current_mtime

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠ Module watch error: {e}")

    def get_loaded_modules(self) -> List[str]:
        """Get list of loaded module names"""
        return list(self.modules.keys())

    def get_module(self, name: str) -> Optional[BaseModule]:
        """Get module instance by name"""
        return self.modules.get(name)

    def get_statistics(self) -> Dict[str, any]:
        """Get loader statistics"""
        state_counts = {}
        for info in self.module_info.values():
            state = info.state.value
            state_counts[state] = state_counts.get(state, 0) + 1

        return {
            'discovered': len(self.discovered_modules),
            'loaded': len(self.modules),
            'states': state_counts,
            'hot_reload_enabled': self.watching
        }
