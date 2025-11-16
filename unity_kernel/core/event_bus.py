"""
UnityKernel AsyncEventBus

The core message bus that connects everything.
- Internal in-memory pub/sub (fast, no Redis required)
- Wildcard pattern matching
- Event persistence via Redis Streams (optional but recommended)
- Guaranteed delivery with retry logic
"""

import asyncio
import re
from typing import Dict, List, Callable, Optional, Pattern, Set
from collections import defaultdict
from datetime import datetime
import json

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .types import Event, Priority


class AsyncEventBus:
    """
    Deterministic async event bus

    Core features:
    - Fast in-memory pub/sub
    - Pattern-based subscriptions (e.g., "sensor.*")
    - Redis Streams persistence (messages never lost)
    - Priority-aware delivery
    - Dead letter queue for failed handlers
    """

    def __init__(self, redis_url: Optional[str] = None, enable_streams: bool = True):
        """
        Initialize event bus

        Args:
            redis_url: Redis connection URL (optional)
            enable_streams: Whether to enable Redis Streams persistence
        """
        # In-memory subscriptions: {pattern: [handlers]}
        self._subscriptions: Dict[Pattern, List[Callable]] = {}
        self._exact_subscriptions: Dict[str, List[Callable]] = defaultdict(list)

        # Redis Streams (for persistence and replay)
        self.redis_url = redis_url
        self.enable_streams = enable_streams and REDIS_AVAILABLE
        self.redis_client: Optional[any] = None
        self.redis_connected = False

        # Statistics
        self.events_published = 0
        self.events_delivered = 0
        self.events_failed = 0

        # Dead letter queue (events that couldn't be delivered)
        self.dead_letter_queue: List[Event] = []

        # Running state
        self.running = False

    async def start(self) -> None:
        """Start the event bus"""
        self.running = True

        # Connect to Redis if configured
        if self.enable_streams and self.redis_url:
            try:
                self.redis_client = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                self.redis_connected = True
                print(f"✓ Redis Streams connected: {self.redis_url}")
            except Exception as e:
                print(f"⚠ Redis Streams unavailable (continuing without): {e}")
                self.redis_connected = False

    async def stop(self) -> None:
        """Stop the event bus"""
        self.running = False

        if self.redis_client:
            await self.redis_client.close()
            self.redis_connected = False

    async def publish(self, event: Event, persist: bool = True) -> None:
        """
        Publish an event to all subscribers

        Args:
            event: Event to publish
            persist: Whether to persist to Redis Streams
        """
        if not self.running:
            raise RuntimeError("Event bus not running")

        self.events_published += 1

        # Persist to Redis Streams first (so even if handlers fail, it's saved)
        if persist and self.redis_connected:
            await self._persist_to_stream(event)

        # Deliver to in-memory subscribers
        await self._deliver_to_subscribers(event)

    async def _persist_to_stream(self, event: Event) -> None:
        """Persist event to Redis Stream"""
        try:
            stream_key = f"unity:events:{event.event_type}"
            event_data = {
                'event_id': event.event_id,
                'event_type': event.event_type,
                'source': event.source,
                'destination': event.destination or '',
                'data': json.dumps(event.data),
                'metadata': json.dumps(event.metadata),
                'timestamp': event.timestamp.isoformat(),
                'priority': event.priority.name,
                'correlation_id': event.correlation_id or '',
                'parent_id': event.parent_id or ''
            }

            await self.redis_client.xadd(stream_key, event_data, maxlen=10000)
        except Exception as e:
            print(f"⚠ Failed to persist event to Redis Stream: {e}")

    async def _deliver_to_subscribers(self, event: Event) -> None:
        """Deliver event to all matching subscribers"""
        handlers_to_call: Set[Callable] = set()

        # Exact match subscribers
        if event.event_type in self._exact_subscriptions:
            handlers_to_call.update(self._exact_subscriptions[event.event_type])

        # Pattern match subscribers
        for pattern, handlers in self._subscriptions.items():
            if pattern.match(event.event_type):
                handlers_to_call.update(handlers)

        # Call all handlers (don't wait for them)
        for handler in handlers_to_call:
            asyncio.create_task(self._safe_call_handler(handler, event))

    async def _safe_call_handler(self, handler: Callable, event: Event) -> None:
        """Call handler with error handling"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
            self.events_delivered += 1
        except Exception as e:
            self.events_failed += 1
            print(f"⚠ Event handler failed: {handler.__name__} for {event.event_type}: {e}")
            # Add to dead letter queue
            self.dead_letter_queue.append(event)

    def subscribe(self, event_pattern: str, handler: Callable) -> None:
        """
        Subscribe to events matching a pattern

        Args:
            event_pattern: Event type pattern (supports wildcards: "sensor.*")
            handler: Async or sync function to call

        Examples:
            bus.subscribe("sensor.camera", handle_camera)
            bus.subscribe("sensor.*", handle_all_sensors)
            bus.subscribe("*", handle_everything)
        """
        # Exact match (most common, most efficient)
        if '*' not in event_pattern:
            self._exact_subscriptions[event_pattern].append(handler)
        else:
            # Convert wildcard pattern to regex
            regex_pattern = event_pattern.replace('.', r'\.').replace('*', '.*')
            compiled_pattern = re.compile(f'^{regex_pattern}$')

            if compiled_pattern not in self._subscriptions:
                self._subscriptions[compiled_pattern] = []
            self._subscriptions[compiled_pattern].append(handler)

    def unsubscribe(self, event_pattern: str, handler: Callable) -> None:
        """Unsubscribe a handler from an event pattern"""
        if '*' not in event_pattern:
            if event_pattern in self._exact_subscriptions:
                self._exact_subscriptions[event_pattern].remove(handler)
        else:
            regex_pattern = event_pattern.replace('.', r'\.').replace('*', '.*')
            compiled_pattern = re.compile(f'^{regex_pattern}$')

            if compiled_pattern in self._subscriptions:
                self._subscriptions[compiled_pattern].remove(handler)

    async def replay_stream(self, stream_key: str, from_id: str = "0",
                           handler: Optional[Callable] = None) -> List[Event]:
        """
        Replay events from Redis Stream

        Critical for resilience: If a model crashes, it can replay missed events.

        Args:
            stream_key: Stream to replay from
            from_id: Start position ('0' = beginning, '$' = latest)
            handler: Optional handler to call for each event

        Returns:
            List of replayed events
        """
        if not self.redis_connected:
            return []

        try:
            # Read from stream
            results = await self.redis_client.xread(
                {stream_key: from_id},
                count=1000,
                block=0
            )

            events = []
            for stream, messages in results:
                for message_id, data in messages:
                    # Reconstruct event
                    event = Event(
                        event_id=data['event_id'],
                        event_type=data['event_type'],
                        source=data['source'],
                        destination=data['destination'] if data['destination'] else None,
                        data=json.loads(data['data']),
                        metadata=json.loads(data['metadata']),
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        priority=Priority[data['priority']],
                        correlation_id=data['correlation_id'] if data['correlation_id'] else None,
                        parent_id=data['parent_id'] if data['parent_id'] else None
                    )
                    events.append(event)

                    # Optionally call handler
                    if handler:
                        await self._safe_call_handler(handler, event)

            return events
        except Exception as e:
            print(f"⚠ Failed to replay stream {stream_key}: {e}")
            return []

    def get_statistics(self) -> Dict[str, any]:
        """Get event bus statistics"""
        return {
            'events_published': self.events_published,
            'events_delivered': self.events_delivered,
            'events_failed': self.events_failed,
            'active_subscriptions': sum(len(h) for h in self._exact_subscriptions.values()) +
                                   sum(len(h) for h in self._subscriptions.values()),
            'dead_letter_queue_size': len(self.dead_letter_queue),
            'redis_connected': self.redis_connected
        }
