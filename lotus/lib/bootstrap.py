"""
LOTUS Module Bootstrap - Phased Initialization System

This handles the sophisticated initialization of modules in phases,
allowing event-driven dependencies to be resolved naturally.
"""

from typing import Dict, List, Set, Optional
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
import logging
import asyncio

from .module import BaseModule, ModuleMetadata
from .exceptions import ModuleLoadError

class BootPhase(Enum):
    """Initialization phases for modules"""
    CORE_SERVICES = 1    # Memory, Providers - fundamental services
    CORE_LOGIC = 2       # Reasoning, Perception - core logic modules
    CAPABILITIES = 3     # Task-specific capability modules
    INTEGRATION = 4      # External system integration modules
    EXTENSIONS = 5       # Optional/community modules

@dataclass
class ModuleLoadInfo:
    """Information about a module during bootstrap"""
    name: str
    path: Path
    metadata: ModuleMetadata
    phase: BootPhase
    instance: Optional[BaseModule] = None
    ready: bool = False

class ModuleBootstrap:
    """
    Handles phased module initialization
    
    This class implements a more sophisticated boot process that:
    1. Groups modules by initialization phase
    2. Allows event-driven dependencies
    3. Supports health checks and readiness
    4. Provides graceful failure handling
    """
    
    def __init__(self, nucleus):
        self.nucleus = nucleus
        self.logger = logging.getLogger("lotus.bootstrap")
        self.modules: Dict[str, ModuleLoadInfo] = {}
        self.current_phase: Optional[BootPhase] = None
    
    def categorize_module(self, name: str, metadata: ModuleMetadata) -> BootPhase:
        """Determine which boot phase a module belongs in"""
        if name in {"memory", "providers"}:
            return BootPhase.CORE_SERVICES
        elif name in {"reasoning", "perception"}:
            return BootPhase.CORE_LOGIC
        elif metadata.type == "capability":
            return BootPhase.CAPABILITIES
        elif metadata.type == "integration":
            return BootPhase.INTEGRATION
        return BootPhase.EXTENSIONS

    async def prepare_modules(self, discovered_modules: Dict[str, Path]) -> None:
        """Prepare modules for phased loading"""
        for name, path in discovered_modules.items():
            try:
                manifest_path = path / "manifest.yaml"
                metadata = await self.nucleus._load_manifest(name, manifest_path)
                phase = self.categorize_module(name, metadata)
                self.modules[name] = ModuleLoadInfo(
                    name=name,
                    path=path,
                    metadata=metadata,
                    phase=phase
                )
            except Exception as e:
                self.logger.error(f"Failed to prepare module {name}: {e}", exc_info=True)
                if self.nucleus.config.get("nucleus.fail_on_module_error", False):
                    raise
    
    async def execute_phase(self, phase: BootPhase) -> None:
        """Execute a single boot phase"""
        self.current_phase = phase
        phase_modules = {
            name: info for name, info in self.modules.items()
            if info.phase == phase and not info.ready
        }
        
        if not phase_modules:
            return
        
        self.logger.info(f"Executing boot phase {phase.name} with {len(phase_modules)} modules")
        
        # Load all modules in this phase
        for name, info in phase_modules.items():
            try:
                instance = await self.nucleus._load_module(name, info.path)
                info.instance = instance
                self.nucleus.modules[name] = instance
                info.ready = True
                self.logger.info(f"Loaded module {name} in phase {phase.name}")
            except Exception as e:
                self.logger.error(f"Failed to load module {name} in phase {phase.name}: {e}", exc_info=True)
                if self.nucleus.config.get("nucleus.fail_on_module_error", False):
                    raise
        
        # Allow some time for event handlers to be registered
        await asyncio.sleep(0.5)
    
    async def boot(self, discovered_modules: Dict[str, Path]) -> List[str]:
        """Execute the complete boot sequence"""
        await self.prepare_modules(discovered_modules)
        
        # Execute each phase in order
        for phase in BootPhase:
            await self.execute_phase(phase)
        
        # Return the final load order
        load_order = []
        for phase in BootPhase:
            phase_modules = sorted(
                [name for name, info in self.modules.items() 
                 if info.phase == phase and info.ready],
                key=lambda x: self.modules[x].metadata.priority or "normal"
            )
            load_order.extend(phase_modules)
        
        return load_order