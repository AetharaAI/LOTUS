"""
Example Module: Monitor

Demonstrates:
- Event subscription
- Event handling
- Module dependencies
"""

import sys
from pathlib import Path

# Add kernel to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core import BaseModule, Event


class MonitorModule(BaseModule):
    """
    Monitor module

    Subscribes to heartbeat events and logs them.
    Demonstrates event subscription and handling.
    """

    async def initialize(self) -> None:
        """Initialize the monitor module"""
        # Subscribe to heartbeat events
        self.subscribe("heartbeat.tick", self.on_heartbeat)

        # Track heartbeat count
        self.heartbeat_count = 0

        print(f"📊 Monitor module initialized")

    async def on_heartbeat(self, event: Event) -> None:
        """
        Handle heartbeat events

        Args:
            event: Heartbeat event
        """
        self.heartbeat_count += 1

        beat_number = event.data.get('beat_number', 0)
        timestamp = event.data.get('timestamp', 'unknown')

        print(f"📊 Monitor received heartbeat #{beat_number} (total: {self.heartbeat_count})")

    async def stop(self) -> None:
        """Stop the monitor"""
        print(f"📊 Monitor stopping (received {self.heartbeat_count} heartbeats total)")
        await super().stop()
