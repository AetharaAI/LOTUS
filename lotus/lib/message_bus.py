"""
LOTUS Message Bus

Async message bus implementation using Redis pub/sub for inter-module communication.
"""

import asyncio
import json
import re
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .logging import get_logger
from .exceptions import MessageBusError


logger = get_logger("message_bus")


class MessageBus:
    """
    Event-driven message bus for inter-module communication

    Uses Redis pub/sub for scalable, distributed messaging.
    Supports:
    - Event publishing and subscription
    - Wildcard subscriptions (e.g., "perception.*")
    - Request/response patterns
    - Message queuing
    """

    def __init__(self, config_or_host = "localhost", redis_port: int = 6379, redis_db: int = 0):
        """
        Initialize message bus

        Args:
            config_or_host: Config object or Redis host string
            redis_port: Redis server port (if not using config)
            redis_db: Redis database number (if not using config)
        """
        # Support both Config object and direct host/port/db params
        if hasattr(config_or_host, 'get'):
            # It's a Config object
            self.redis_host = config_or_host.get("redis.host", "localhost")
            self.redis_port = config_or_host.get("redis.port", 6379)
            self.redis_db = config_or_host.get("redis.db", 0)
        else:
            # It's a host string
            self.redis_host = config_or_host
            self.redis_port = redis_port
            self.redis_db = redis_db

        self.redis_client: Optional[Any] = None
        self.pubsub: Optional[Any] = None

        # Subscription handlers: {pattern: [handler_funcs]}
        self.handlers: Dict[str, List[Callable]] = {}

        # Background tasks
        self.listener_task: Optional[asyncio.Task] = None
        self.running = False

        # In-memory fallback if Redis not available
        self.fallback_mode = False
        self.fallback_handlers: Dict[str, List[Callable]] = {}

    @property
    def redis(self):
        """Alias for redis_client to match expected interface"""
        return self.redis_client

    async def connect(self) -> None:
        """
        Connect to Redis

        Raises:
            MessageBusError: If connection fails
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory message bus (NOT suitable for production)")
            self.fallback_mode = True
            return

        try:
            self.redis_client = await aioredis.from_url(
                f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}",
                encoding="utf-8",
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")

            # Create pubsub
            self.pubsub = self.redis_client.pubsub()

        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using in-memory fallback: {e}")
            self.fallback_mode = True

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        self.running = False

        if self.listener_task and not self.listener_task.done():
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            await self.pubsub.close()

        if self.redis_client:
            await self.redis_client.close()

        logger.info("Disconnected from message bus")

    async def publish(self, channel: str, message: Any) -> None:
        """
        Publish a message to a channel

        Args:
            channel: Channel name (e.g., "perception.file_changed")
            message: Message data (will be JSON-serialized)
        """
        # Ensure message has required fields
        if isinstance(message, dict):
            if 'timestamp' not in message:
                message['timestamp'] = datetime.utcnow().isoformat()
            if 'event' not in message:
                message['event'] = channel

        # Serialize message
        message_json = json.dumps(message)

        if self.fallback_mode:
            # In-memory delivery
            await self._deliver_message_fallback(channel, message)
        else:
            # Publish to Redis
            try:
                await self.redis_client.publish(channel, message_json)
                logger.debug(f"Published to {channel}: {message_json[:100]}")
            except Exception as e:
                logger.error(f"Failed to publish message: {e}")
                raise MessageBusError(f"Failed to publish message: {e}")

    async def subscribe(self, pattern: str, handler: Callable) -> None:
        """
        Subscribe to a channel pattern

        Args:
            pattern: Channel pattern (supports wildcards: "perception.*" or exact: "perception.file_changed")
            handler: Async function to call with message data
        """
        if pattern not in self.handlers:
            self.handlers[pattern] = []

        self.handlers[pattern].append(handler)
        logger.debug(f"Subscribed to {pattern}")

        if self.fallback_mode:
            # Store in fallback handlers
            if pattern not in self.fallback_handlers:
                self.fallback_handlers[pattern] = []
            self.fallback_handlers[pattern].append(handler)
        else:
            # Subscribe in Redis
            if self.pubsub:
                if '*' in pattern:
                    await self.pubsub.psubscribe(pattern)
                else:
                    await self.pubsub.subscribe(pattern)

    async def unsubscribe(self, pattern: str) -> None:
        """
        Unsubscribe from a channel pattern

        Args:
            pattern: Channel pattern to unsubscribe from
        """
        if pattern in self.handlers:
            del self.handlers[pattern]

        if self.fallback_mode:
            if pattern in self.fallback_handlers:
                del self.fallback_handlers[pattern]
        else:
            if self.pubsub:
                if '*' in pattern:
                    await self.pubsub.punsubscribe(pattern)
                else:
                    await self.pubsub.unsubscribe(pattern)

        logger.debug(f"Unsubscribed from {pattern}")

    async def start_listening(self) -> None:
        """Start listening for messages"""
        if self.fallback_mode:
            logger.info("Message bus in fallback mode (in-memory only)")
            return

        self.running = True
        self.listener_task = asyncio.create_task(self._listen_loop())
        logger.info("Started listening for messages")

    async def _listen_loop(self) -> None:
        """Background task that listens for messages"""
        if not self.pubsub:
            return

        try:
            async for message in self.pubsub.listen():
                if not self.running:
                    break

                if message['type'] in ('message', 'pmessage'):
                    channel = message.get('channel', '')
                    data = message.get('data', '')

                    try:
                        # Parse message
                        message_data = json.loads(data) if isinstance(data, str) else data

                        # Deliver to handlers
                        await self._deliver_message(channel, message_data)

                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse message: {data}")
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")

        except asyncio.CancelledError:
            logger.debug("Listen loop cancelled")
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")

    async def _deliver_message(self, channel: str, message: Any) -> None:
        """
        Deliver message to registered handlers

        Args:
            channel: Channel the message was published to
            message: Message data
        """
        delivered = False

        for pattern, handlers in self.handlers.items():
            # Check if channel matches pattern
            if self._match_pattern(pattern, channel):
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
                        delivered = True
                    except Exception as e:
                        logger.error(f"Error in handler for {channel}: {e}")

        if not delivered:
            logger.debug(f"No handlers for channel: {channel}")

    async def _deliver_message_fallback(self, channel: str, message: Any) -> None:
        """
        Deliver message in fallback mode (in-memory)

        Args:
            channel: Channel name
            message: Message data
        """
        for pattern, handlers in self.fallback_handlers.items():
            if self._match_pattern(pattern, channel):
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
                    except Exception as e:
                        logger.error(f"Error in fallback handler for {channel}: {e}")

    def _match_pattern(self, pattern: str, channel: str) -> bool:
        """
        Check if channel matches pattern

        Args:
            pattern: Pattern (may contain wildcards)
            channel: Channel name

        Returns:
            True if channel matches pattern
        """
        # Convert wildcard pattern to regex
        if '*' in pattern:
            regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
            return re.match(f'^{regex_pattern}$', channel) is not None
        else:
            return pattern == channel

    async def cleanup(self) -> None:
        """Cleanup resources (alias for disconnect)"""
        await self.disconnect()
