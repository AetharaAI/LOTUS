"""
Standard event handlers and base functionality for LOTUS modules.

This provides consistent patterns for module event handling and lifecycle management.
"""

from typing import Optional, Any, Dict
from lib.module import BaseModule

class StandardEventHandlers:
    """Mixin class providing standard event handlers for modules"""
    
    async def on_user_input(self, event: Dict[str, Any]) -> None:
        """Default handler for user input - modules can override if needed"""
        pass
        
    async def on_voice_input(self, event: Dict[str, Any]) -> None:
        """Default handler for voice input - modules can override if needed"""
        pass
        
    async def on_system_ready(self, event: Dict[str, Any]) -> None:
        """Default handler for system ready event - modules can override if needed"""
        pass

class EnhancedBaseModule(BaseModule, StandardEventHandlers):
    """
    Enhanced base module with standard event handlers and lifecycle management
    
    This provides a consistent foundation for all LOTUS modules with:
    - Standard event handlers
    - Service dependency management
    - Lifecycle hooks
    """
    
    async def _init(self) -> None:
        """Enhanced initialization with proper ordering"""
        # Register standard event handlers first
        await super()._init()
        
        # Initialize module-specific functionality
        if hasattr(self, 'initialize'):
            await self.initialize()
    
    async def shutdown(self) -> None:
        """Enhanced shutdown with proper ordering"""
        # Shutdown module-specific functionality
        if hasattr(self, 'cleanup'):
            await self.cleanup()
            
        # Call parent shutdown
        await super().shutdown()