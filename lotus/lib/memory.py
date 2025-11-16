"""
LOTUS Memory System Classes

Provides the 4-tier memory architecture:
- L1: Working Memory (Redis, ~10 mins TTL)
- L2: Short-term Memory (Redis Streams, ~24 hours)
- L3: Long-term Memory (ChromaDB, semantic search)
- L4: Persistent Memory (PostgreSQL, permanent storage)
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta

from .logging import get_logger


logger = get_logger("memory")


# Try to import sentence-transformers (optional)
try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    SentenceTransformer = _SentenceTransformer
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    # Provide a dummy class if not available
    class SentenceTransformer:
        def __init__(self, *args, **kwargs):
            logger.warning("sentence-transformers not available, using dummy embedder")

        def encode(self, text):
            return [0.0] * 384  # Return dummy embedding


class MemoryType(Enum):
    """Types of memory items"""
    PERCEPTION = "perception"  # Input from perception module
    THOUGHT = "thought"        # Reasoning outputs
    ACTION = "action"          # Actions taken
    RESULT = "result"          # Action results
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"


@dataclass
class MemoryItem:
    """
    A single memory item

    Can be stored in any tier of the memory system.
    """
    id: str
    type: MemoryType
    content: Any
    timestamp: str
    metadata: Dict[str, Any] = None
    importance: float = 0.5  # 0-1 scale
    tags: List[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['type'] = self.type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryItem':
        """Create from dictionary"""
        if 'type' in data and isinstance(data['type'], str):
            data['type'] = MemoryType(data['type'])
        return cls(**data)


class WorkingMemory:
    """
    L1: Working Memory

    Fast, short-lived memory using Redis.
    Stores current context and recently accessed items.
    """

    def __init__(self, redis_client: Any, ttl_seconds: int = 600, max_items: int = 100):
        """
        Initialize working memory

        Args:
            redis_client: Redis client instance
            ttl_seconds: Time-to-live for items
            max_items: Maximum items to keep
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self.key_prefix = "lotus:working_memory:"

    async def store(self, item: MemoryItem) -> None:
        """Store item in working memory"""
        key = f"{self.key_prefix}{item.id}"
        value = json.dumps(item.to_dict())

        if self.redis:
            await self.redis.setex(key, self.ttl_seconds, value)

    async def recall(self, item_id: str) -> Optional[MemoryItem]:
        """Recall item by ID"""
        key = f"{self.key_prefix}{item_id}"

        if self.redis:
            value = await self.redis.get(key)
            if value:
                return MemoryItem.from_dict(json.loads(value))

        return None

    async def clear(self) -> None:
        """Clear all working memory"""
        if self.redis:
            keys = await self.redis.keys(f"{self.key_prefix}*")
            if keys:
                await self.redis.delete(*keys)


class ShortTermMemory:
    """
    L2: Short-term Memory

    Stores recent history using Redis Streams.
    Maintains temporal ordering and allows replay.
    """

    def __init__(self, redis_client: Any, ttl_hours: int = 24, max_items: int = 1000):
        """
        Initialize short-term memory

        Args:
            redis_client: Redis client instance
            ttl_hours: Hours to keep items
            max_items: Maximum items to keep
        """
        self.redis = redis_client
        self.ttl_hours = ttl_hours
        self.max_items = max_items
        self.stream_key = "lotus:short_term_memory"

    async def store(self, item: MemoryItem) -> None:
        """Store item in short-term memory"""
        if self.redis:
            await self.redis.xadd(
                self.stream_key,
                {'data': json.dumps(item.to_dict())},
                maxlen=self.max_items
            )

    async def recall_recent(self, count: int = 10) -> List[MemoryItem]:
        """Recall recent items"""
        if not self.redis:
            return []

        items = await self.redis.xrevrange(self.stream_key, count=count)
        memories = []

        for item_id, data in items:
            memory_data = json.loads(data[b'data'])
            memories.append(MemoryItem.from_dict(memory_data))

        return memories


