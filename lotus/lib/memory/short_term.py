"""
LOTUS Memory System - L2: Short-term Memory

Redis Streams-backed short-term memory for recent history (last 24 hours).
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis
import logging

from .base import MemoryTier, MemoryItem, MemoryType


class ShortTermMemory(MemoryTier):
    """
    L2: Short-term Memory - Recent history (last 24 hours)
    """
    
    def __init__(self, redis_client: redis.Redis, 
                 ttl_hours: int = 24, max_items: int = 1000):
        super().__init__("short_term_memory", tier_level=2, ttl=ttl_hours * 3600)
        self.redis = redis_client
        self.max_items = max_items
        self.ttl_hours = ttl_hours
        
        self.stream_key = "lotus:memory:L2:stream"
        self.index_key = "lotus:memory:L2:index"
        self.access_prefix = f"{self.index_key}:access:"
        self.logger = logging.getLogger(f"lotus.memory.{self.tier_name}")
    
    async def store(self, memory: MemoryItem) -> Optional[str]:
        """Store memory in L2 (Short-term Memory)"""
        try:
            memory.source_tier = "L2"
            
            entry_data = {
                "memory_id": memory.id,
                "content": memory.content,
                "memory_type": memory.memory_type.value,
                "timestamp": str(memory.timestamp),
                "importance": str(memory.importance),
                "metadata": json.dumps(memory.metadata),
                "access_count": str(memory.access_count),
                "last_accessed": str(memory.last_accessed) if memory.last_accessed else "",
                "source_module": memory.source_module or ""
            }
            
            stream_id_bytes = await self.redis.xadd(self.stream_key, entry_data, maxlen=self.max_items, approximate=True)
            stream_id = stream_id_bytes.decode('utf-8')
            await self.redis.hset(self.index_key, memory.id, stream_id)
            
            await self._prune_old_entries() # Prune based on TTL if applicable
            self.logger.debug(f"Stored memory {memory.id[:15]}... in L2 with stream_id {stream_id[:10]}...")
            return memory.id
        except Exception as e:
            self.logger.exception(f"Error storing memory {memory.id[:15]}... in L2.")
            return None

    async def store_raw_data(self, content: str, memory_type: str, importance: float, metadata: Dict, source_module: str) -> Optional[str]:
        """
        Specifically store raw, potentially large, perception data in L2.
        This provides the full fidelity feed.
        """
        try:
            memory = MemoryItem(
                content=content,
                memory_type=MemoryType(memory_type),
                timestamp=time.time(),
                importance=importance,
                metadata=metadata,
                source_module=source_module
            )
            return await self.store(memory) # Reuse the general store method
        except Exception as e:
            self.logger.exception(f"Error storing raw perception data {memory.id[:15]}... in L2.")
            return None


    async def retrieve(self, query: str, limit: int = 10,
                      filters: Optional[Dict] = None) -> List[MemoryItem]:
        """Retrieve memories from short-term memory"""
        self.logger.debug(f"Retrieving from L2 with query: {query[:50]}..., limit: {limit}, filters: {filters}")
        memories = []
        
        try:
            min_timestamp_cutoff = time.time() - self.ttl
            if filters and 'time_range_hours' in filters:
                hours = filters['time_range_hours']
                min_timestamp_cutoff = time.time() - (hours * 3600)
            
            entries = await self.redis.xrevrange(self.stream_key, count=self.max_items)
            
            for stream_id, entry_data_bytes in entries:
                entry_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in entry_data_bytes.items()}
                memory = self._parse_stream_entry(entry_data)
                
                if not memory: continue
                if memory.timestamp < min_timestamp_cutoff: break 
                
                if filters:
                    if 'memory_type' in filters and memory.memory_type.value != filters['memory_type']: continue
                    if 'min_importance' in filters and memory.importance < filters['min_importance']: continue
                
                if query and query != "*":
                    query_lower = query.lower()
                    if query_lower not in memory.content.lower():
                        continue
                
                memory.mark_accessed()
                await self._update_access_count_and_timestamp(memory.id, memory.access_count, memory.last_accessed)
                
                memories.append(memory)
                
                if len(memories) >= limit:
                    break
            
            self.logger.debug(f"Successfully retrieved {len(memories)} memories from L2.")
            return memories
        except Exception as e:
            self.logger.exception(f"Error retrieving from L2 with query: {query[:50]}...")
            return []

    async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]:
        """Retrieve a list of memories by their exact IDs from L2."""
        self.logger.debug(f"Getting {len(memory_ids)} memories by ID from L2.")
        memories = []
        if not memory_ids:
            return []
        
        try:
            # Retrieve stream IDs from the index
            stream_ids_bytes = await self.redis.hmget(self.index_key, *memory_ids)
            
            # Use XREAD to fetch specific stream entries by ID if possible, or iterate
            for i, stream_id_bytes in enumerate(stream_ids_bytes):
                if stream_id_bytes:
                    stream_id = stream_id_bytes.decode('utf-8')
                    # XREVRANGE with count 1 and specific ID to get that entry
                    entries = await self.redis.xrevrange(self.stream_key, max=stream_id, min=stream_id, count=1)
                    if entries:
                        _, entry_data_bytes = entries[0]
                        entry_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in entry_data_bytes.items()}
                        memory = self._parse_stream_entry(entry_data)
                        if memory:
                            memory.mark_accessed()
                            await self._update_access_count_and_timestamp(memory.id, memory.access_count, memory.last_accessed)
                            memories.append(memory)
                else:
                    self.logger.debug(f"Memory ID {memory_ids[i][:15]}... not found in L2 index.")
            return memories
        except Exception as e:
            self.logger.exception(f"Error getting memories by ID from L2.")
            return []

    async def delete(self, memory_id: str) -> bool:
        """Delete a specific memory from short-term memory"""
        self.logger.debug(f"Attempting to delete memory {memory_id[:15]}... from L2.")
        try:
            stream_id = await self.redis.hget(self.index_key, memory_id)
            
            if not stream_id:
                self.logger.debug(f"Memory {memory_id[:15]}... not found in L2 index for deletion.")
                return False
            
            deleted_count = await self.redis.xdel(self.stream_key, stream_id.decode('utf-8'))
            await self.redis.hdel(self.index_key, memory_id)
            await self.redis.delete(f"{self.access_prefix}{memory_id}")
            
            self.logger.debug(f"Deleted memory {memory_id[:15]}... from L2. Status: {deleted_count > 0}")
            return deleted_count > 0
        except Exception as e:
            self.logger.exception(f"Error deleting memory {memory_id[:15]}... from L2.")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get short-term memory statistics"""
        self.logger.debug("Getting L2 statistics.")
        try:
            stream_info = await self.redis.xinfo_stream(self.stream_key, full=False)
            
            count = stream_info.get('length', 0)
            
            oldest_timestamp = None
            newest_timestamp = None
            avg_importance = 0.0
            memory_types = {}
            
            if count > 0:
                oldest_id = stream_info.get('first-entry-id', b'0-0').decode('utf-8')
                newest_id = stream_info.get('last-entry-id', b'0-0').decode('utf-8')
                
                oldest_timestamp = int(oldest_id.split('-')[0]) / 1000
                newest_timestamp = int(newest_id.split('-')[0]) / 1000

                entries = await self.redis.xrevrange(self.stream_key, count=min(count, 100))
                total_importance = 0.0
                for _, entry_data_bytes in entries:
                    entry_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in entry_data_bytes.items()}
                    memory = self._parse_stream_entry(entry_data)
                    if memory:
                        total_importance += memory.importance
                        mem_type = memory.memory_type.value
                        memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
                avg_importance = total_importance / len(entries) if entries else 0.0
            
            stats = {
                "tier": "L2_short_term",
                "count": count,
                "max_capacity": self.max_items,
                "utilization": count / self.max_items if self.max_items > 0 else 0,
                "avg_importance": avg_importance,
                "oldest_timestamp": oldest_timestamp,
                "newest_timestamp": newest_timestamp,
                "age_hours": (time.time() - (oldest_timestamp or time.time())) / 3600,
                "memory_types": memory_types,
                "ttl_hours": self.ttl_hours
            }
            self.logger.debug("L2 statistics generated.")
            return stats
        except redis.ResponseError as re:
            self.logger.warning(f"L2 stream '{self.stream_key}' does not exist or Redis error during stats: {re}")
            return {"tier": "L2_short_term", "error": str(re), "count": 0}
        except Exception as e:
            self.logger.exception("Error getting L2 statistics.")
            return {"tier": "L2_short_term", "error": str(e), "count": 0}
    
    async def get_time_range(self, start_time: float, end_time: float) -> List[MemoryItem]:
        """Get all memories within a specific time range"""
        self.logger.debug(f"Getting L2 memories in time range: {start_time} to {end_time}.")
        memories = []
        try:
            start_id = f"{int(start_time * 1000)}-0"
            end_id = f"{int(end_time * 1000)}-max"
            
            entries = await self.redis.xrange(self.stream_key, min=start_id, max=end_id)
            
            for _, entry_data_bytes in entries:
                entry_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in entry_data_bytes.items()}
                memory = self._parse_stream_entry(entry_data)
                if memory:
                    memories.append(memory)
            
            memories.sort(key=lambda m: m.timestamp)
            self.logger.debug(f"Retrieved {len(memories)} memories from L2 in specified time range.")
            return memories
        except Exception as e:
            self.logger.exception(f"Error getting L2 memories in time range {start_time}-{end_time}.")
            return []
    
    async def get_conversation_flow(self, hours: int = 24) -> List[MemoryItem]:
        """Get conversation flow for the last N hours"""
        self.logger.debug(f"Getting L2 conversation flow for last {hours} hours.")
        try:
            cutoff_time = time.time() - (hours * 3600)
            memories = await self.retrieve("*", limit=self.max_items, filters={'time_range_hours': hours})
            
            episodic = [m for m in memories if m.memory_type == MemoryType.EPISODIC]
            episodic.sort(key=lambda m: m.timestamp)
            
            self.logger.debug(f"Retrieved {len(episodic)} episodic memories for conversation flow from L2.")
            return episodic
        except Exception as e:
            self.logger.exception(f"Error getting L2 conversation flow for {hours} hours.")
            return []
    
    async def retrieve_recent(self, count: int = 10) -> List[MemoryItem]:
        """Retrieve the N most recent memories from the stream directly."""
        self.logger.debug(f"Retrieving {count} most recent memories from L2 stream.")
        memories = []
        try:
            entries = await self.redis.xrevrange(self.stream_key, count=count)
            for _, entry_data_bytes in entries:
                entry_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in entry_data_bytes.items()}
                memory = self._parse_stream_entry(entry_data)
                if memory:
                    memories.append(memory)
            self.logger.debug(f"Retrieved {len(memories)} recent memories directly from L2 stream.")
            return memories
        except Exception as e:
            self.logger.exception(f"Error retrieving recent memories directly from L2 stream.")
            return []

    async def _parse_stream_entry(self, entry_data: Dict[str, Any]) -> Optional[MemoryItem]:
        """Parse Redis Stream entry into MemoryItem"""
        try:
            metadata = json.loads(entry_data.get('metadata', '{}'))
            access_count = int(entry_data.get('access_count', 0))
            last_accessed_str = entry_data.get('last_accessed', '')
            last_accessed = float(last_accessed_str) if last_accessed_str else None

            return MemoryItem(
                content=entry_data.get('content', ''),
                memory_type=MemoryType(entry_data.get('memory_type', 'episodic')),
                timestamp=float(entry_data.get('timestamp', 0)),
                importance=float(entry_data.get('importance', 0.5)),
                metadata=metadata,
                access_count=access_count,
                last_accessed=last_accessed,
                id=entry_data.get('memory_id', ''),
                source_module=entry_data.get('source_module') or None,
                source_tier="L2"
            )
        except Exception as e:
            self.logger.error(f"Error parsing L2 stream entry: {e}. Data: {entry_data}", exc_info=True)
            return None
    
    async def _update_access_count_and_timestamp(self, memory_id: str, new_access_count: int, new_last_accessed: float) -> None:
        """Update access count and last accessed timestamp for a memory."""
        try:
            access_key = f"{self.access_prefix}{memory_id}"
            await self.redis.hset(access_key, mapping={
                "access_count": new_access_count,
                "last_accessed": new_last_accessed
            })
            await self.redis.expire(access_key, self.ttl)
            self.logger.debug(f"Updated access for {memory_id[:15]}... in L2 access store.")
        except Exception as e:
            self.logger.exception(f"Error updating access for memory {memory_id[:15]}... in L2.")

    async def _prune_old_entries(self) -> int:
        """Prune entries older than TTL. (Currently approximated by MAXLEN)."""
        self.logger.debug("Running L2 explicit pruning for old entries. This is currently an approximation.")
        # Redis Streams MAXLEN handles trimming by count. For TTL, a background scan with XDEL on older IDs is needed.
        return 0
    
    async def health_check(self) -> bool:
        """Check if Redis Streams are accessible"""
        try:
            await self.redis.ping()
            try:
                await self.redis.xinfo_stream(self.stream_key, full=False)
            except redis.ResponseError as e:
                if "no such key" in str(e).lower():
                    self.logger.debug(f"L2 health check: Stream '{self.stream_key}' does not exist yet (normal on fresh start).")
                else:
                    raise
            self.is_healthy = True
            self.logger.debug("L2 health check successful.")
            return True
        except Exception as e:
            self.is_healthy = False
            self.logger.error(f"L2 health check failed: {e}", exc_info=True)
            return False
    
    def should_store_in_tier(self, memory: MemoryItem) -> bool:
        """Short-term memory stores memories that are less than `self.ttl_hours` hours old and have importance > 0.1."""
        age_hours = (time.time() - memory.timestamp) / 3600
        return age_hours < self.ttl_hours and memory.importance > 0.1
