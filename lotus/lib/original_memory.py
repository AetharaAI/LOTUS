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
import chromadb
from chromadb.config import Settings
import psycopg
from sentence_transformers import SentenceTransformer


class Memory:
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


class MemorySystem:
    """
    Unified memory system interface
    
    Handles all memory operations across 4 tiers
    """
    
    def __init__(self, redis_client: redis.Redis, chroma_client: chromadb.Client, 
                 postgres_conn, embedding_model: str = "all-MiniLM-L6-v2"):
        self.redis = redis_client
        self.chroma = chroma_client
        self.postgres = postgres_conn
        
        # Embedding model for vector search
        self.embedder = SentenceTransformer(embedding_model)
        
        # Initialize collections
        self.collections = {}
        
    async def initialize(self):
        """Initialize memory system"""
        # Create default ChromaDB collection
        try:
            self.collections["default"] = self.chroma.get_or_create_collection(
                name="lotus_memories",
                metadata={"description": "LOTUS long-term memory storage"}
            )
        except Exception as e:
            raise Exception(f"Failed to initialize memory system: {e}")
    
    # ========================================
    # HIGH-LEVEL INTERFACE
    # ========================================
    
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
        await self.redis.setex(
            f"working:{memory_id}",
            600,  # 10 minutes TTL
            json.dumps(memory_dict)
        )
        
        # L2: Add to short-term stream (Redis Streams)
        await self.redis.xadd(
            "lotus:memories:stream",
            memory_dict
        )
        
        # L3: If important enough, add to long-term (ChromaDB)
        if importance >= 0.5:
            await self._store_long_term(content, memory_type, importance, metadata)
        
        # L4: If critical fact, store in structured DB
        if importance >= 0.8 or memory_type == "persistent":
            await self._store_persistent(content, memory_type, importance, metadata)
        
        return memory_id
    
    async def recall(self, query: str, limit: int = 10, 
                    memory_types: List[str] = None) -> List[Memory]:
        """
        Retrieve relevant memories
        
        Searches across all tiers and returns most relevant
        
        Args:
            query: What to search for
            limit: Maximum number of memories to return
            memory_types: Filter by memory type
            
        Returns:
            List of Memory objects, ranked by relevance
        """
        all_memories = []
        
        # Search L1: Working memory (fastest)
        working = await self._search_working(query, limit=5)
        all_memories.extend(working)
        
        # Search L2: Short-term memory
        short_term = await self._search_short_term(query, limit=5)
        all_memories.extend(short_term)
        
        # Search L3: Long-term vector search (most relevant)
        if len(all_memories) < limit:
            long_term = await self._search_long_term(query, limit=limit - len(all_memories))
            all_memories.extend(long_term)
        
        # Filter by type if specified
        if memory_types:
            all_memories = [m for m in all_memories if m.type in memory_types]
        
        # Rank by relevance and recency
        ranked = self._rank_memories(all_memories, query)
        
        return ranked[:limit]
    
    async def forget(self, memory_id: str):
        """Remove a memory from all tiers"""
        # Remove from working memory
        await self.redis.delete(f"working:{memory_id}")
        
        # Note: Can't easily delete from streams, they'll expire
        # TODO: Implement deletion from ChromaDB and PostgreSQL
    
    # ========================================
    # MODULE-SPECIFIC STATE
    # ========================================
    
    async def get_state(self, module_name: str, key: str) -> Optional[Any]:
        """Get module-specific state"""
        value = await self.redis.get(f"module:{module_name}:state:{key}")
        if value:
            return json.loads(value)
        return None
    
    async def set_state(self, module_name: str, key: str, value: Any, 
                       ttl: Optional[int] = None):
        """Set module-specific state"""
        serialized = json.dumps(value)
        if ttl:
            await self.redis.setex(f"module:{module_name}:state:{key}", ttl, serialized)
        else:
            await self.redis.set(f"module:{module_name}:state:{key}", serialized)
    
    # ========================================
    # TIER-SPECIFIC IMPLEMENTATIONS
    # ========================================
    
    async def _search_working(self, query: str, limit: int) -> List[Memory]:
        """Search working memory (L1)"""
        memories = []
        
        # Get all working memory keys
        cursor = '0'
        while True:
            cursor, keys = await self.redis.scan(
                cursor, match="working:*", count=100
            )
            
            for key in keys:
                value = await self.redis.get(key)
                if value:
                    mem_dict = json.loads(value)
                    if query.lower() in mem_dict["content"].lower():
                        memories.append(Memory(**mem_dict))
            
            if cursor == '0':
                break
        
        return memories[:limit]
    
    async def _search_short_term(self, query: str, limit: int) -> List[Memory]:
        """Search short-term memory (L2)"""
        memories = []
        
        # Read from stream (last 1000 entries)
        entries = await self.redis.xrevrange(
            "lotus:memories:stream",
            count=1000
        )
        
        for entry_id, entry_data in entries:
            if query.lower() in entry_data.get(b'content', b'').decode('utf-8').lower():
                mem = Memory(
                    content=entry_data.get(b'content', b'').decode('utf-8'),
                    memory_type=entry_data.get(b'type', b'').decode('utf-8'),
                    timestamp=float(entry_data.get(b'timestamp', 0)),
                    importance=float(entry_data.get(b'importance', 0.5))
                )
                memories.append(mem)
                
                if len(memories) >= limit:
                    break
        
        return memories
    
    async def _search_long_term(self, query: str, limit: int) -> List[Memory]:
        """Search long-term memory (L3) using vector similarity"""
        # Generate query embedding
        query_embedding = self.embedder.encode(query).tolist()
        
        # Query ChromaDB
        results = self.collections["default"].query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        
        memories = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                mem = Memory(
                    content=doc,
                    memory_type=metadata.get('type', 'semantic'),
                    timestamp=metadata.get('timestamp', time.time()),
                    importance=metadata.get('importance', 0.5),
                    metadata=metadata
                )
                memories.append(mem)
        
        return memories
    
    async def _store_long_term(self, content: str, memory_type: str, 
                               importance: float, metadata: Dict):
        """Store in long-term memory (L3)"""
        # Generate embedding
        embedding = self.embedder.encode(content).tolist()
        
        # Store in ChromaDB
        self.collections["default"].add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "type": memory_type,
                "timestamp": time.time(),
                "importance": importance,
                **(metadata or {})
            }],
            ids=[f"mem_{int(time.time() * 1000000)}"]
        )
    
    async def _store_persistent(self, content: str, memory_type: str,
                                importance: float, metadata: Dict):
        """Store in persistent memory (L4)"""
        # Store in PostgreSQL
        async with self.postgres.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO memories (content, type, timestamp, importance, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (content, memory_type, datetime.now(), importance, json.dumps(metadata))
            )
            await self.postgres.commit()
    
    def _rank_memories(self, memories: List[Memory], query: str) -> List[Memory]:
        """Rank memories by relevance and recency"""
        # Simple ranking: importance * recency_factor
        now = time.time()
        
        def score(mem: Memory) -> float:
            # Recency factor (exponential decay)
            age_hours = (now - mem.timestamp) / 3600
            recency_factor = 0.5 ** (age_hours / 24)  # Half-life of 24 hours
            
            # Relevance factor (simple keyword matching)
            relevance = query.lower().count(mem.content.lower()[:20])
            
            return mem.importance * recency_factor * (1 + relevance)
        
        return sorted(memories, key=score, reverse=True)
    
    # ========================================
    # CONSOLIDATION
    # ========================================
    
    async def consolidate(self):
        """
        Move memories from short-term to long-term
        
        Called periodically by memory module
        """
        # Get last hour from stream
        one_hour_ago = (time.time() - 3600) * 1000
        entries = await self.redis.xrange(
            "lotus:memories:stream",
            min=str(int(one_hour_ago))
        )
        
        # Extract important memories
        for entry_id, entry_data in entries:
            importance = float(entry_data.get(b'importance', 0))
            
            if importance >= 0.6:
                content = entry_data.get(b'content', b'').decode('utf-8')
                memory_type = entry_data.get(b'type', b'').decode('utf-8')
                
                # Store in long-term
                await self._store_long_term(content, memory_type, importance, {})