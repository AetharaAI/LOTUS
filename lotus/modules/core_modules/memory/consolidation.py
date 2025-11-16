"""
LOTUS Memory Module - 4-Tier Memory System Coordinator

Manages the complete memory architecture and integrates with the event bus.
Uses the new modular tier implementations from lib/memory/
"""

import asyncio
import time
from typing import Dict, List, Any, Optional

from lotus.lib.module import BaseModule
from lotus.lib.decorators import on_event, tool, periodic
from lotus.lib.memory import (
    MemoryItem, MemoryType,
    WorkingMemory, ShortTermMemory, LongTermMemory, PersistentMemory,
    MemoryRetrieval, RetrievalConfig, RetrievalStrategy
)


class MemoryModule(BaseModule):
    """
    Memory System Coordinator
    
    Manages all 4 tiers and provides memory services to other modules
    via the event bus.
    """
    
    async def initialize(self) -> None:
        """Initialize all memory tiers"""
        self.logger.info("Initializing 4-tier memory system")
        
        # Get backend connections from nucleus
        # These should be set up in nucleus.py and stored in config
        redis_client = self.config.get("connections.redis")
        chroma_client = self.config.get("connections.chromadb")
        postgres_conn = self.config.get("connections.postgres")
        
        if not all([redis_client, chroma_client, postgres_conn]):
            self.logger.error("Missing backend connections! Check nucleus.py setup")
            raise RuntimeError("Memory backends not initialized")
        
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
        self.L3 = LongTermMemory(
            chroma_client,
            collection_name=self.config.get("memory.long_term.collection_name", "lotus_memories"),
            embedding_model=self.config.get("memory.long_term.embedding_model", "all-MiniLM-L6-v2")
        )
        
        # Initialize L4: Persistent Memory (PostgreSQL)
        self.L4 = PersistentMemory(
            postgres_conn,
            table_name=self.config.get("memory.persistent.table_name", "lotus_knowledge")
        )
        
        # Create database schema for L4
        await self.L4.initialize()
        
        # Initialize retrieval system
        self.retrieval = MemoryRetrieval(self.L1, self.L2, self.L3, self.L4)
        
        # Consolidation settings
        self.consolidation_enabled = self.config.get("memory.consolidation.enabled", True)
        self.consolidation_interval = self.config.get("memory.consolidation.interval_minutes", 30)
        
        # Statistics
        self.stats = {
            "stored": 0,
            "retrieved": 0,
            "consolidated": 0,
            "last_consolidation": None
        }
        
        # Start background consolidation if enabled
        if self.consolidation_enabled:
            asyncio.create_task(self._consolidation_loop())
        
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
        - source_module: str (optional)
        """
        try:
            # Parse event data
            content = event_data.get("content")
            if not content:
                self.logger.warning("Store request with no content")
                return
            
            memory_type_str = event_data.get("memory_type", "episodic")
            memory_type = MemoryType(memory_type_str)
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
            
            # Store in appropriate tiers based on importance
            memory_id = await self.L1.store(memory)  # Always store in L1
            await self.L2.store(memory)               # Always store in L2
            
            tiers_stored = ["L1", "L2"]
            
            if importance >= 0.5:
                await self.L3.store(memory)           # Store in L3 if important
                tiers_stored.append("L3")
            
            if importance >= 0.8:
                await self.L4.store(memory)           # Store in L4 if critical
                tiers_stored.append("L4")
            
            self.stats["stored"] += 1
            
        
        

            # Publish confirmation
            await self.publish("memory.stored", {
                "memory_id": memory_id,
                "tiers": tiers_stored,
                "timestamp": memory.timestamp
            })
            
            self.logger.debug(f"Stored memory in {len(tiers_stored)} tiers: {memory_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store memory: {e}")
            await self.publish("memory.error", {
                "operation": "store",
                "error": str(e)
            })
    
    @on_event("memory.retrieve")
    async def handle_retrieve(self, event_data: Dict) -> None:
        """
        Retrieve memories by query
        
        Event data should contain:
        - query: str
        - max_results: int (optional, default: 10)
        - strategy: str (optional, default: "comprehensive")
        """
        try:
            query = event_data.get("query")
            if not query:
                self.logger.warning("Retrieve request with no query")
                return
            
            max_results = event_data.get("max_results", 10)
            strategy_str = event_data.get("strategy", "comprehensive")
            
            # Build retrieval config (RetrievalConfig here doesn't accept a
            # strategy parameter; the retrieval API expects the strategy as
            # a separate argument when using the memory package's API.)
            config = RetrievalConfig(
                max_results=max_results
            )

            # Retrieve memories using the requested strategy string
            memories = await self.retrieval.retrieve(query, strategy=strategy_str, config=config)
            
            self.stats["retrieved"] += len(memories)
            
            # Publish results
            await self.publish("memory.retrieved", {
                "query": query,
                "count": len(memories),
                "memories": [m.to_dict() for m in memories]
            })
            
            self.logger.debug(f"Retrieved {len(memories)} memories for query: {query}")
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve memories: {e}")
            await self.publish("memory.error", {
                "operation": "retrieve",
                "error": str(e)
            })
    
    @on_event("memory.get_context")
    async def handle_get_context(self, event_data: Dict) -> None:
        """
        Get recent context for reasoning engine
        
        Event data should contain:
        - minutes: int (default: 10)
        """
        try:
            minutes = event_data.get("minutes", 10)
            
            # Get recent context from L1
            context = await self.retrieval.get_recent_context(minutes)
            
            # Publish context
            await self.publish("memory.context", {
                "minutes": minutes,
                "count": len(context),
                "memories": [m.to_dict() for m in context]
            })
            
            self.logger.debug(f"Provided {len(context)} memories as context")
            
        except Exception as e:
            self.logger.error(f"Failed to get context: {e}")
            await self.publish("memory.error", {
                "operation": "get_context",
                "error": str(e)
            })
    
    @tool("get_memory_stats")
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory system statistics"""
        try:
            # Get stats from retrieval system (includes all tiers)
            system_stats = await self.retrieval.get_stats()
            
            # Add module-level stats
            system_stats["module_stats"] = self.stats
            
            return system_stats
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    async def _consolidation_loop(self) -> None:
        """
        Background memory consolidation loop
        
        Periodically moves memories between tiers based on importance
        and access patterns
        """
        interval_seconds = self.consolidation_interval * 60
        
        self.logger.info(f"Starting consolidation loop (interval: {self.consolidation_interval} min)")
        
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                
                self.logger.info("Starting memory consolidation...")
                
                consolidated = await self._run_consolidation()
                
                self.stats["consolidated"] += consolidated
                self.stats["last_consolidation"] = time.time()
                
                # Publish consolidation results
                await self.publish("memory.consolidated", {
                    "count": consolidated,
                    "timestamp": time.time()
                })
                
                self.logger.info(f"Consolidation complete: {consolidated} memories processed")
                
            except Exception as e:
                self.logger.error(f"Consolidation error: {e}")
    
    async def _run_consolidation(self) -> int:
        """
        Run the actual consolidation process
        
        Returns:
            Number of memories consolidated
        """
        total_consolidated = 0
        threshold = self.config.get("memory.consolidation.importance_threshold", 0.5)
        
        # L1 → L2: Promote important working memories
        l1_memories = await self.L1.get_all_for_consolidation()
        for memory in l1_memories:
            if self.L2.should_store_in_tier(memory):
                await self.L2.store(memory)
                total_consolidated += 1
        
        # L2 → L3: Promote to long-term semantic memory
        l2_memories = await self.L2.retrieve("*", limit=1000)
        for memory in l2_memories:
            if self.L3.should_store_in_tier(memory):
                await self.L3.store(memory)
                total_consolidated += 1
        
        # L3 → L4: Promote critical facts to persistent storage
        l3_memories = await self.L3.get_important_memories(min_importance=0.8)
        for memory in l3_memories:
            if self.L4.should_store_in_tier(memory):
                await self.L4.store(memory)
                total_consolidated += 1
        
        return total_consolidated
    
    async def shutdown(self) -> None:
        """Graceful shutdown of memory system"""
        self.logger.info("Shutting down memory system")
        
        # Health check all tiers before shutdown
        health = {
            "L1": await self.L1.health_check(),
            "L2": await self.L2.health_check(),
            "L3": await self.L3.health_check(),
            "L4": await self.L4.health_check()
        }
        
        self.logger.info(f"Memory system health at shutdown: {health}")
        self.logger.info("Memory system shutdown complete")