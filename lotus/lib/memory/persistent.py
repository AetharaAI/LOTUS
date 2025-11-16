"""
LOTUS Memory System - L4: Persistent Memory

PostgreSQL-backed persistent memory for permanent structured knowledge.
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

try:
    import psycopg
    from psycopg.rows import dict_row
    from sqlalchemy import text
    _PSYCOPG_AVAILABLE = True
except ImportError:
    psycopg = None
    dict_row = None
    text = None
    _PSYCOPG_AVAILABLE = False


from .base import MemoryTier, MemoryItem, MemoryType


if not _PSYCOPG_AVAILABLE:
    class PersistentMemory(MemoryTier):
        """
        No-op PersistentMemory implementation when psycopg is not installed.
        """
        def __init__(self, postgres_conn, table_name: str = "lotus_memories"):
            super().__init__("persistent_memory_noop", tier_level=4, ttl=None)
            self.conn = None
            self.table_name = table_name
            self.logger = logging.getLogger(f"lotus.memory.{self.tier_name}")
            self.logger.warning("PostgreSQL (psycopg) not available. L4 PersistentMemory is in no-op mode.")

        async def initialize(self) -> None:
            self.logger.debug("No-op L4 PersistentMemory initialize called.")
            return

        async def store(self, memory: MemoryItem) -> Optional[str]:
            self.logger.debug(f"No-op L4 PersistentMemory store called for {memory.id[:15]}...")
            return memory.id

        async def retrieve(self, query: str, limit: int = 10, filters: Optional[Dict] = None) -> List[MemoryItem]:
            self.logger.debug(f"No-op L4 PersistentMemory retrieve called for query: {query[:50]}...")
            return []

        async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]:
            self.logger.debug(f"No-op L4 PersistentMemory get_memories_by_id called for {len(memory_ids)} IDs.")
            return []
        
        async def delete(self, memory_id: str) -> bool:
            self.logger.debug(f"No-op L4 PersistentMemory delete called for {memory_id[:15]}...")
            return False
        
        async def get_stats(self) -> Dict[str, Any]:
            return {"tier": "L4_persistent_noop", "count": 0, "error": "psycopg not available"}

        async def get_facts(self, limit: int = 100) -> List[MemoryItem]: return []
        async def get_skills(self, limit: int = 100) -> List[MemoryItem]: return []
        async def get_user_profile_data(self) -> Dict[str, Any]: return {}
        async def store_user_preference(self, key: str, value: Any, importance: float = 0.9) -> str: return f"user_pref_noop:{key}"
        async def _update_access(self, memory_id: str, access_count: int, last_accessed: Optional[float]) -> None: return
        async def health_check(self) -> bool: return True
        def should_store_in_tier(self, memory: MemoryItem) -> bool: return False

else: # psycopg is available
    from sqlalchemy import text

    class PersistentMemory(MemoryTier):
        """
        L4: Persistent Memory - Permanent structured knowledge
        """
        
        def __init__(self, postgres_conn, table_name: str = "lotus_memories"):
            super().__init__("persistent_memory", tier_level=4, ttl=None)
            
            self.conn = postgres_conn
            self.table_name = table_name
            self.logger = logging.getLogger(f"lotus.memory.{self.tier_name}")
            if self.conn is None:
                self.logger.critical("PostgreSQL engine is None. L4 PersistentMemory will be non-functional.")
                self.is_healthy = False
                raise RuntimeError("PostgreSQL engine not provided to PersistentMemory.")
        
        async def initialize(self) -> None:
            """Create database schema if it doesn't exist"""
            self.logger.debug(f"Initializing L4 PersistentMemory schema for table '{self.table_name}'.")
            try:
                async with self.conn.connect() as aconn:
                    async with aconn.begin():
                        await aconn.execute(text(f"""
                            CREATE TABLE IF NOT EXISTS {self.table_name} (
                                id TEXT PRIMARY KEY,
                                content TEXT NOT NULL,
                                content_tsvector TSVECTOR,
                                memory_type TEXT NOT NULL,
                                timestamp FLOAT NOT NULL,
                                importance FLOAT NOT NULL,
                                metadata JSONB,
                                access_count INTEGER DEFAULT 0,
                                last_accessed FLOAT,
                                source_module TEXT,
                                source_tier TEXT DEFAULT 'L4',
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                        
                        await aconn.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_memory_type 
                            ON {self.table_name}(memory_type)
                        """))
                        
                        await aconn.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_importance 
                            ON {self.table_name}(importance)
                        """))
                        
                        await aconn.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_timestamp 
                            ON {self.table_name}(timestamp)
                        """))
                        
                        await aconn.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_content_search 
                            ON {self.table_name} USING GIN(content_tsvector)
                        """))
                        
                        await aconn.execute(text(f"""
                            CREATE OR REPLACE FUNCTION {self.table_name}_tsvector_update() 
                            RETURNS TRIGGER AS $$
                            BEGIN
                                NEW.content_tsvector = to_tsvector('english', NEW.content);
                                NEW.updated_at = CURRENT_TIMESTAMP;
                                RETURN NEW;
                            END;
                            $$ LANGUAGE plpgsql
                        """))
                        
                        await aconn.execute(text(f"""
                            DROP TRIGGER IF EXISTS tsvector_update ON {self.table_name}
                        """))
                        
                        await aconn.execute(text(f"""
                            CREATE TRIGGER tsvector_update 
                            BEFORE INSERT OR UPDATE ON {self.table_name}
                            FOR EACH ROW EXECUTE FUNCTION {self.table_name}_tsvector_update()
                        """))
                        self.logger.info(f"L4 schema for table '{self.table_name}' initialized successfully.")
                self.is_healthy = True
            except Exception as e:
                self.logger.critical(f"Failed to initialize L4 PersistentMemory schema for table '{self.table_name}': {e}", exc_info=True)
                self.is_healthy = False
                raise

        async def store(self, memory: MemoryItem) -> Optional[str]:
            """Store memory in L4 (Persistent Memory)"""
            if not self.is_healthy:
                self.logger.warning(f"Attempted to store memory {memory.id[:15]}... in unhealthy L4. Skipping.")
                return None
            self.logger.debug(f"Storing memory {memory.id[:15]}... in L4.")
            try:
                memory.source_tier = "L4"
                
                async with self.conn.connect() as aconn:
                    async with aconn.begin():
                        await aconn.execute(text(f"""
                            INSERT INTO {self.table_name} 
                            (id, content, memory_type, timestamp, importance, metadata, 
                             access_count, last_accessed, source_module, source_tier)
                            VALUES (:id, :content, :memory_type, :timestamp, :importance, :metadata, 
                                    :access_count, :last_accessed, :source_module, :source_tier)
                            ON CONFLICT (id) DO UPDATE SET
                                content = EXCLUDED.content,
                                memory_type = EXCLUDED.memory_type,
                                importance = EXCLUDED.importance,
                                metadata = EXCLUDED.metadata,
                                access_count = EXCLUDED.access_count,
                                last_accessed = EXCLUDED.last_accessed,
                                source_module = EXCLUDED.source_module,
                                updated_at = CURRENT_TIMESTAMP
                        """), {
                            "id": memory.id,
                            "content": memory.content,
                            "memory_type": memory.memory_type.value,
                            "timestamp": memory.timestamp,
                            "importance": memory.importance,
                            "metadata": json.dumps(memory.metadata),
                            "access_count": memory.access_count,
                            "last_accessed": memory.last_accessed,
                            "source_module": memory.source_module,
                            "source_tier": "L4"
                        })
                self.logger.debug(f"Memory {memory.id[:15]}... stored/updated in L4.")
                return memory.id
            except Exception as e:
                self.logger.exception(f"Error storing memory {memory.id[:15]}... in L4.")
                raise

        async def retrieve(self, query: str, limit: int = 10,
                          filters: Optional[Dict] = None) -> List[MemoryItem]:
            """Retrieve memories from persistent memory using PostgreSQL full-text search."""
            if not self.is_healthy:
                self.logger.warning(f"Attempted to retrieve from unhealthy L4 for query: {query[:50]}.... Skipping.")
                return []
            self.logger.debug(f"Retrieving from L4 with query: {query[:50]}..., limit: {limit}, filters: {filters}")
            
            try:
                where_clauses = []
                params = {}
                
                if query and query != "*":
                    where_clauses.append("content_tsvector @@ plainto_tsquery('english', :query_text)")
                    params["query_text"] = query
                
                if filters:
                    if 'memory_type' in filters:
                        where_clauses.append("memory_type = :memory_type")
                        params["memory_type"] = filters['memory_type']
                    
                    if 'min_importance' in filters:
                        where_clauses.append("importance >= :min_importance")
                        params["min_importance"] = filters['min_importance']
                    
                    if 'source_module' in filters:
                        where_clauses.append("source_module = :source_module")
                        params["source_module"] = filters['source_module']
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
                
                if query and query != "*":
                    order_by = "ts_rank(content_tsvector, plainto_tsquery('english', :query_text_rank)) DESC, importance DESC"
                    params["query_text_rank"] = query
                else:
                    order_by = "importance DESC, timestamp DESC"
                
                async with self.conn.connect() as aconn:
                    result = await aconn.execute(text(f"""
                        SELECT * FROM {self.table_name}
                        WHERE {where_sql}
                        ORDER BY {order_by}
                        LIMIT :limit
                    """), {**params, "limit": limit})
                    
                    rows = result.fetchall()
                
                memories = []
                for row in rows:
                    memory = MemoryItem(
                        content=row.content,
                        memory_type=MemoryType(row.memory_type),
                        timestamp=row.timestamp.timestamp() if isinstance(row.timestamp, datetime) else row.timestamp,
                        importance=row.importance,
                        metadata=json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata or {},
                        access_count=row.access_count,
                        last_accessed=row.last_accessed.timestamp() if isinstance(row.last_accessed, datetime) else row.last_accessed,
                        id=row.id,
                        source_module=row.source_module,
                        source_tier="L4"
                    )
                    memory.mark_accessed()
                    await self._update_access(memory.id, memory.access_count, memory.last_accessed)
                    memories.append(memory)
                
                self.logger.debug(f"Successfully retrieved {len(memories)} memories from L4.")
                return memories
            except Exception as e:
                self.logger.exception(f"Error retrieving from L4 with query: {query[:50]}...")
                return []

        async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]:
            """Retrieve a list of memories by their exact IDs from L4."""
            if not self.is_healthy: return []
            self.logger.debug(f"Getting {len(memory_ids)} memories by ID from L4.")
            memories = []
            if not memory_ids:
                return []
            
            try:
                async with self.conn.connect() as aconn:
                    result = await aconn.execute(text(f"""
                        SELECT * FROM {self.table_name}
                        WHERE id = ANY(:memory_ids)
                    """), {"memory_ids": memory_ids})
                    rows = result.fetchall()
                
                for row in rows:
                    memory = MemoryItem(
                        content=row.content,
                        memory_type=MemoryType(row.memory_type),
                        timestamp=row.timestamp.timestamp() if isinstance(row.timestamp, datetime) else row.timestamp,
                        importance=row.importance,
                        metadata=json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata or {},
                        access_count=row.access_count,
                        last_accessed=row.last_accessed.timestamp() if isinstance(row.last_accessed, datetime) else row.last_accessed,
                        id=row.id,
                        source_module=row.source_module,
                        source_tier="L4"
                    )
                    memory.mark_accessed()
                    await self._update_access(memory.id, memory.access_count, memory.last_accessed)
                    memories.append(memory)
                return memories
            except Exception as e:
                self.logger.exception(f"Error getting memories by ID from L4.")
                return []

        async def delete(self, memory_id: str) -> bool:
            """Delete a specific memory from persistent memory"""
            if not self.is_healthy: return False
            self.logger.debug(f"Deleting memory {memory_id[:15]}... from L4.")
            try:
                async with self.conn.connect() as aconn:
                    async with aconn.begin():
                        result = await aconn.execute(text(f"""
                            DELETE FROM {self.table_name} WHERE id = :id
                        """), {"id": memory_id})
                        
                        deleted_count = result.rowcount
                self.logger.debug(f"Memory {memory_id[:15]}... deleted from L4. Count: {deleted_count}")
                return deleted_count > 0
            except Exception as e:
                self.logger.exception(f"Error deleting memory {memory_id[:15]}... from L4.")
                return False
        
        async def get_stats(self) -> Dict[str, Any]:
            """Get persistent memory statistics"""
            if not self.is_healthy: return {"tier": "L4_persistent_unhealthy", "count": 0}
            self.logger.debug("Getting L4 statistics.")
            try:
                async with self.conn.connect() as aconn:
                    count_result = await aconn.execute(text(f"SELECT COUNT(*) as count FROM {self.table_name}"))
                    count = count_result.scalar_one()
                    
                    stats_result = await aconn.execute(text(f"""
                        SELECT 
                            AVG(importance) as avg_importance,
                            MIN(timestamp) as oldest_timestamp,
                            MAX(timestamp) as newest_timestamp,
                            memory_type,
                            COUNT(*) as type_count
                        FROM {self.table_name}
                        GROUP BY memory_type
                    """))
                    stats_rows = stats_result.fetchall()
                
                avg_importance = 0
                oldest_timestamp = None
                newest_timestamp = None
                memory_types = {}
                
                for row in stats_rows:
                    if row.avg_importance: avg_importance = max(avg_importance, row.avg_importance)
                    if row.oldest_timestamp:
                        ts = row.oldest_timestamp.timestamp() if isinstance(row.oldest_timestamp, datetime) else row.oldest_timestamp
                        if oldest_timestamp is None or ts < oldest_timestamp: oldest_timestamp = ts
                    if row.newest_timestamp:
                        ts = row.newest_timestamp.timestamp() if isinstance(row.newest_timestamp, datetime) else row.newest_timestamp
                        if newest_timestamp is None or ts > newest_timestamp: newest_timestamp = ts
                    
                    memory_types[row.memory_type] = row.type_count
                
                stats = {
                    "tier": "L4_persistent",
                    "count": count,
                    "max_capacity": "unlimited",
                    "avg_importance": avg_importance,
                    "oldest_timestamp": oldest_timestamp,
                    "newest_timestamp": newest_timestamp,
                    "age_days": (time.time() - (oldest_timestamp or time.time())) / 86400,
                    "memory_types": memory_types,
                    "storage_type": "postgresql",
                    "features": ["full_text_search", "ACID", "relational"]
                }
                self.logger.debug("L4 statistics generated.")
                return stats
            except Exception as e:
                self.logger.exception("Error getting L4 statistics.")
                return {"tier": "L4_persistent", "error": str(e), "count": 0}
        
        async def get_facts(self, limit: int = 100) -> List[MemoryItem]:
            """Get all semantic memories (facts)"""
            if not self.is_healthy: return []
            self.logger.debug(f"Getting L4 facts, limit: {limit}.")
            return await self.retrieve("*", limit=limit, 
                                      filters={'memory_type': MemoryType.SEMANTIC.value})
        
        async def get_skills(self, limit: int = 100) -> List[MemoryItem]:
            """Get all procedural memories (skills)"""
            if not self.is_healthy: return []
            self.logger.debug(f"Getting L4 skills, limit: {limit}.")
            return await self.retrieve("*", limit=limit,
                                      filters={'memory_type': MemoryType.PROCEDURAL.value})
        
        async def get_user_profile_data(self) -> Dict[str, Any]:
            """Get all user profile-related memories"""
            if not self.is_healthy: return {}
            self.logger.debug("Getting L4 user profile data.")
            profile = {}
            try:
                async with self.conn.connect() as aconn:
                    result = await aconn.execute(text(f"""
                        SELECT id, content, importance, timestamp, metadata
                        FROM {self.table_name}
                        WHERE metadata->>'category' = 'user_profile'
                        ORDER BY importance DESC
                    """))
                    rows = result.fetchall()
                
                for row in rows:
                    metadata = json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata or {}
                    key = metadata.get('profile_key', row.id)
                    profile[key] = {
                        'content': row.content,
                        'importance': row.importance,
                        'timestamp': row.timestamp.timestamp() if isinstance(row.timestamp, datetime) else row.timestamp,
                        'metadata': metadata
                    }
                self.logger.debug(f"Retrieved {len(profile)} user profile items from L4.")
                return profile
            except Exception as e:
                self.logger.exception("Error getting L4 user profile data.")
                return {}
        
        async def store_user_preference(self, key: str, value: Any, 
                                       importance: float = 0.9) -> Optional[str]: # Changed return to Optional[str]
            """Store a user preference permanently"""
            if not self.is_healthy: return f"user_pref_noop:{key}"
            self.logger.debug(f"Storing user preference '{key}' in L4.")
            memory = MemoryItem(
                content=f"User preference: {key} = {json.dumps(value)}",
                memory_type=MemoryType.SEMANTIC,
                timestamp=time.time(),
                importance=importance,
                metadata={
                    'category': 'user_profile',
                    'profile_key': key,
                    'value': value
                },
                id=f"user_pref:{key}"
            )
            
            return await self.store(memory)
        
        async def _update_access(self, memory_id: str, access_count: int,
                                last_accessed: Optional[float]) -> None:
            """Update access tracking for a memory"""
            if not self.is_healthy: return
            try:
                async with self.conn.connect() as aconn:
                    async with aconn.begin():
                        await aconn.execute(text(f"""
                            UPDATE {self.table_name}
                            SET access_count = :access_count, last_accessed = :last_accessed, updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """), {
                            "access_count": access_count,
                            "last_accessed": last_accessed,
                            "id": memory_id
                        })
                self.logger.debug(f"Updated access for {memory_id[:15]}... in L4.")
            except Exception as e:
                self.logger.error(f"Error updating access for memory {memory_id[:15]}... in L4: {e}")
        
        async def health_check(self) -> bool:
            """Check if PostgreSQL is accessible"""
            try:
                if self.conn is None: raise RuntimeError("PostgreSQL engine is None.")
                async with self.conn.connect() as aconn:
                    await aconn.execute(text("SELECT 1"))
                self.is_healthy = True
                self.logger.debug("L4 health check successful.")
                return True
            except Exception as e:
                self.is_healthy = False
                self.logger.error(f"L4 health check failed: {e}", exc_info=True)
                return False
        
        def should_store_in_tier(self, memory: MemoryItem) -> bool:
            """Persistent memory stores memories that have importance >= 0.8, are persistent, or user profile data."""
            return (
                memory.importance >= 0.8 or
                memory.memory_type == MemoryType.PERSISTENT or
                (memory.metadata and memory.metadata.get('category') == 'user_profile')
            )