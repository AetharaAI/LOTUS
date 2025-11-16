"""
Service Registry for LOTUS

This manages service registration and access in a way that avoids
circular dependencies by using event-based communication.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import asyncio
import logging

@dataclass
class ServiceRegistration:
    """Information about a registered service"""
    name: str
    instance: Any
    ready: bool = False
    dependents: list = None

    def __post_init__(self):
        if self.dependents is None:
            self.dependents = []

class ServiceRegistry:
    """
    Manages service registration and access
    
    Instead of direct access, services communicate via events:
    - service.request.<service_name>
    - service.response.<service_name>
    """
    
    def __init__(self, message_bus):
        self.services: Dict[str, ServiceRegistration] = {}
        self.message_bus = message_bus
        self.logger = logging.getLogger("lotus.services")
        
    async def register(self, name: str, instance: Any) -> None:
        """Register a service"""
        if name in self.services:
            self.logger.warning(f"Service {name} already registered. Updating registration.")
        
        self.services[name] = ServiceRegistration(name=name, instance=instance)
        self.logger.info(f"Service {name} registered")
        
        # Publish service availability
        await self.message_bus.publish(f"service.available.{name}", {
            "service": name,
            "status": "ready"
        })
    
    async def request(self, service: str, method: str, **kwargs) -> Any:
        """Request a service operation via events"""
        if service not in self.services:
            raise KeyError(f"Service {service} not registered")
            
        request_id = f"req_{service}_{method}_{id(kwargs)}"
        
        # Publish request
        await self.message_bus.publish(f"service.request.{service}", {
            "id": request_id,
            "method": method,
            "params": kwargs
        })
        
        # Wait for response
        try:
            response = await self.message_bus.wait_for(
                f"service.response.{request_id}",
                timeout=30.0
            )
            return response.get("result")
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout waiting for {service}.{method} response")
            raise
    
    def get(self, name: str) -> Optional[Any]:
        """Get a service instance directly (use with caution)"""
        if name in self.services:
            return self.services[name].instance
        return None
    
    async def wait_for_service(self, name: str, timeout: float = 30.0) -> Any:
        """Wait for a service to become available"""
        if name in self.services:
            return self.services[name].instance
            
        try:
            await self.message_bus.wait_for(
                f"service.available.{name}",
                timeout=timeout
            )
            return self.services[name].instance
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout waiting for service {name}")
            raise