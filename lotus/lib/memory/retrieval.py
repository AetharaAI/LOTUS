"""
LOTUS Memory System - Intelligent Cross-Tier Retrieval

This is the "memory retrieval intelligence" of LOTUS - the system that
searches across all 4 memory tiers and intelligently ranks results.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .base import MemoryItem, MemoryType, MemoryTier # Import MemoryTier for type hinting
from .working_memory import WorkingMemory
from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from .persistent import PersistentMemory


class RetrievalStrategy(Enum):
    """Different retrieval strategies based on query type"""
    RECENT_CONTEXT = "recent_context"      # Last 10 min (L1 only)
    TODAY_HISTORY = "today_history"        # Last 24 hours (L1 + L2)
    SEMANTIC_SEARCH = "semantic_search"    # Meaning-based (L3 focus)
    FACT_LOOKUP = "fact_lookup"            # Permanent facts (L4)
    COMPREHENSIVE = "comprehensive"        # Search all tiers


@dataclass
class RetrievalConfig:
    """Configuration for memory retrieval"""
    strategy: RetrievalStrategy = RetrievalStrategy.COMPREHENSIVE
    max_results: int = 10
    min_relevance: float = 0.3
    
    weight_l1: float = 0.4
    weight_l2: float = 0.3
    weight_l3: float = 0.2
    weight_l4: float = 0.1
    
    importance_weight: float = 0.4
    recency_weight: float = 0.3
    access_weight: float = 0.2
    semantic_weight: float = 0.1


class MemoryRetrieval:
    """
    Intelligent cross-tier memory retrieval system
    """
    
    def __init__(self, L1: WorkingMemory, L2: ShortTermMemory, 
                 L3: LongTermMemory, L4: PersistentMemory):
        self.L1 = L1
        self.L2 = L2
        self.L3 = L3
        self.L4 = L4
        # A simple logger for MemoryRetrieval
        import logging
        self.logger = logging.getLogger(f"lotus.memory.retrieval")
        self.logger.debug("MemoryRetrieval initialized.")
    
    async def retrieve(self, query: str, config: Optional[RetrievalConfig] = None) -> List[MemoryItem]:
        """Retrieve memories across all tiers with intelligent ranking"""
        self.logger.debug(f"Starting comprehensive retrieve for query: {query[:50]}...")
        if config is None:
            config = RetrievalConfig()
        
        tiers_to_search = self._select_tiers(config.strategy)
        
        search_tasks = []
        if 'L1' in tiers_to_search: search_tasks.append(self._search_L1(query, config))
        if 'L2' in tiers_to_search: search_tasks.append(self._search_L2(query, config))
        if 'L3' in tiers_to_search: search_tasks.append(self._search_L3(query, config))
        if 'L4' in tiers_to_search: search_tasks.append(self._search_L4(query, config))
        
        tier_results = await asyncio.gather(*search_tasks, return_exceptions=True) # Gather results, handle exceptions
        
        all_memories = []
        for res in tier_results:
            if isinstance(res, Exception):
                self.logger.error(f"Error during tier search: {res}", exc_info=True)
            else:
                all_memories.extend(res)
        
        unique_memories = self._deduplicate(all_memories)
        
        ranked_memories = self._rank_memories(unique_memories, query, config)
        
        filtered_memories = [
            m for m in ranked_memories 
            if m.metadata.get('composite_score', 0) >= config.min_relevance
        ]
        self.logger.debug(f"Retrieved {len(filtered_memories)} ranked memories for query: {query[:50]}...")
        return filtered_memories[:config.max_results]
    
    async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]:
        """
        Retrieves memories directly by their IDs from the most appropriate tier.
        This is a facade for direct ID lookup in individual tiers.
        """
        self.logger.debug(f"Retrieving {len(memory_ids)} memories by ID via MemoryRetrieval.")
        if not memory_ids:
            return []
        
        all_memories: List[MemoryItem] = []
        
        # Prioritize L1, then L2, then L3, then L4
        # This prevents unnecessary lookups in lower tiers if found in higher.
        
        # First, try to get all from L1 (fastest)
        l1_found = await self.L1.get_memories_by_id(memory_ids)
        all_memories.extend(l1_found)
        
        remaining_ids = list(set(memory_ids) - {m.id for m in l1_found})
        if not remaining_ids: return all_memories
        
        # Then, try L2 for remaining
        l2_found = await self.L2.get_memories_by_id(remaining_ids)
        all_memories.extend(l2_found)
        
        remaining_ids = list(set(remaining_ids) - {m.id for m in l2_found})
        if not remaining_ids: return all_memories
        
        # Then, try L3 for remaining
        l3_found = await self.L3.get_memories_by_id(remaining_ids)
        all_memories.extend(l3_found)

        remaining_ids = list(set(remaining_ids) - {m.id for m in l3_found})
        if not remaining_ids: return all_memories
        
        # Finally, try L4 for remaining
        l4_found = await self.L4.get_memories_by_id(remaining_ids)
        all_memories.extend(l4_found)

        # Deduplicate and return
        unique_memories = {m.id: m for m in all_memories}.values()
        self.logger.debug(f"Retrieved {len(unique_memories)} unique memories by ID.")
        return list(unique_memories)

    async def get_recent_context(self, minutes: int = 10) -> List[MemoryItem]:
        """Get recent conversation context for reasoning engine"""
        self.logger.debug(f"Getting recent context for last {minutes} minutes.")
        memories = await self.L1.get_recent_context(minutes) # L1 has specialized method
        memories.sort(key=lambda m: m.timestamp)
        self.logger.debug(f"Retrieved {len(memories)} recent context items.")
        return memories
    
    async def find_related(self, memory: MemoryItem, limit: int = 5) -> List[MemoryItem]:
        """Find memories related to a given memory"""
        self.logger.debug(f"Finding memories related to memory ID: {memory.id[:15]}...")
        related = await self.L3.find_similar(memory.id, limit=limit)
        
        config = RetrievalConfig(
            strategy=RetrievalStrategy.COMPREHENSIVE,
            max_results=limit
        )
        
        if memory.source_module:
            module_memories = await self.retrieve(
                memory.content,
                config=config
            )
            
            all_related = related + module_memories
            unique_related = self._deduplicate(all_related)
            
            return unique_related[:limit]
        
        return related
    
    async def get_conversation_summary(self, hours: int = 24) -> List[MemoryItem]:
        """Get a summary of the last N hours of conversation"""
        self.logger.debug(f"Getting conversation summary for last {hours} hours.")
        conversation = await self.L2.get_conversation_flow(hours)
        important = [m for m in conversation if m.importance > 0.6]
        self.logger.debug(f"Retrieved {len(important)} important conversation items.")
        return important
    
    async def search_by_type(self, memory_type: MemoryType, 
                            limit: int = 50) -> List[MemoryItem]:
        """Search for memories of a specific type across all tiers"""
        self.logger.debug(f"Searching by memory type: {memory_type.value}, limit: {limit}.")
        config = RetrievalConfig(
            strategy=RetrievalStrategy.COMPREHENSIVE,
            max_results=limit
        )
        
        tasks = [
            self.L1.retrieve("*", limit=limit, filters={'memory_type': memory_type.value}),
            self.L2.retrieve("*", limit=limit, filters={'memory_type': memory_type.value}),
            self.L3.get_by_type(memory_type, limit=limit),
            self.L4.retrieve("*", limit=limit, filters={'memory_type': memory_type.value})
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_memories = []
        for res in results:
            if isinstance(res, Exception):
                self.logger.error(f"Error during type-specific tier search: {res}", exc_info=True)
            else:
                all_memories.extend(res)
        
        unique = self._deduplicate(all_memories)
        unique.sort(key=lambda m: m.importance, reverse=True)
        self.logger.debug(f"Retrieved {len(unique)} memories of type {memory_type.value}.")
        return unique[:limit]
    
    # === Private Methods ===
    
    def _select_tiers(self, strategy: RetrievalStrategy) -> List[str]:
        """Determine which tiers to search based on strategy"""
        if strategy == RetrievalStrategy.RECENT_CONTEXT: return ['L1']
        elif strategy == RetrievalStrategy.TODAY_HISTORY: return ['L1', 'L2']
        elif strategy == RetrievalStrategy.SEMANTIC_SEARCH: return ['L3', 'L4']
        elif strategy == RetrievalStrategy.FACT_LOOKUP: return ['L4']
        else: return ['L1', 'L2', 'L3', 'L4']
    
    async def _search_L1(self, query: str, config: RetrievalConfig) -> List[MemoryItem]:
        """Search working memory"""
        memories = await self.L1.retrieve(query, limit=config.max_results * 2)
        for m in memories: m.metadata['search_tier'] = 'L1'; m.metadata['tier_weight'] = config.weight_l1
        return memories
    
    async def _search_L2(self, query: str, config: RetrievalConfig) -> List[MemoryItem]:
        """Search short-term memory"""
        memories = await self.L2.retrieve(query, limit=config.max_results * 2)
        for m in memories: m.metadata['search_tier'] = 'L2'; m.metadata['tier_weight'] = config.weight_l2
        return memories
    
    async def _search_L3(self, query: str, config: RetrievalConfig) -> List[MemoryItem]:
        """Search long-term memory"""
        memories = await self.L3.retrieve(query, limit=config.max_results * 2)
        for m in memories: m.metadata['search_tier'] = 'L3'; m.metadata['tier_weight'] = config.weight_l3
        return memories
    
    async def _search_L4(self, query: str, config: RetrievalConfig) -> List[MemoryItem]:
        """Search persistent memory"""
        memories = await self.L4.retrieve(query, limit=config.max_results * 2)
        for m in memories: m.metadata['search_tier'] = 'L4'; m.metadata['tier_weight'] = config.weight_l4
        return memories
    
    def _deduplicate(self, memories: List[MemoryItem]) -> List[MemoryItem]:
        """Remove duplicate memories (same ID from different tiers)"""
        seen_ids = set()
        unique = []
        
        tier_priority = {'L1': 1, 'L2': 2, 'L3': 3, 'L4': 4}
        sorted_memories = sorted(
            memories,
            key=lambda m: tier_priority.get(m.metadata.get('search_tier', 'L4'), 4)
        )
        
        for memory in sorted_memories:
            if memory.id not in seen_ids:
                seen_ids.add(memory.id)
                unique.append(memory)
        
        return unique
    
    def _rank_memories(self, memories: List[MemoryItem], query: str,
                      config: RetrievalConfig) -> List[MemoryItem]:
        """Rank memories by composite relevance score"""
        current_time = time.time()
        
        for memory in memories:
            importance_score = memory.importance
            age_hours = (current_time - memory.timestamp) / 3600
            recency_score = 1.0 / (1.0 + age_hours / 24.0)
            access_score = min(memory.access_count / 10.0, 1.0)
            tier_weight = memory.metadata.get('tier_weight', 0.25)
            semantic_score = memory.metadata.get('semantic_distance', 0.5)
            semantic_score = 1.0 - min(semantic_score, 1.0)
            
            composite = (
                importance_score * config.importance_weight +
                recency_score * config.recency_weight +
                access_score * config.access_weight +
                semantic_score * config.semantic_weight
            )
            
            composite *= (1.0 + tier_weight)
            
            memory.metadata['composite_score'] = composite
            memory.metadata['score_breakdown'] = {
                'importance': importance_score,
                'recency': recency_score,
                'access': access_score,
                'semantic': semantic_score,
                'tier_weight': tier_weight
            }
        
        memories.sort(key=lambda m: m.metadata.get('composite_score', 0), reverse=True)
        
        return memories
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics for entire memory system"""
        stats_list = await asyncio.gather(
            self.L1.get_stats(),
            self.L2.get_stats(),
            self.L3.get_stats(),
            self.L4.get_stats(),
            return_exceptions=True # Allow individual tier stats to fail
        )
        
        combined_stats = {
            'total_memories': 0,
            'L1': {'error': 'Failed to get stats'} if isinstance(stats_list[0], Exception) else stats_list[0],
            'L2': {'error': 'Failed to get stats'} if isinstance(stats_list[1], Exception) else stats_list[1],
            'L3': {'error': 'Failed to get stats'} if isinstance(stats_list[2], Exception) else stats_list[2],
            'L4': {'error': 'Failed to get stats'} if isinstance(stats_list[3], Exception) else stats_list[3],
            'health': {
                'L1': await self.L1.health_check(),
                'L2': await self.L2.health_check(),
                'L3': await self.L3.health_check(),
                'L4': await self.L4.health_check()
            }
        }
        
        # Calculate total memories, ignoring tiers that failed to report stats
        for tier_key in ['L1', 'L2', 'L3', 'L4']:
            tier_stats = combined_stats.get(tier_key)
            if isinstance(tier_stats, dict) and 'count' in tier_stats and not tier_stats.get('error'):
                combined_stats['total_memories'] += tier_stats['count']

        return combined_stats