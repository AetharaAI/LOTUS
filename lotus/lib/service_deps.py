"""
Service dependency management for LOTUS modules
"""

from functools import wraps
from typing import List, Optional, Any
import asyncio
import logging

def requires_services(*service_names: str):
    """
    Decorator to declare service dependencies
    
    Usage:
    @requires_services('memory', 'providers')
    async def my_method(self):
        # Services will be available when this runs
        await self.memory.store(...)
    """
    def decorator(f):
        @wraps(f)
        async def wrapper(self, *args, **kwargs):
            # Ensure all required services are ready
            for service in service_names:
                if not hasattr(self, service) or getattr(self, service) is None:
                    try:
                        setattr(self, service, 
                            await self.service_registry.wait_for_service(service))
                    except asyncio.TimeoutError:
                        self.logger.error(f"Required service {service} not available")
                        raise RuntimeError(f"Required service {service} not available")
            return await f(self, *args, **kwargs)
        return wrapper
    return decorator