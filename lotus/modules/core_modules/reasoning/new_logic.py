"""
Updated reasoning engine implementation using service dependencies
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from lotus.lib.module import BaseModule
from lotus.lib.decorators import on_event, tool
from lotus.lib.service_deps import requires_services
from lotus.lib.utils import generate_id, timestamp_now

class ReasoningEngine(BaseModule):
    """LOTUS Reasoning Engine with proper service dependencies"""
    
    def __init__(self, name: str, metadata: Dict, message_bus: Any, config: Any, logger: logging.Logger):
        super().__init__(name, metadata, message_bus, config, logger)
        self.logger = logging.getLogger(f"lotus.module.{name}")

    @requires_services('memory', 'providers')
    async def think(self, context: Dict) -> Dict:
        """Process input using memory and providers"""
        # Services are guaranteed to be available here
        result = await self.providers.complete(
            messages=[{"content": "Think about: " + context['input']}]
        )
        
        await self.memory.store({
            "type": "thought",
            "content": result
        })
        
        return {"response": result}
    
    @on_event("perception.user_input")
    @requires_services('memory', 'providers')
    async def on_user_input(self, event):
        """Handle user input"""
        thought = await self.think(event.data)
        await self.message_bus.publish("action.respond", thought)