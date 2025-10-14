"""
Memory Module - 4-Tier Memory System

This module coordinates LOTUS's entire memory architecture:
- L1 (Working): Last 10 minutes, instant Redis access
- L2 (Short-term): Last 24 hours, Redis Streams
- L3 (Long-term): Semantic memories, ChromaDB vectors
- L4 (Persistent): Structured facts, PostgreSQL

The memory system automatically:
- Routes storage to appropriate tier
- Consolidates memories over time
- Retrieves across all tiers
- Ranks by relevance and recency
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import hashlib

from lib.module import BaseModule
from lib.decorators import on_event, tool, periodic
from lib.memory import (
    WorkingMemory, ShortTermMemory, LongTermMemory, 
    PersistentMemory, MemoryItem
)


@dataclass
class MemoryQuery:
    """Query for memory retrieval"""
    query: str
    tier: Optional[str] = None  # Specific tier or search all
    limit: int = 10
    min_relevance: float = 0.5
    time_window: Optional[timedelta] = None


class MemoryModule(BaseModule):
    """
    Memory System Coordinator
    
    Manages all 4 tiers of memory and handles:
    - Intelligent storage routing
    - Cross-tier retrieval
    - Memory consolidation
    - Relevance ranking
    """
    
    async def initialize(self) -> None:
        """Initialize all memory tiers"""
        self.logger.info("Initializing 4-tier memory system")
        
        # Initialize memory tiers
        self.L1 = WorkingMemory(
            self.config, 
            self.message_bus,
            ttl=self.config.get("memory.working_memory.ttl_seconds", 600)
        )
        
        self.L2 = ShortTermMemory(
            self.config,
            self.message_bus,
            ttl_hours=self.config.get("memory.short_term.ttl_hours", 24)
        )
        
        self.L3 = LongTermMemory(
            self.config,
            self.message_bus,
            collection_name=self.config.get("memory.long_term.collection_name", "lotus_memories")
        )
        
        self.L4 = PersistentMemory(
            self.config,
            self.message_bus,
            table_name=self.config.get("memory.persistent.table_name", "knowledge")
        )
        
        # Consolidation tracking
        self.consolidation_enabled = self.config.get("memory.consolidation.enabled", True)
        self.consolidation_threshold = self.config.get("memory.consolidation.importance_threshold", 0.5)
        
        # Statistics
        self.stats = {
            "stored": 0,
            "retrieved": 0,
            "consolidated": 0,
            "last_consolidation": None
        }
        
        self.logger.info("Memory system initialized successfully")
        
    @on_event("memory.store")
    async def handle_store(self, event: Dict[str, Any]) -> None:
        """
        Store a memory in the appropriate tier
        
        Event data:
        {
            "content": "text or data to store",
            "metadata": {"type": "conversation", "importance": 0.8},
            "tier": "auto"  # or specific: L1, L2, L3, L4
        }
        """
        content = event.get("content")
        metadata = event.get("metadata", {})
        requested_tier = event.get("tier", "auto")
        
        if not content:
            self.logger.warning("Store request with no content")
            return
        
        # Determine tier
        tier = self._determine_tier(content, metadata, requested_tier)
        
        # Create memory item
        memory = MemoryItem(
            id=self._generate_id(content),
            content=content,
            metadata=metadata,
            timestamp=datetime.now(),
            importance=metadata.get("importance", 0.5),
            access_count=0
        )
        
        # Store in appropriate tier
        try:
            if tier == "L1":
                await self.L1.store(memory)
            elif tier == "L2":
                await self.L2.store(memory)
            elif tier == "L3":
                await self.L3.store(memory)
            elif tier == "L4":
                await self.L4.store(memory)
            
            self.stats["stored"] += 1
            
            # Publish success event
            await self.publish("memory.stored", {
                "memory_id": memory.id,
                "tier": tier,
                "timestamp": memory.timestamp.isoformat()
            })
            
            self.logger.debug(f"Stored memory in {tier}: {memory.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store memory: {e}")
            await self.publish("memory.error", {
                "error": str(e),
                "operation": "store"
            })
    
    @on_event("memory.retrieve")
    async def handle_retrieve(self, event: Dict[str, Any]) -> None:
        """
        Retrieve memories by query
        
        Event data:
        {
            "query": "search query",
            "tier": "all",  # or specific: L1, L2, L3, L4
            "limit": 10,
            "min_relevance": 0.5
        }
        """
        query = MemoryQuery(
            query=event.get("query", ""),
            tier=event.get("tier"),
            limit=event.get("limit", 10),
            min_relevance=event.get("min_relevance", 0.5)
        )
        
        # Retrieve from specified tier(s)
        results = await self._retrieve_memories(query)
        
        # Rank results
        ranked_results = self._rank_results(results, query.query)
        
        # Limit results
        final_results = ranked_results[:query.limit]
        
        self.stats["retrieved"] += len(final_results)
        
        # Publish results
        await self.publish("memory.retrieved", {
            "query": query.query,
            "count": len(final_results),
            "results": [
                {
                    "id": m.id,
                    "content": m.content,
                    "metadata": m.metadata,
                    "relevance": m.relevance_score,
                    "tier": m.tier
                }
                for m in final_results
            ]
        })
        
        self.logger.debug(f"Retrieved {len(final_results)} memories for query: {query.query}")
    
    @on_event("memory.search")
    async def handle_search(self, event: Dict[str, Any]) -> None:
        """
        Semantic search across all tiers
        
        Event data:
        {
            "query": "semantic search query",
            "limit": 10
        }
        """
        query = event.get("query", "")
        limit = event.get("limit", 10)
        
        # Semantic search in L3 (vector store)
        results = await self.L3.semantic_search(query, limit=limit)
        
        # Also check L1 and L2 for very recent matches
        recent_l1 = await self.L1.search(query, limit=5)
        recent_l2 = await self.L2.search(query, limit=5)
        
        # Combine and rank
        all_results = results + recent_l1 + recent_l2
        ranked = self._rank_results(all_results, query)
        
        await self.publish("memory.retrieved", {
            "query": query,
            "count": len(ranked[:limit]),
            "results": [
                {
                    "id": m.id,
                    "content": m.content,
                    "relevance": m.relevance_score,
                    "tier": m.tier
                }
                for m in ranked[:limit]
            ]
        })
    
    @periodic(interval=1800)  # Every 30 minutes
    async def consolidate_memories(self) -> None:
        """
        Periodic memory consolidation
        
        Moves important memories between tiers:
        - L1 â†' L2: Frequently accessed working memories
        - L2 â†' L3: Important short-term to long-term
        - L2 â†' L4: Facts and structured knowledge
        """
        if not self.consolidation_enabled:
            return
        
        self.logger.info("Starting memory consolidation")
        consolidated_count = 0
        
        try:
            # L1 â†' L2: Move frequently accessed items
            l1_items = await self.L1.get_frequent_items(threshold=3)
            for item in l1_items:
                await self.L2.store(item)
                consolidated_count += 1
            
            # L2 â†' L3: Move important items to long-term
            l2_items = await self.L2.get_important_items(
                threshold=self.consolidation_threshold
            )
            for item in l2_items:
                await self.L3.store(item)
                consolidated_count += 1
            
            # L2 â†' L4: Extract facts and store persistently
            facts = await self._extract_facts_from_l2()
            for fact in facts:
                await self.L4.store(fact)
                consolidated_count += 1
            
            self.stats["consolidated"] += consolidated_count
            self.stats["last_consolidation"] = datetime.now()
            
            await self.publish("memory.consolidated", {
                "count": consolidated_count,
                "timestamp": datetime.now().isoformat()
            })
            
            self.logger.info(f"Consolidated {consolidated_count} memories")
            
        except Exception as e:
            self.logger.error(f"Consolidation failed: {e}")
    
    @tool("memory_stats")
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "stored_total": self.stats["stored"],
            "retrieved_total": self.stats["retrieved"],
            "consolidated_total": self.stats["consolidated"],
            "last_consolidation": (
                self.stats["last_consolidation"].isoformat()
                if self.stats["last_consolidation"] else None
            ),
            "tier_counts": {
                "L1": await self.L1.count(),
                "L2": await self.L2.count(),
                "L3": await self.L3.count(),
                "L4": await self.L4.count()
            }
        }
    
    async def shutdown(self) -> None:
        """Shutdown memory systems gracefully"""
        self.logger.info("Shutting down memory system")
        
        # Flush all tiers
        await self.L1.flush()
        await self.L2.flush()
        await self.L3.flush()
        await self.L4.flush()
        
        self.logger.info("Memory system shutdown complete")
    
    # Helper methods
    
    def _determine_tier(
        self, 
        content: str, 
        metadata: Dict[str, Any],
        requested: str
    ) -> str:
        """Determine which tier to store in"""
        if requested in ["L1", "L2", "L3", "L4"]:
            return requested
        
        # Auto-determine based on content and metadata
        importance = metadata.get("importance", 0.5)
        content_type = metadata.get("type", "unknown")
        
        # Facts go to L4
        if content_type in ["fact", "knowledge", "structured"]:
            return "L4"
        
        # High importance goes to L3
        if importance > 0.7:
            return "L3"
        
        # Recent conversation goes to L2
        if content_type in ["conversation", "interaction"]:
            return "L2"
        
        # Everything else starts in L1
        return "L1"
    
    async def _retrieve_memories(
        self, 
        query: MemoryQuery
    ) -> List[MemoryItem]:
        """Retrieve memories from specified tier(s)"""
        results = []
        
        if query.tier == "all" or query.tier is None:
            # Search all tiers
            results.extend(await self.L1.search(query.query))
            results.extend(await self.L2.search(query.query))
            results.extend(await self.L3.search(query.query))
            results.extend(await self.L4.search(query.query))
        elif query.tier == "L1":
            results = await self.L1.search(query.query)
        elif query.tier == "L2":
            results = await self.L2.search(query.query)
        elif query.tier == "L3":
            results = await self.L3.search(query.query)
        elif query.tier == "L4":
            results = await self.L4.search(query.query)
        
        return results
    
    def _rank_results(
        self, 
        results: List[MemoryItem],
        query: str
    ) -> List[MemoryItem]:
        """Rank results by relevance and recency"""
        now = datetime.now()
        
        for item in results:
            # Calculate recency score (0-1)
            age_seconds = (now - item.timestamp).total_seconds()
            recency_score = 1.0 / (1.0 + age_seconds / 3600)  # Decay over hours
            
            # Calculate access score
            access_score = min(item.access_count / 10.0, 1.0)
            
            # Combined relevance score
            item.relevance_score = (
                0.4 * item.importance +
                0.3 * recency_score +
                0.2 * access_score +
                0.1  # Base score
            )
        
        # Sort by relevance
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)
    
    async def _extract_facts_from_l2(self) -> List[MemoryItem]:
        """Extract factual information from short-term memory"""
        # This would use NLP to extract facts
        # For now, return important items that look like facts
        items = await self.L2.get_important_items(threshold=0.8)
        
        facts = []
        for item in items:
            # Simple heuristic: short, declarative statements
            if len(item.content) < 200 and "." in item.content:
                facts.append(item)
        
        return facts
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory"""
        return hashlib.sha256(
            f"{content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]