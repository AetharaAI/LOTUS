"""
LOTUS Memory Module - Coordinator for 4-Tier Memory System

This module manages the complete memory architecture and exposes
it via the event bus for other modules to use.
"""

import asyncio
import time
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
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer(self.config.get("memory.long_term.embedding_model", "all-MiniLM-L6-v2"))
        self.L3 = LongTermMemory(
            chroma_client,
            embedder,
            collection_name=self.config.get("memory.long_term.collection_name", "lotus_memories"),
            embedding_model=self.config.get("memory.long_term.embedding_model", "all-MiniLM-L6-v2")
        )
        
        # Initialize L4: Persistent Memory (PostgreSQL)
        self.L4 = PersistentMemory(
            postgres_conn,
            table_name=self.config.get("memory.persistent.table_name", "lotus_knowledge")
        )
        
        # Create database schema
        await self.L4.initialize()
        
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
        if importance >= 0.8:
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
        
        # Build retrieval config
        config = RetrievalConfig(
            strategy=RetrievalStrategy(strategy),
            max_results=max_results
        )
        
        # Retrieve memories
        memories = await self.retrieval.retrieve(query, config)
        
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
                
                # L3 → L4 consolidation
                l3_memories = await self.L3.get_important_memories(min_importance=0.8)
                l3_promoted = 0
                
                for memory in l3_memories:
                    # Check if should be in L4
                    if self.L4.should_store_in_tier(memory):
                        await self.L4.store(memory)
                        l3_promoted += 1
                
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