class LongTermMemory:
    """
    L3: Long-term Memory

    Semantic memory using ChromaDB for similarity search.
    Stores important memories with embeddings.
    """

    def __init__(self, chroma_client: Any, collection_name: str, embedder: Any):
        """
        Initialize long-term memory

        Args:
            chroma_client: ChromaDB client instance
            collection_name: Name of collection
            embedder: Embedding model (SentenceTransformer)
        """
        self.chroma = chroma_client
        self.collection_name = collection_name
        self.embedder = embedder
        self.collection = None

    async def initialize(self) -> None:
        """Initialize collection"""
        if self.chroma:
            try:
                self.collection = self.chroma.get_or_create_collection(
                    name=self.collection_name
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB collection: {e}")

    async def store(self, item: MemoryItem) -> None:
        """Store item in long-term memory"""
        if not self.collection:
            return

        # Create embedding
        content_text = str(item.content)
        embedding = self.embedder.encode(content_text).tolist()

        # Store in ChromaDB
        try:
            self.collection.add(
                ids=[item.id],
                embeddings=[embedding],
                documents=[content_text],
                metadatas=[{
                    'type': item.type.value,
                    'timestamp': item.timestamp,
                    'importance': item.importance,
                    **item.metadata
                }]
            )
        except Exception as e:
            logger.error(f"Failed to store in long-term memory: {e}")

    async def search(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Search for similar memories"""
        if not self.collection:
            return []

        # Create query embedding
        query_embedding = self.embedder.encode(query).tolist()

        # Search
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

            memories = []
            if results['ids']:
                for i, item_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    content = results['documents'][0][i]

                    memory = MemoryItem(
                        id=item_id,
                        type=MemoryType(metadata.get('type', 'knowledge')),
                        content=content,
                        timestamp=metadata.get('timestamp', ''),
                        importance=metadata.get('importance', 0.5),
                        metadata=metadata
                    )
                    memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"Failed to search long-term memory: {e}")
            return []


class PersistentMemory:
    """
    L4: Persistent Memory

    Permanent storage using PostgreSQL.
    Stores critical knowledge and system state.
    """

    def __init__(self, db_engine: Any, table_name: str = "lotus_knowledge"):
        """
        Initialize persistent memory

        Args:
            db_engine: SQLAlchemy engine or connection
            table_name: Database table name
        """
        self.db_engine = db_engine
        self.table_name = table_name

    async def store(self, item: MemoryItem) -> None:
        """Store item in persistent memory"""
        # This would use SQLAlchemy to insert into database
        # For now, just log (database setup required)
        logger.debug(f"Would store in persistent memory: {item.id}")

    async def search(self, query: Dict[str, Any]) -> List[MemoryItem]:
        """Search persistent memory"""
        # This would use SQLAlchemy to query database
        logger.debug(f"Would search persistent memory: {query}")
        return []


class RetrievalStrategy(Enum):
    """Memory retrieval strategies"""
    RECENT = "recent"              # Most recent items
    IMPORTANT = "important"        # Highest importance
    SEMANTIC = "semantic"          # Semantic similarity
    COMBINED = "combined"          # Combination of strategies


@dataclass
class RetrievalConfig:
    """Configuration for memory retrieval"""
    strategy: RetrievalStrategy = RetrievalStrategy.COMBINED
    max_items: int = 10
    min_importance: float = 0.0
    time_window_hours: Optional[int] = None


class MemoryRetrieval:
    """
    Unified memory retrieval across all tiers

    Provides intelligent retrieval strategies.
    """

    def __init__(self, L1: WorkingMemory, L2: ShortTermMemory,
                 L3: LongTermMemory, L4: PersistentMemory):
        """
        Initialize memory retrieval

        Args:
            L1: Working memory instance
            L2: Short-term memory instance
            L3: Long-term memory instance
            L4: Persistent memory instance
        """
        self.L1 = L1
        self.L2 = L2
        self.L3 = L3
        self.L4 = L4

    async def retrieve(self, query: str, config: RetrievalConfig = None) -> List[MemoryItem]:
        """
        Retrieve memories using specified strategy

        Args:
            query: Search query
            config: Retrieval configuration

        Returns:
            List of relevant memories
        """
        if config is None:
            config = RetrievalConfig()

        memories = []

        if config.strategy == RetrievalStrategy.RECENT:
            # Get recent from L2
            memories = await self.L2.recall_recent(config.max_items)

        elif config.strategy == RetrievalStrategy.SEMANTIC:
            # Search L3 for semantic similarity
            memories = await self.L3.search(query, config.max_items)

        elif config.strategy == RetrievalStrategy.COMBINED:
            # Combine recent and semantic
            recent = await self.L2.recall_recent(config.max_items // 2)
            semantic = await self.L3.search(query, config.max_items // 2)
            memories = recent + semantic

        # Filter by importance
        if config.min_importance > 0:
            memories = [m for m in memories if m.importance >= config.min_importance]

        # Limit results
        return memories[:config.max_items]
