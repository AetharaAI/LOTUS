"""
LOTUS Memory System - L1: Working Memory

Ultra-fast Redis-backed working memory for immediate context.
"""

import json
import time
from typing import List, Dict, Any, Optional
import redis.asyncio as redis
import logging

from .base import MemoryTier, MemoryItem, MemoryType


class WorkingMemory(MemoryTier):
    """
    L1: Working Memory - Immediate context (last 10 minutes)
    """
    
    def __init__(self, redis_client: redis.Redis, 
                 ttl_seconds: int = 600, max_items: int = 100):
        super().__init__("working_memory", tier_level=1, ttl=ttl_seconds)
        self.redis = redis_client
        self.max_items = max_items
        
        self.key_prefix = "lotus:memory:L1:"
        self.timeline_key = f"{self.key_prefix}timeline"
        self.logger = logging.getLogger(f"lotus.memory.{self.tier_name}")
    
    async def store(self, memory: MemoryItem) -> Optional[str]:
        """Store memory in L1 (Working Memory)"""
        try:
            memory.source_tier = "L1"
            memory_key = f"{self.key_prefix}{memory.id}"
            memory_data = json.dumps(memory.to_dict())
            
            await self.redis.setex(memory_key, self.ttl, memory_data)
            await self.redis.lpush(self.timeline_key, memory.id)
            await self.redis.ltrim(self.timeline_key, 0, self.max_items - 1)
            self.logger.debug(f"Stored memory {memory.id[:15]}... in L1.")
            return memory.id
        except Exception as e:
            self.logger.exception(f"Error storing memory {memory.id[:15]}... in L1.")
            return None # Return None on failure
    
    async def retrieve(self, query: str, limit: int = 10,
                      filters: Optional[Dict] = None) -> List[MemoryItem]:
        """Retrieve memories from working memory"""
        self.logger.debug(f"Retrieving from L1 with query: {query[:50]}..., limit: {limit}, filters: {filters}")
        memories = []
        
        try:
            memory_ids = await self.redis.lrange(self.timeline_key, 0, self.max_items - 1)
            
            for memory_id_bytes in memory_ids:
                memory_id = memory_id_bytes.decode('utf-8')
                memory_key = f"{self.key_prefix}{memory_id}"
                
                memory_data = await self.redis.get(memory_key)
                
                if not memory_data:
                    self.logger.debug(f"Memory {memory_id[:15]}... expired or not found, removing from L1 timeline.")
                    await self.redis.lrem(self.timeline_key, 0, memory_id)
                    continue
                
                mem_dict = json.loads(memory_data)
                memory = MemoryItem.from_dict(mem_dict)
                
                if filters:
                    if 'memory_type' in filters and memory.memory_type.value != filters['memory_type']: continue
                    if 'min_importance' in filters and memory.importance < filters['min_importance']: continue
                
                if query and query != "*":
                    query_lower = query.lower()
                    if query_lower not in memory.content.lower():
                        continue
                
                memory.mark_accessed()
                await self.redis.setex(memory_key, self.ttl, json.dumps(memory.to_dict()))
                
                memories.append(memory)
                
                if len(memories) >= limit:
                    break
            self.logger.debug(f"Successfully retrieved {len(memories)} memories from L1.")
            return memories
        except Exception as e:
            self.logger.exception(f"Error retrieving from L1 with query: {query[:50]}...")
            return []

    async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]:
        """Retrieve a list of memories by their exact IDs from L1."""
        self.logger.debug(f"Getting {len(memory_ids)} memories by ID from L1.")
        memories = []
        if not memory_ids:
            return []
        
        try:
            # Prepare keys for mget
            keys = [f"{self.key_prefix}{mid}" for mid in memory_ids]
            
            # Retrieve all memories in one go
            results = await self.redis.mget(keys)
            
            for i, result in enumerate(results):
                if result:
                    mem_dict = json.loads(result)
                    memory = MemoryItem.from_dict(mem_dict)
                    memory.mark_accessed() # Mark as accessed
                    await self.redis.setex(keys[i], self.ttl, json.dumps(memory.to_dict())) # Update access
                    memories.append(memory)
                else:
                    self.logger.debug(f"Memory ID {memory_ids[i][:15]}... not found in L1.")
            return memories
        except Exception as e:
            self.logger.exception(f"Error getting memories by ID from L1.")
            return []
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a specific memory from working memory"""
        try:
            memory_key = f"{self.key_prefix}{memory_id}"
            deleted = await self.redis.delete(memory_key)
            await self.redis.lrem(self.timeline_key, 0, memory_id)
            self.logger.debug(f"Deleted memory {memory_id[:15]}... from L1. Status: {deleted > 0}")
            return deleted > 0
        except Exception as e:
            self.logger.exception(f"Error deleting memory {memory_id[:15]}... from L1.")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get working memory statistics"""
        self.logger.debug("Getting L1 statistics.")
        try:
            timeline_length = await self.redis.llen(self.timeline_key)
            memory_ids = await self.redis.lrange(self.timeline_key, 0, -1)
            
            total_memories = 0
            total_importance = 0.0
            oldest_timestamp = None
            newest_timestamp = None
            memory_types = {}
            
            for memory_id_bytes in memory_ids:
                memory_id = memory_id_bytes.decode('utf-8')
                memory_key = f"{self.key_prefix}{memory_id}"
                memory_data = await self.redis.get(memory_key)
                
                if memory_data:
                    total_memories += 1
                    mem_dict = json.loads(memory_data)
                    
                    total_importance += mem_dict['importance']
                    
                    timestamp = mem_dict['timestamp']
                    if oldest_timestamp is None or timestamp < oldest_timestamp: oldest_timestamp = timestamp
                    if newest_timestamp is None or timestamp > newest_timestamp: newest_timestamp = timestamp
                    
                    mem_type = mem_dict['memory_type']
                    memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
            
            stats = {
                "tier": "L1_working",
                "count": total_memories,
                "max_capacity": self.max_items,
                "utilization": total_memories / self.max_items if self.max_items > 0 else 0,
                "avg_importance": total_importance / total_memories if total_memories > 0 else 0,
                "oldest_timestamp": oldest_timestamp,
                "newest_timestamp": newest_timestamp,
                "age_minutes": (time.time() - (oldest_timestamp or time.time())) / 60,
                "memory_types": memory_types,
                "ttl_seconds": self.ttl
            }
            self.logger.debug("L1 statistics generated.")
            return stats
        except Exception as e:
            self.logger.exception("Error getting L1 statistics.")
            return {"tier": "L1_working", "error": str(e), "count": 0}
    
    async def get_all_for_consolidation(self) -> List[MemoryItem]:
        """Get all memories for consolidation process"""
        self.logger.debug("Getting all L1 memories for consolidation.")
        return await self.retrieve("*", limit=self.max_items)
    
    async def clear(self) -> int:
        """Clear all working memory (use with caution!)"""
        self.logger.warning("Clearing all L1 working memory!")
        try:
            memory_ids = await self.redis.lrange(self.timeline_key, 0, -1)
            
            count = 0
            for memory_id_bytes in memory_ids:
                memory_id = memory_id_bytes.decode('utf-8')
                if await self.delete(memory_id):
                    count += 1
            
            await self.redis.delete(self.timeline_key)
            self.logger.info(f"Cleared {count} memories from L1.")
            return count
        except Exception as e:
            self.logger.exception("Error clearing L1 working memory.")
            return 0
    
    async def health_check(self) -> bool:
        """Check if Redis is accessible"""
        try:
            await self.redis.ping()
            self.is_healthy = True
            self.logger.debug("L1 health check successful.")
            return True
        except Exception as e:
            self.is_healthy = False
            self.logger.error(f"L1 health check failed: {e}")
            return False
    
    def should_store_in_tier(self, memory: MemoryItem) -> bool:
        """Working memory stores EVERYTHING initially"""
        return True
    
    async def get_recent_context(self, minutes: int = 10) -> List[MemoryItem]:
        """Get all memories from the last N minutes"""
        self.logger.debug(f"Getting L1 recent context for last {minutes} minutes.")
        try:
            cutoff_time = time.time() - (minutes * 60)
            all_memories = await self.retrieve("*", limit=self.max_items)
            
            recent = [m for m in all_memories if m.timestamp >= cutoff_time]
            recent.sort(key=lambda m: m.timestamp, reverse=True)
            self.logger.debug(f"Retrieved {len(recent)} recent context memories from L1.")
            return recent
        except Exception as e:
            self.logger.exception(f"Error getting L1 recent context for {minutes} minutes.")
            return []
