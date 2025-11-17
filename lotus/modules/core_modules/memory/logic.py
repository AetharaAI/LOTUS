"""
LOTUS Memory Module - Coordinator for 4-Tier Memory System

This module manages the complete memory architecture and exposes
it via the event bus for other modules to use.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.module import BaseModule
from lib.decorators import on_event, tool, periodic
from lib.memory import (
    MemoryItem, MemoryType,
    WorkingMemory, ShortTermMemory, LongTermMemory, PersistentMemory,
    MemoryRetrieval, RetrievalConfig, RetrievalStrategy
)


class MemoryModule(BaseModule):
    """
    Memory System Coordinator
    
    Manages all 4 tiers and provides memory services to other modules
    """
    
    async def initialize(self) -> None:
        """Initialize all memory tiers"""
        self.logger.info("Initializing 4-tier memory system")
        
        # Get connections from nucleus
        redis_client = self.config.get("services.redis")
        chroma_client = self.config.get("services.chroma")
        postgres_conn = self.config.get("services.db_engine")
        
        # Initialize L1: Working Memory (Redis)
        self.L1 = WorkingMemory(
            redis_client,
            ttl_seconds=self.config.get("memory.working_memory.ttl_seconds", 600),
            max_items=self.config.get("memory.working_memory.max_items", 100)
        )
        
        # Initialize L2: Short-term Memory (Redis Streams)
        self.L2 = ShortTermMemory(
            redis_client,
            ttl_hours=self.config.get("memory.short_term.ttl_hours", 24),
            max_items=self.config.get("memory.short_term.max_items", 1000)
        )
        
        # Initialize L3: Long-term Memory (ChromaDB)
        # Import the SentenceTransformer via the lib.memory package which
        # defensively provides a dummy fallback when the heavy dependency
        # (torch / sentence-transformers) is not available or fails to
        # initialize (for example due to missing CUDA libraries).
        try:
            from lib.memory import SentenceTransformer
            embedder = SentenceTransformer(self.config.get("memory.long_term.embedding_model", "all-MiniLM-L6-v2"))
        except Exception as e:
            self.logger.warning(f"SentenceTransformer not available, using dummy embedder: {e}")
            class _EmbedderShim:
                def encode(self, text):
                    return [0.0]
            embedder = _EmbedderShim()

        # If Chroma isn't configured/available, create a lightweight no-op
        # long-term memory shim so retrieval calls succeed (return empty
        # results) instead of raising AttributeError. This keeps the runtime
        # usable in environments where Chroma is optional.
        if chroma_client is None:
            class NoOpLongTermMemory:
                def __init__(self, *args, **kwargs):
                    self.collection = None

                async def initialize(self):
                    return

                async def store(self, *args, **kwargs):
                    return None

                # Provide both `search` and `retrieve` variants because the
                # codebase contains two slightly different memory abstractions
                # (legacy and newer). Implement both to be compatible.
                async def search(self, query: str, limit: int = 10):
                    return []

                async def retrieve(self, *args, **kwargs):
                    # Old callers may call retrieve(query, limit=..)
                    return []

                async def find_similar(self, *args, **kwargs):
                    return []

                async def get_important_memories(self, *args, **kwargs):
                    return []

                async def get_by_type(self, *args, **kwargs):
                    return []

                def should_store_in_tier(self, *_args, **_kwargs):
                    return False

            self.L3 = NoOpLongTermMemory()
        else:
            self.L3 = LongTermMemory(
                chroma_client,
                collection_name=self.config.get("memory.long_term.collection_name", "lotus_memories"),
                embedder=embedder
            )
        
        # Initialize L4: Persistent Memory (PostgreSQL)
        try:
            # PersistentMemory may require psycopg (psycopg[binary])
            self.L4 = PersistentMemory(
                postgres_conn,
                table_name=self.config.get("memory.persistent.table_name", "lotus_knowledge")
            )

            # Create database schema
            await self.L4.initialize()
        except Exception as e:
            # If persistent layer can't be initialized (missing deps, schema issues),
            # fall back to a no-op persistent memory shim so callers can
            # unconditionally call `.store()` / `.retrieve()` without checks.
            self.logger.warning(f"Persistent memory (L4) not initialized: {e}")

            class NoOpPersistentMemory:
                async def initialize(self):
                    return

                async def store(self, *args, **kwargs):
                    return None

                async def retrieve(self, *args, **kwargs):
                    return []

                def should_store_in_tier(self, *_args, **_kwargs):
                    return False

                async def get_stats(self):
                    return {"count": 0}

                async def health_check(self):
                    return True

            self.L4 = NoOpPersistentMemory()
        
        # Initialize retrieval system
        self.retrieval = MemoryRetrieval(self.L1, self.L2, self.L3, self.L4)
        
        # Start background consolidation if enabled
        if self.config.get("memory.consolidation.enabled", True):
            interval_minutes = self.config.get("memory.consolidation.interval_minutes", 30)
            asyncio.create_task(self._consolidation_loop(interval_minutes))
        
        self.logger.info("Memory system initialized successfully")
    
    @on_event("memory.store")
    async def handle_store(self, event_data: Dict) -> None:
        """
        Store a memory in appropriate tiers
        
        Event data should contain:
        - content: str
        - memory_type: str (episodic, semantic, procedural, working)
        - importance: float (0.0-1.0)
        - metadata: dict (optional)
        """
        # Parse event data
        content = event_data.get("content")
        memory_type = MemoryType(event_data.get("memory_type", "episodic"))
        importance = event_data.get("importance", 0.5)
        metadata = event_data.get("metadata", {})
        source_module = event_data.get("source_module")
        
        # Create memory item
        memory = MemoryItem(
            content=content,
            memory_type=memory_type,
            timestamp=time.time(),
            importance=importance,
            metadata=metadata,
            source_module=source_module
        )
        
        # Store in L1 (always)
        memory_id = await self.L1.store(memory)
        
        # Store in L2 (always)
        await self.L2.store(memory)
        
        # Store in L3 if important enough
        if importance >= 0.5:
            await self.L3.store(memory)
        
        # Store in L4 if critical
        if importance >= 0.8 and self.L4 is not None:
            await self.L4.store(memory)
        
        # Publish confirmation
        await self.publish("memory.stored", {
            "memory_id": memory_id,
            "tiers": self._get_stored_tiers(importance)
        })
        
        self.logger.debug(f"Stored memory: {content[:50]}... (ID: {memory_id})")
    
    @on_event("memory.retrieve")
    async def handle_retrieve(self, event_data: Dict) -> None:
        """
        Retrieve memories by query
        
        Event data should contain:
        - query: str
        - max_results: int (optional)
        - strategy: str (optional)
        """
        query = event_data.get("query")
        max_results = event_data.get("max_results", 10)
        strategy = event_data.get("strategy", "comprehensive")
        
        # Build retrieval config (RetrievalConfig does not accept a strategy
        # parameter; the retrieval method accepts strategy separately)
        config = RetrievalConfig(
            max_results=max_results
        )

        # Retrieve memories using the requested strategy string
        memories = await self.retrieval.retrieve(query, strategy=strategy, config=config)
        
        # Publish results
        await self.publish("memory.retrieved", {
            "query": query,
            "count": len(memories),
            "memories": [m.to_dict() for m in memories]
        })
        
        self.logger.debug(f"Retrieved {len(memories)} memories for query: {query}")
    
    @on_event("memory.get_context")
    async def handle_get_context(self, event_data: Dict) -> None:
        """
        Get recent context for reasoning engine
        
        Event data should contain:
        - minutes: int (default: 10)
        """
        minutes = event_data.get("minutes", 10)
        
        # Get recent context
        context = await self.retrieval.get_recent_context(minutes)
        
        # Publish context
        await self.publish("memory.context", {
            "minutes": minutes,
            "count": len(context),
            "memories": [m.to_dict() for m in context]
        })
    
    @tool("get_memory_stats")
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return await self.retrieval.get_stats()
    
    async def _consolidation_loop(self, interval_minutes: int) -> None:
        """
        Background memory consolidation
        
        Periodically moves memories between tiers based on importance
        and access patterns
        """
        interval_seconds = interval_minutes * 60
        
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                
                self.logger.info("Starting memory consolidation...")
                
                # Get consolidation threshold
                threshold = self.config.get("memory.consolidation.importance_threshold", 0.5)
                
                # L1 → L2 consolidation
                l1_memories = await self.L1.get_all_for_consolidation()
                l1_promoted = 0
                
                for memory in l1_memories:
                    # Check if should be in L2
                    if self.L2.should_store_in_tier(memory):
                        await self.L2.store(memory)
                        l1_promoted += 1
                
                # L2 → L3 consolidation
                l2_memories = await self.L2.retrieve("*", limit=1000)
                l2_promoted = 0
                
                for memory in l2_memories:
                    # Check if should be in L3
                    if self.L3.should_store_in_tier(memory):
                        await self.L3.store(memory)
                        l2_promoted += 1
                
                # L3 → L4 consolidation (only if L4 available)
                l3_promoted = 0
                if self.L4 is not None:
                    l3_memories = await self.L3.get_important_memories(min_importance=0.8)
                    for memory in l3_memories:
                        # Check if should be in L4
                        try:
                            if self.L4.should_store_in_tier(memory):
                                await self.L4.store(memory)
                                l3_promoted += 1
                        except Exception as e:
                            self.logger.warning(f"Error promoting memory to L4: {e}")
                
                # Publish consolidation results
                await self.publish("memory.consolidated", {
                    "l1_to_l2": l1_promoted,
                    "l2_to_l3": l2_promoted,
                    "l3_to_l4": l3_promoted
                })
                
                self.logger.info(f"Consolidation complete: L1→L2:{l1_promoted}, L2→L3:{l2_promoted}, L3→L4:{l3_promoted}")
                
            except Exception as e:
                self.logger.error(f"Consolidation error: {e}")
    
    def _get_stored_tiers(self, importance: float) -> List[str]:
        """Determine which tiers a memory was stored in"""
        tiers = ["L1", "L2"]
        if importance >= 0.5:
            tiers.append("L3")
        if importance >= 0.8:
            tiers.append("L4")
        return tiers

    # ------------------------------------------------------------------
    # Programmatic API (facade) for other modules
    # Reasoning and other modules expect methods like `recall` and
    # `remember` to be available on the memory service instance.
    # These methods reuse the internal handlers to provide a simple
    # async interface.
    # ------------------------------------------------------------------
    async def recall(self, query: str, limit: int = 10, strategy: str = "comprehensive") -> List[Any]:
        """Programmatic retrieval API used by other modules.

        Returns a list of MemoryItem objects (not serialized).
        """
        # Build retrieval config and pass strategy string to retrieval
        config = RetrievalConfig(max_results=limit)
        try:
            if hasattr(self, 'retrieval') and self.retrieval is not None:
                # Some retrieval implementations accept (query, strategy=..., config=...)
                # while others accept only (query, config). Try the common
                # signatures gracefully.
                try:
                    memories = await self.retrieval.retrieve(query, strategy=strategy, config=config)
                except TypeError:
                    memories = await self.retrieval.retrieve(query, config=config)

                return memories or []
            else:
                return []
        except Exception as e:
            # If any backend is missing or misbehaving, log and return empty
            self.logger.warning(f"Memory recall failed, returning empty list: {e}")
            return []

    # Legacy compatibility methods -------------------------------------
    async def search(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Compatibility wrapper so callers can use memory.search(...).

        Returns a list of simple dicts (serialized MemoryItem) to match
        existing call-sites in reasoning and tools.
        """
        try:
            results = await self.recall(query, limit=limit, strategy=kwargs.get('strategy', 'semantic'))
            # Convert MemoryItem objects to dicts for older callers
            return [m.to_dict() if hasattr(m, 'to_dict') else dict(m) for m in (results or [])]
        except Exception as e:
            self.logger.debug(f"Legacy search wrapper failed: {e}")
            return []

    async def store(self, payload: Dict[str, Any]) -> Optional[str]:
        """Compatibility wrapper for memory.store(...) used by tools.

        Accepts either a MemoryItem-like dict or explicit fields.
        """
        try:
            # If payload is already in the expected shape, use it
            content = payload.get('content') if isinstance(payload, dict) else str(payload)
            importance = payload.get('importance', 0.5) if isinstance(payload, dict) else 0.5
            memory_type = payload.get('type', payload.get('memory_type', 'episodic')) if isinstance(payload, dict) else 'episodic'
            metadata = payload.get('metadata', {}) if isinstance(payload, dict) else {}

            return await self.remember(content=content, memory_type=memory_type, importance=importance, metadata=metadata)
        except Exception as e:
            self.logger.debug(f"Legacy store wrapper failed: {e}")
            return None

    async def get_recent(self, type: str = "conversation", limit: int = 10) -> List[Dict[str, Any]]:
        """Convenience wrapper used by ContextBuilder._get_conversation_history

        This maps to short-term or working memory retrieval as appropriate.
        """
        try:
            # Try working memory helper first
            if type == "conversation":
                # Attempt to read recent items from L2 short-term stream
                recent = await self.L2.retrieve_recent(count=limit)
                # Normalize entries
                out = []
                for entry in recent:
                    data = entry.get('data', {})
                    out.append({
                        'content': data.get('content'),
                        'timestamp': float(data.get('timestamp', time.time())),
                        'metadata': data.get('metadata', {})
                    })
                return out
            else:
                return []
        except Exception as e:
            self.logger.debug(f"get_recent wrapper failed: {e}")
            return []

    async def get_working_memory(self) -> List[Dict[str, Any]]:
        """Return a small list of working memory entries for context builders."""
        try:
            keys = await self.L1.search("*")
            out = []
            for k in keys[:10]:
                data = await self.L1.retrieve(k.replace('working:', ''))
                if data:
                    out.append(data)
            return out
        except Exception as e:
            self.logger.debug(f"get_working_memory failed: {e}")
            return []

    async def remember(
        self,
        content: str,
        memory_type: str = "episodic",
        importance: float = 0.5,
        metadata: Optional[Dict] = None,
        source_module: Optional[str] = None
    ) -> Optional[str]:
        """Programmatic store API used by other modules.

        Mirrors the behavior of the `memory.store` event handler and
        returns the L1 memory id when available.
        """
        metadata = metadata or {}

        memory = MemoryItem(
            content=content,
            memory_type=MemoryType(memory_type),
            timestamp=time.time(),
            importance=importance,
            metadata=metadata,
            source_module=source_module
        )

        # Store in L1 (always)
        memory_id = await self.L1.store(memory)

        # Store in L2 (always)
        await self.L2.store(memory)

        # Store in L3 if important enough
        if importance >= 0.5:
            await self.L3.store(memory)

        # Store in L4 if critical
        if importance >= 0.8:
            await self.L4.store(memory)

        return memory_id