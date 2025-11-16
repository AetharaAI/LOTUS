"""
LOTUS Memory System - Abstraction Layer

Provides a unified interface for the 4-tier memory architecture:
- L1 (Working Memory): Redis - immediate context
- L2 (Short-term Memory): Redis Streams - recent history
- L3 (Long-term Memory): ChromaDB - semantic search
- L4 (Persistent Memory): PostgreSQL - structured data
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis

# Optional heavy deps: import defensively so the package can be imported
# even when optional backends (ChromaDB, psycopg, sentence-transformers)
# are not installed in the environment.
try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None

try:
    import psycopg
except Exception:
    psycopg = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    # Provide a tiny fallback embedder with a compatible `encode` method.
    class _DummyEmbedder:
        def __init__(self, *args, **kwargs):
            pass

        def encode(self, text):
            # Return a small fixed-dimension embedding (list of floats).
            # It is intentionally simplistic: downstream code should
            # handle empty or trivial embeddings gracefully.
            return [0.0]

    SentenceTransformer = _DummyEmbedder


class MemoryItem:
    """Represents a single memory"""
    def __init__(self, content: str, memory_type: str, timestamp: float,
                 importance: float = 0.5, metadata: Dict = None):
        self.content = content
        self.type = memory_type
        self.timestamp = timestamp
        self.importance = importance
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "type": self.type,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "metadata": self.metadata
        }


class MemoryType:
    """Memory type constants"""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PERSISTENT = "persistent"


class WorkingMemory:
    """L1: Working memory using Redis"""

    def __init__(self, redis_client: redis.Redis, ttl_seconds: int = 600, max_items: int = 100):
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items

    async def store(self, key: str, data: Any, ttl: int = None):
        """Store data in working memory"""
        if ttl is None:
            ttl = self.ttl_seconds
        serialized = json.dumps(data)
        await self.redis.setex(f"working:{key}", ttl, serialized)

    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data from working memory"""
        value = await self.redis.get(f"working:{key}")
        if value:
            return json.loads(value)
        return None

    async def search(self, pattern: str) -> List[str]:
        """Search for keys matching pattern"""
        cursor = '0'
        keys = []
        while True:
            cursor, batch = await self.redis.scan(cursor, match=f"working:{pattern}", count=100)
            keys.extend(batch)
            if cursor == '0':
                break
        return keys

    async def get_all_for_consolidation(self) -> List[Dict[str, Any]]:
        """Return all working memories as a list of dicts for consolidation.

        This method is used by the consolidation process which may call
        `should_store_in_tier` on the target tier and then `store` the
        returned dicts. Returning simple dicts keeps this lightweight and
        compatible with the rest of the codebase.
        """
        # Prefer to use a dedicated timeline/list key (fast LRANGE) if available
        # Common names used in different implementations:
        # - 'lotus:memory:L1:timeline' (preferred, used by WorkingMemory implementation)
        # - 'working:timeline' (legacy)
        timeline_keys = [
            "lotus:memory:L1:timeline",
            "working:timeline",
            "lotus:memories:timeline",
        ]

        memories = []
        for tkey in timeline_keys:
            try:
                exists = await self.redis.exists(tkey)
                if exists:
                    ids = await self.redis.lrange(tkey, 0, -1)
                    for mem_id in ids:
                        if isinstance(mem_id, bytes):
                            mem_id = mem_id.decode('utf-8')
                        # Try to retrieve by id (strip any timeline prefix differences)
                        data = await self.retrieve(mem_id)
                        if data:
                            if isinstance(data, str):
                                try:
                                    data = json.loads(data)
                                except Exception:
                                    data = {"content": data}
                            memories.append(data)
                    return memories
            except Exception:
                # If any timeline access fails, continue to next option
                continue

        # Fallback: scan the keyspace (less efficient). Use SCAN cursor loop to
        # avoid blocking Redis for large keyspaces.
        cursor = 0
        try:
            while True:
                cursor, batch = await self.redis.scan(cursor=cursor, match="working:*", count=500)
                for k in batch:
                    if isinstance(k, bytes):
                        k = k.decode('utf-8')
                    mem_key = k.replace("working:", "")
                    data = await self.retrieve(mem_key)
                    if data:
                        if isinstance(data, str):
                            try:
                                data = json.loads(data)
                            except Exception:
                                data = {"content": data}
                        memories.append(data)
                if cursor == 0 or cursor == '0':
                    break
        except Exception:
            # On any failure return what we have so consolidation can proceed
            return memories

        return memories


