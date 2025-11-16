"""
Example Module: Heartbeat

Demonstrates:
- Module lifecycle
- Event publishing
- Periodic tasks
- Configuration access
"""

import asyncio
from datetime import datetime

import sys
from pathlib import Path

# Add kernel to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core import BaseModule, Event, Priority


class HeartbeatModule(BaseModule):
    """
    Simple heartbeat module

    Publishes periodic heartbeat events to demonstrate the module system.
    """

    async def initialize(self) -> None:
        """Initialize the heartbeat module"""
        # Get interval from config
        self.interval = self.get_config('interval', 5)

        print(f"♥ Heartbeat module initialized (interval: {self.interval}s)")

    async def start(self) -> None:
        """Start the heartbeat"""
        await super().start()

        # Start heartbeat task
        self.create_task(self._heartbeat_loop())

        print(f"♥ Heartbeat started")

    async def _heartbeat_loop(self) -> None:
        """Background task that publishes heartbeats"""
        beat_count = 0

        while self.running:
            try:
                await asyncio.sleep(self.interval)

                beat_count += 1

                # Publish heartbeat event
                await self.publish(Event(
                    event_type="heartbeat.tick",
                    source=self.info.name,
                    data={
                        'beat_number': beat_count,
                        'timestamp': datetime.utcnow().isoformat(),
                        'interval': self.interval
                    },
                    priority=Priority.LOW
                ))

                print(f"♥ Heartbeat #{beat_count}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠ Heartbeat error: {e}")

    async def stop(self) -> None:
        """Stop the heartbeat"""
        print(f"♥ Heartbeat stopping...")
        await super().stop()
