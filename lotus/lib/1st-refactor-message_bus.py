
"""
Message Bus - Redis Pub/Sub Wrapper

Provides event-driven communication between modules using Redis.

Features:
- Publish/Subscribe messaging
- Redis Streams for event history
- JSON serialization
- Audit stream for persistent tracing (stream:debug.messages)
"""

import asyncio
import json
from typing import Callable, Any, Dict, List, Optional
from datetime import datetime
import redis.asyncio as redis
import logging # Import logging

class MessageBus:
    """Redis-based message bus for inter-module communication."""

    def __init__(self, config=None, host: str = "localhost", port: int = 6379, db: int = 0):
        # Setup logging for the MessageBus
        self.logger = logging.getLogger("lotus.message_bus")

        # Handle Config object
        if config is not None:
            if hasattr(config, 'get'):
                self.host = config.get("redis.host", host)
                self.port = config.get("redis.port", port)
                self.db = config.get("redis.db", db)
            else:
                self.host = config.get("redis.host", host) if hasattr(config, 'get') else host
                self.port = config.get("redis.port", port) if hasattr(config, 'get') else port
                self.db = config.get("redis.db", db) if hasattr(config, 'get') else db
        else:
            self.host = host
            self.port = port
            self.db = db

        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None

        # Subscriptions: channel -> [callbacks]
        self.subscriptions: Dict[str, List[Callable]] = {}
        # Keep track of actual Redis PubSub subscriptions
        self._redis_subscriptions: Dict[str, asyncio.Task] = {}


        # Background task for handling messages
        self.message_task: Optional[asyncio.Task] = None

        self.connected = False
        self.logger.debug(f"MessageBus initialized for {self.host}:{self.port}/{self.db}")

    async def connect(self) -> None:
        """Connect to Redis"""
        if self.connected:
            self.logger.warning("Attempted to connect MessageBus when already connected.")
            return

        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True # Decode responses for Redis commands
            )

            await self.redis.ping()
            self.logger.info("Redis client connected.")

            self.pubsub = self.redis.pubsub()
            self.logger.info("Redis PubSub client created.")

            # Start the message handler task
            self.message_task = asyncio.create_task(self._message_handler())
            self.connected = True
            self.logger.info("MessageBus connected successfully.")
        except Exception as e:
            self.logger.critical(f"Failed to connect MessageBus to Redis: {e}", exc_info=True)
            # Ensure resources are cleaned up on failure
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if not self.connected:
            self.logger.debug("Attempted to disconnect MessageBus when not connected.")
            return

        self.connected = False
        self.logger.info("MessageBus disconnecting...")

        # Cancel message handler task
        if self.message_task:
            self.message_task.cancel()
            try:
                await self.message_task
            except asyncio.CancelledError:
                self.logger.debug("Message handler task cancelled.")
            except Exception as e:
                self.logger.error(f"Error while cancelling message handler task: {e}")

        # Unsubscribe all active subscriptions in Redis PubSub
        if self.pubsub:
            for channel_or_pattern in list(self._redis_subscriptions.keys()):
                try:
                    if "*" in channel_or_pattern:
                        await self.pubsub.punsubscribe(channel_or_pattern)
                        self.logger.debug(f"PubSub punsubscribed from '{channel_or_pattern}'.")
                    else:
                        await self.pubsub.unsubscribe(channel_or_pattern)
                        self.logger.debug(f"PubSub unsubscribed from '{channel_or_pattern}'.")
                except Exception as e:
                    self.logger.error(f"Error during PubSub unsubscribe from '{channel_or_pattern}': {e}")
            self._redis_subscriptions.clear()
            try:
                await self.pubsub.close()
                self.logger.debug("PubSub client closed.")
            except Exception as e:
                self.logger.error(f"Error closing PubSub client: {e}")
            self.pubsub = None

        if self.redis:
            try:
                await self.redis.close()
                self.logger.debug("Redis client closed.")
            except Exception as e:
                self.logger.error(f"Error closing Redis client: {e}")
            self.redis = None
        
        self.subscriptions.clear()
        self.logger.info("MessageBus disconnected successfully.")

    def _get_stream_name(self, channel: str) -> str:
        """Get Redis stream name for a channel"""
        return f"stream:{channel}"

    async def publish(self, channel: str, data: Any) -> None:
        """Publish a message to a channel"""
        if not self.connected or not self.redis:
            self.logger.error(f"Attempted to publish to '{channel}' but MessageBus is not connected or Redis client is None.")
            raise Exception("Not connected to Redis")

        if isinstance(data, (list, dict)):
            try:
                size = len(json.dumps(data)) # Check serialized size
            except Exception:
                size = 0
            if size > 100000: # Increased threshold for reasonable payloads
                self.logger.warning(f"Perception data for channel '{channel}' is very large ({size} bytes), consider optimizing.")
                # raise ValueError(f"Perception data too large for bus ({size} bytes)") # Re-enable if strict limits needed

        message = {
            "channel": channel,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        serialized_message = json.dumps(message)

        try:
            print(f"[msgbus-publish] channel={channel} timestamp={message['timestamp']}")
            await self.redis.publish(channel, serialized_message)
            self.logger.debug(f"Published message to Pub/Sub channel '{channel}'.")
        except Exception as e:
            self.logger.error(f"Failed to publish message to Pub/Sub channel '{channel}': {e}", exc_info=True)

        stream_name = self._get_stream_name(channel)
        try:
            await self.redis.xadd(stream_name, {"data": serialized_message}, maxlen=10000, approximate=True)
            self.logger.debug(f"Added message to Redis Stream '{stream_name}'.")
        except Exception as e:
            print(f"[msgbus-xadd-fail] stream={stream_name} error={e}")
            self.logger.error(f"Failed to add message to Redis Stream '{stream_name}': {e}", exc_info=True)

        try:
            await self.redis.xadd("stream:debug.messages", {
                "direction": "publish",
                "channel": channel,
                "data": json.dumps(data), # Store original data for audit
                "ts": datetime.utcnow().isoformat()
            }, maxlen=5000, approximate=True)
            self.logger.debug(f"Added audit entry for publish on channel '{channel}'.")
        except Exception as e:
            self.logger.error(f"Failed to add audit entry for publish on channel '{channel}': {e}", exc_info=True)


    async def subscribe(self, channel_or_pattern: str, callback: Callable) -> None:
        """Subscribe to a channel or pattern"""
        if not self.connected or not self.pubsub:
            self.logger.error(f"Attempted to subscribe to '{channel_or_pattern}' but MessageBus is not connected or PubSub client is None.")
            raise Exception("Not connected to Redis")

        if channel_or_pattern not in self.subscriptions:
            self.subscriptions[channel_or_pattern] = []
            
            try:
                if "*" in channel_or_pattern:
                    await self.pubsub.psubscribe(channel_or_pattern)
                    self.logger.info(f"PubSub client psubscribed to pattern '{channel_or_pattern}'.")
                else:
                    await self.pubsub.subscribe(channel_or_pattern)
                    self.logger.info(f"PubSub client subscribed to channel '{channel_or_pattern}'.")
                self._redis_subscriptions[channel_or_pattern] = True # Mark as subscribed in Redis
            except Exception as e:
                self.logger.error(f"Failed to subscribe PubSub client to '{channel_or_pattern}': {e}", exc_info=True)
                # Clean up if PubSub subscription fails
                if channel_or_pattern in self.subscriptions:
                    del self.subscriptions[channel_or_pattern]
                raise

        self.subscriptions[channel_or_pattern].append(callback)
        self.logger.debug(f"Callback registered for '{channel_or_pattern}'. Total callbacks: {len(self.subscriptions[channel_or_pattern])}")

    async def unsubscribe(self, channel_or_pattern: str, callback: Callable) -> None:
        """Unsubscribe from a channel or pattern"""
        if not self.connected or not self.pubsub:
            self.logger.debug(f"Attempted to unsubscribe from '{channel_or_pattern}' but MessageBus is not connected or PubSub client is None.")
            return # Simply return if not connected

        if channel_or_pattern in self.subscriptions:
            if callback in self.subscriptions[channel_or_pattern]:
                self.subscriptions[channel_or_pattern].remove(callback)
                self.logger.debug(f"Callback unregistered for '{channel_or_pattern}'. Remaining callbacks: {len(self.subscriptions[channel_or_pattern])}")

            if not self.subscriptions[channel_or_pattern]: # If no more local callbacks
                try:
                    if "*" in channel_or_pattern:
                        await self.pubsub.punsubscribe(channel_or_pattern)
                        self.logger.info(f"PubSub client punsubscribed from pattern '{channel_or_pattern}'.")
                    else:
                        await self.pubsub.unsubscribe(channel_or_pattern)
                        self.logger.info(f"PubSub client unsubscribed from channel '{channel_or_pattern}'.")
                    if channel_or_pattern in self._redis_subscriptions:
                        del self._redis_subscriptions[channel_or_pattern] # Remove from Redis subscriptions tracking
                except Exception as e:
                    self.logger.error(f"Error during PubSub client unsubscribe from '{channel_or_pattern}': {e}")
                
                del self.subscriptions[channel_or_pattern]
                self.logger.debug(f"Removed all local subscriptions for '{channel_or_pattern}'.")

    async def _message_handler(self) -> None:
        """Background task that handles incoming messages"""
        self.logger.info("Starting message handler task.")
        try:
            # The async for loop robustly handles message reception and re-subscription
            async for message in self.pubsub.listen():
                if not self.connected: # Check connection status in loop
                    self.logger.info("MessageBus no longer connected. Stopping message handler.")
                    break

                if message["type"] in ["message", "pmessage"]:
                    channel = message.get("channel") or message.get("pattern") or "unknown"
                    payload_data = None # Initialize for finally block

                    # Deserialize message
                    try:
                        # message["data"] is already decoded due to decode_responses=True in redis.Redis
                        # It should be a JSON string from our publish method.
                        deserialized_message = json.loads(message["data"])
                        # The `data` field of the overall message contains the actual payload
                        payload_data = deserialized_message.get("data") 
                        source_channel = deserialized_message.get("channel", channel) # Use actual channel from message
                    except json.JSONDecodeError as jde:
                        self.logger.error(f"JSONDecodeError in message handler for channel '{channel}': {jde}. Raw data: {message.get('data')}", exc_info=True)
                        # Fallback to raw data if JSON decoding fails
                        payload_data = message.get("data")
                        source_channel = channel
                    except Exception as e:
                        self.logger.error(f"Unexpected error deserializing message for channel '{channel}': {e}. Raw message: {message}", exc_info=True)
                        payload_data = message.get("data")
                        source_channel = channel

                    # Debug: print receipt of message for tracing
                    try:
                        # Only log payload preview if it's a dict or string
                        payload_preview = str(payload_data)[:100] if isinstance(payload_data, (dict, str)) else type(payload_data).__name__
                        print(f"[msgbus-recv] channel={source_channel} type={message.get('type')} payload_type={type(payload_data).__name__} preview={payload_preview}")
                        self.logger.debug(f"Received message on channel '{source_channel}' (type: {message.get('type')}, payload type: {type(payload_data).__name__}).")
                    except Exception as e:
                        self.logger.error(f"Error logging message receipt: {e}", exc_info=True)

                    # Write audit entry asynchronously (bounded)
                    if payload_data is not None:
                        try:
                            # Use current event loop to create task
                            asyncio.get_event_loop().create_task(
                                self.redis.xadd("stream:debug.messages", {
                                    "direction": "recv",
                                    "channel": source_channel,
                                    "data": json.dumps(payload_data),
                                    "ts": datetime.utcnow().isoformat()
                                }, maxlen=5000, approximate=True)
                            )
                        except Exception as e:
                            self.logger.error(f"Failed to add audit entry for received message on channel '{source_channel}': {e}", exc_info=True)

                    # Dispatch to matching subscriptions
                    try:
                        for pattern, callbacks in list(self.subscriptions.items()): # Iterate on a copy
                            if self._channel_matches(source_channel, pattern):
                                for callback in list(callbacks): # Iterate on a copy
                                    try:
                                        # Call callback with source_channel and actual payload
                                        await callback(source_channel, payload_data)
                                    except Exception as e:
                                        self.logger.error(f"Error executing callback for channel '{source_channel}' (pattern '{pattern}'): {e}", exc_info=True)
                    except Exception as e:
                        self.logger.error(f"Error during callback dispatch for channel '{source_channel}': {e}", exc_info=True)
                    finally:
                        # Explicitly free references for large payloads if necessary
                        del payload_data
                        if self.redis.connection_pool.max_connections > 1: # Only relevant if connection pool is active
                            try:
                                import gc
                                gc.collect()
                            except Exception:
                                pass # gc.collect is best-effort

        except asyncio.CancelledError:
            self.logger.info("Message handler task cancelled.")
        except Exception as e:
            self.logger.critical(f"Critical error in MessageBus message handler: {e}", exc_info=True)
            # Reattempt connection after a delay on critical errors
            if self.connected:
                self.logger.warning("Attempting to reconnect MessageBus after critical error...")
                await self.disconnect()
                await asyncio.sleep(5) # Backoff before reconnecting
                try:
                    await self.connect()
                except Exception as reconnect_e:
                    self.logger.critical(f"Failed to reconnect MessageBus after error: {reconnect_e}")
                    # If reconnection fails, let the loop break and system handle it
        self.logger.info("Message handler task stopped.")

    def _channel_matches(self, channel: str, pattern: str) -> bool:
        """Check if channel matches pattern (supports wildcards)"""
        if "*" not in pattern:
            return channel == pattern

        # Simple wildcard matching
        parts = pattern.split("*")
        if len(parts) == 2:
            prefix, suffix = parts
            return channel.startswith(prefix) and channel.endswith(suffix)

        return False

    async def get_history(self, channel: str, count: int = 100, start: str = "-", end: str = "+") -> List[Dict]:
        """Get historical messages from a channel stream"""
        if not self.connected or not self.redis:
            self.logger.warning(f"Attempted to get history for '{channel}' but MessageBus is not connected or Redis client is None. Returning empty list.")
            return []
        
        stream_name = self._get_stream_name(channel)
        result = []
        try:
            messages = await self.redis.xrange(stream_name, start, end, count)

            for msg_id, fields in messages:
                try:
                    # fields values are bytes if decode_responses=False, but here it's True for Redis client
                    # so fields should have string keys and values if original data was string.
                    # Our stored data is `serialized_message`, which is a JSON string.
                    deserialized_message = json.loads(fields["data"])
                    result.append({
                        "id": msg_id,
                        "channel": deserialized_message.get("channel", channel),
                        "data": deserialized_message.get("data"), # Extract actual payload
                        "timestamp": deserialized_message.get("timestamp")
                    })
                except Exception as e:
                    self.logger.error(f"Error parsing historical message from stream '{stream_name}' (ID: {msg_id}): {e}. Raw fields: {fields}", exc_info=True)
                    result.append({"id": msg_id, "raw_fields": fields, "error": str(e)})
        except Exception as e:
            self.logger.error(f"Failed to get history for stream '{stream_name}': {e}", exc_info=True)

        return result

    async def get_latest(self, channel: str, count: int = 1) -> Optional[Dict]:
        """Get the most recent message from a channel stream"""
        if not self.connected or not self.redis:
            self.logger.warning(f"Attempted to get latest for '{channel}' but MessageBus is not connected or Redis client is None. Returning None.")
            return None
        
        stream_name = self._get_stream_name(channel)
        try:
            # XREVRANGE returns newest first
            messages = await self.redis.xrevrange(stream_name, count=count)
            if messages:
                msg_id, fields = messages[0]
                try:
                    deserialized_message = json.loads(fields["data"])
                    return {
                        "id": msg_id,
                        "channel": deserialized_message.get("channel", channel),
                        "data": deserialized_message.get("data"),
                        "timestamp": deserialized_message.get("timestamp")
                    }
                except Exception as e:
                    self.logger.error(f"Error parsing latest message from stream '{stream_name}' (ID: {msg_id}): {e}. Raw fields: {fields}", exc_info=True)
                    return {"id": msg_id, "raw_fields": fields, "error": str(e)}
            return None
        except Exception as e:
            self.logger.error(f"Failed to get latest message from stream '{stream_name}': {e}", exc_info=True)
            return None