class ShortTermMemory:
    """L2: Short-term memory using Redis Streams"""

    def __init__(self, redis_client: redis.Redis, ttl_hours: int = 24, max_items: int = 1000):
        self.redis = redis_client
        self.ttl_hours = ttl_hours
        self.max_items = max_items

    async def store(self, data: Dict[str, Any]) -> str:
        """Store data in short-term memory stream"""
        entry_id = await self.redis.xadd("lotus:memories:stream", data, maxlen=self.max_items)
        return entry_id

    async def retrieve_recent(self, count: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent entries from stream"""
        entries = await self.redis.xrevrange("lotus:memories:stream", count=count)
        return [
            {
                "id": entry_id,
                "data": {k.decode('utf-8'): v.decode('utf-8') for k, v in entry_data.items()}
            }
            for entry_id, entry_data in entries
        ]

    async def retrieve(self, pattern: str = "*", limit: int = 100) -> List[Dict[str, Any]]:
        """Generic retrieve for consolidation/testing compatibility.

        This returns the most recent entries filtered by a simple substring
        match against the `content` field. It's a lightweight helper used by
        consolidation code which expects a `.retrieve` method on L2.
        """
        recent = await self.retrieve_recent(count=limit)
        if pattern in (None, "*", ""):
            return recent[:limit]

        out = []
        pat = pattern.lower()
        for entry in recent:
            data = entry.get('data', {})
            content = data.get('content', '')
            if pat == '*' or pat in content.lower():
                out.append(entry)
                if len(out) >= limit:
                    break
        return out


class LongTermMemory:
    """L3: Long-term memory using ChromaDB"""

    def __init__(self, chroma_client: Any, embedder: Any,
                 collection_name: str = "lotus_memories", embedding_model: str = "all-MiniLM-L6-v2"):
        self.chroma = chroma_client
        self.embedder = embedder
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.collection = None

    async def initialize(self):
        """Initialize the long-term memory collection"""
        self.collection = self.chroma.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "LOTUS long-term memory storage"}
        )

    async def store(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Store content in long-term memory"""
        if not self.collection:
            await self.initialize()

        # Generate embedding
        embedding = self.embedder.encode(content).tolist()

        # Store in ChromaDB
        memory_id = f"mem_{int(time.time() * 1000000)}"
        self.collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata or {}],
            ids=[memory_id]
        )
        return memory_id

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search long-term memory using vector similarity"""
        if not self.collection:
            await self.initialize()

        # Generate query embedding
        query_embedding = self.embedder.encode(query).tolist()

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )

        memories = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                memories.append({
                    "content": doc,
                    "metadata": metadata,
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })

        return memories


class PersistentMemory:
    """L4: Persistent memory using PostgreSQL via SQLAlchemy"""

    def __init__(self, db_engine, table_name: str = "lotus_knowledge"):
        self.db_engine = db_engine
        self.table_name = table_name

    async def initialize(self):
        """Initialize database schema"""
        # Create table if it doesn't exist using SQLAlchemy
        from sqlalchemy import text
        async with self.db_engine.connect() as conn:
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    importance FLOAT DEFAULT 0.5,
                    metadata JSONB DEFAULT '{{}}'::jsonb
                )
            """))
            await conn.commit()

    async def store(self, content: str, memory_type: str, importance: float, metadata: Dict = None):
        """Store data in persistent memory"""
        from sqlalchemy import text
        async with self.db_engine.connect() as conn:
            await conn.execute(
                text(f"""
                INSERT INTO {self.table_name} (content, type, timestamp, importance, metadata)
                VALUES (:content, :type, :timestamp, :importance, :metadata)
                """),
                {
                    "content": content,
                    "type": memory_type,
                    "timestamp": datetime.now(),
                    "importance": importance,
                    "metadata": json.dumps(metadata or {})
                }
            )
            await conn.commit()

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search persistent memory (basic text search)"""
        from sqlalchemy import text
        async with self.db_engine.connect() as conn:
            result = await conn.execute(
                text(f"""
                SELECT content, type, timestamp, importance, metadata
                FROM {self.table_name}
                WHERE content ILIKE :query
                ORDER BY timestamp DESC
                LIMIT :limit
                """),
                {"query": f"%{query}%", "limit": limit}
            )
            rows = result.fetchall()

            return [
                {
                    "content": row[0],
                    "type": row[1],
                    "timestamp": row[2].timestamp() if hasattr(row[2], 'timestamp') else row[2],
                    "importance": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {}
                }
                for row in rows
            ]


class MemorySystem:
    """
    Unified memory system interface

    Handles all memory operations across 4 tiers
    """

    def __init__(self, redis_client: redis.Redis, chroma_client: Any,
                 postgres_conn, embedding_model: str = "all-MiniLM-L6-v2"):
        self.redis = redis_client
        self.chroma = chroma_client
        self.postgres = postgres_conn

        # Embedding model for vector search
        self.embedder = SentenceTransformer(embedding_model)

        # Initialize tier-specific systems
        self.working = WorkingMemory(redis_client)
        self.short_term = ShortTermMemory(redis_client)
        self.long_term = LongTermMemory(chroma_client, self.embedder)
        self.persistent = PersistentMemory(postgres_conn)  # postgres_conn is now SQLAlchemy engine

    async def initialize(self):
        """Initialize memory system"""
        await self.long_term.initialize()

    async def remember(self, content: str, memory_type: str = "episodic",
                      importance: float = 0.5, metadata: Dict = None) -> str:
        """
        Store a memory across appropriate tiers

        Args:
            content: The content to remember
            memory_type: Type of memory (episodic, semantic, procedural)
            importance: 0.0-1.0, determines which tiers to store in
            metadata: Additional context

        Returns:
            Memory ID
        """
        timestamp = time.time()
        memory_id = f"{memory_type}:{timestamp}"

        memory_dict = {
            "content": content,
            "type": memory_type,
            "timestamp": timestamp,
            "importance": importance,
            "metadata": metadata or {}
        }

        # L1: Always store in working memory (Redis)
        await self.working.store(memory_id, memory_dict, ttl=600)

        # L2: Add to short-term stream (Redis Streams)
        await self.short_term.store(memory_dict)

        # L3: If important enough, add to long-term (ChromaDB)
        if importance >= 0.5:
            await self.long_term.store(content, metadata)

        # L4: If critical fact, store in structured DB
        if importance >= 0.8 or memory_type == "persistent":
            await self.persistent.store(content, memory_type, importance, metadata)

        return memory_id

    async def recall(self, query: str, limit: int = 10,
                    memory_types: List[str] = None) -> List[MemoryItem]:
        """
        Retrieve relevant memories

        Searches across all tiers and returns most relevant

        Args:
            query: What to search for
            limit: Maximum number of memories to return
            memory_types: Filter by memory type

        Returns:
            List of MemoryItem objects, ranked by relevance
        """
        all_memories = []

        # Search L1: Working memory (fastest)
        working_keys = await self.working.search("*")
        for key in working_keys[:5]:  # Limit to avoid too many
            data = await self.working.retrieve(key.replace("working:", ""))
            if data and query.lower() in data["content"].lower():
                all_memories.append(MemoryItem(**data))

        # Search L2: Short-term memory
        short_term_data = await self.short_term.retrieve_recent(count=5)
        for entry in short_term_data:
            data = entry["data"]
            if query.lower() in data.get("content", "").lower():
                all_memories.append(MemoryItem(
                    content=data["content"],
                    memory_type=data["type"],
                    timestamp=float(data["timestamp"]),
                    importance=float(data.get("importance", 0.5)),
                    metadata=json.loads(data.get("metadata", "{}"))
                ))

        # Search L3: Long-term vector search (most relevant)
        if len(all_memories) < limit:
            long_term_results = await self.long_term.search(query, limit=limit - len(all_memories))
            for result in long_term_results:
                all_memories.append(MemoryItem(
                    content=result["content"],
                    memory_type=result["metadata"].get("type", "semantic"),
                    timestamp=result["metadata"].get("timestamp", time.time()),
                    importance=result["metadata"].get("importance", 0.5),
                    metadata=result["metadata"]
                ))

        # Filter by type if specified
        if memory_types:
            all_memories = [m for m in all_memories if m.type in memory_types]

        # Rank by relevance and recency
        ranked = self._rank_memories(all_memories, query)

        return ranked[:limit]

    def _rank_memories(self, memories: List[MemoryItem], query: str) -> List[MemoryItem]:
        """Rank memories by relevance and recency"""
        # Simple ranking: importance * recency_factor
        now = time.time()

        def score(mem: MemoryItem) -> float:
            # Recency factor (exponential decay)
            age_hours = (now - mem.timestamp) / 3600
            recency_factor = 0.5 ** (age_hours / 24)  # Half-life of 24 hours

            # Relevance factor (simple keyword matching)
            relevance = query.lower().count(mem.content.lower()[:20])

            return mem.importance * recency_factor * (1 + relevance)

        return sorted(memories, key=score, reverse=True)


class RetrievalConfig:
    """Configuration for memory retrieval"""

    def __init__(self, max_results: int = 10, similarity_threshold: float = 0.7,
                 recency_weight: float = 0.3, relevance_weight: float = 0.7):
        self.max_results = max_results
        self.similarity_threshold = similarity_threshold
        self.recency_weight = recency_weight
        self.relevance_weight = relevance_weight


class RetrievalStrategy:
    """Strategies for memory retrieval"""

    SEMANTIC = "semantic"  # Vector similarity search
    KEYWORD = "keyword"    # Text matching
    TEMPORAL = "temporal"  # Time-based retrieval
    HYBRID = "hybrid"      # Combination approach


class MemoryRetrieval:
    """Unified memory retrieval system"""

    def __init__(self, working_memory, short_term_memory, long_term_memory, persistent_memory):
        self.working = working_memory
        self.short_term = short_term_memory
        self.long_term = long_term_memory
        self.persistent = persistent_memory

    async def retrieve(self, query: str, strategy: str = RetrievalStrategy.HYBRID,
                      config: RetrievalConfig = None) -> List[MemoryItem]:
        """Retrieve memories using specified strategy"""
        if config is None:
            config = RetrievalConfig()

        if strategy == RetrievalStrategy.SEMANTIC:
            return await self._semantic_retrieval(query, config)
        elif strategy == RetrievalStrategy.KEYWORD:
            return await self._keyword_retrieval(query, config)
        elif strategy == RetrievalStrategy.TEMPORAL:
            return await self._temporal_retrieval(query, config)
        else:  # HYBRID
            return await self._hybrid_retrieval(query, config)

    async def _semantic_retrieval(self, query: str, config: RetrievalConfig) -> List[MemoryItem]:
        """Retrieve using semantic similarity"""
        # Search long-term memory (vector search). Be defensive: some
        # long-term shims may not implement `search` (older or noop
        # implementations), so handle that gracefully.
        results = []
        try:
            if hasattr(self.long_term, 'search'):
                results = await self.long_term.search(query, limit=config.max_results)
            elif hasattr(self.long_term, 'retrieve'):
                # Older API may expose `retrieve` which returns raw dicts or
                # MemoryItem objects depending on implementation.
                raw = await self.long_term.retrieve(query, limit=config.max_results)
                # Normalize to expected dict-like results if possible
                if raw:
                    results = []
                    for r in raw:
                        if hasattr(r, 'to_dict'):
                            results.append(r.to_dict())
                        elif isinstance(r, dict):
                            results.append(r)
                        else:
                            results.append({"content": str(r), "metadata": {}})
            else:
                # No vector search available; return empty list
                results = []
        except Exception:
            # If underlying backend fails, don't bubble the exception to callers
            results = []

        memories = []
        for result in results:
            if result.get("distance", 1.0) <= (1.0 - config.similarity_threshold):
                memories.append(MemoryItem(
                    content=result["content"],
                    memory_type=result["metadata"].get("type", "semantic"),
                    timestamp=result["metadata"].get("timestamp", time.time()),
                    importance=result["metadata"].get("importance", 0.5),
                    metadata=result["metadata"]
                ))

        return memories

    async def _keyword_retrieval(self, query: str, config: RetrievalConfig) -> List[MemoryItem]:
        """Retrieve using keyword matching"""
        # Search working memory first
        working_keys = await self.working.search("*")
        memories = []

        for key in working_keys[:config.max_results]:
            data = await self.working.retrieve(key.replace("working:", ""))
            if data and query.lower() in data["content"].lower():
                memories.append(MemoryItem(**data))

        # Search short-term memory
        short_term_data = await self.short_term.retrieve_recent(count=config.max_results)
        for entry in short_term_data:
            data = entry["data"]
            if query.lower() in data.get("content", "").lower():
                memories.append(MemoryItem(
                    content=data["content"],
                    memory_type=data["type"],
                    timestamp=float(data["timestamp"]),
                    importance=float(data.get("importance", 0.5)),
                    metadata=json.loads(data.get("metadata", "{}"))
                ))

        return memories[:config.max_results]

    async def _temporal_retrieval(self, query: str, config: RetrievalConfig) -> List[MemoryItem]:
        """Retrieve recent memories"""
        # Get recent entries from short-term memory
        short_term_data = await self.short_term.retrieve_recent(count=config.max_results)

        memories = []
        for entry in short_term_data:
            data = entry["data"]
            memories.append(MemoryItem(
                content=data["content"],
                memory_type=data["type"],
                timestamp=float(data["timestamp"]),
                importance=float(data.get("importance", 0.5)),
                metadata=json.loads(data.get("metadata", "{}"))
            ))

        return memories

    async def _hybrid_retrieval(self, query: str, config: RetrievalConfig) -> List[MemoryItem]:
        """Combine multiple retrieval strategies"""
        # Get results from all strategies
        semantic = await self._semantic_retrieval(query, config)
        keyword = await self._keyword_retrieval(query, config)
        temporal = await self._temporal_retrieval(query, config)

        # Combine and deduplicate
        all_memories = semantic + keyword + temporal
        seen = set()
        unique_memories = []

        for mem in all_memories:
            key = (mem.content, mem.timestamp)
            if key not in seen:
                seen.add(key)
                unique_memories.append(mem)

        # Score and rank
        now = time.time()
        def score(mem: MemoryItem) -> float:
            # Recency score
            age_hours = (now - mem.timestamp) / 3600
            recency_score = max(0, 1.0 - (age_hours / 24))  # Decay over 24 hours

            # Relevance score (simple keyword match)
            relevance_score = 1.0 if query.lower() in mem.content.lower() else 0.3

            # Importance score
            importance_score = mem.importance

            return (config.recency_weight * recency_score +
                   config.relevance_weight * relevance_score +
                   (1.0 - config.recency_weight - config.relevance_weight) * importance_score)

        ranked = sorted(unique_memories, key=score, reverse=True)
        return ranked[:config.max_results]