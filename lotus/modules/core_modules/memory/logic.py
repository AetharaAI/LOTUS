"""
LOTUS Memory Module - Coordinator for 4-Tier Memory System

This module manages the complete memory architecture and exposes
it via the event bus for other modules to use.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional
import logging

from lotus.lib.module import BaseModule, Event
from lotus.lib.decorators import on_event, tool, periodic
from lotus.lib.memory import (
    MemoryItem, MemoryType,
    WorkingMemory, ShortTermMemory, LongTermMemory, PersistentMemory,
    MemoryRetrieval, RetrievalConfig, RetrievalStrategy
)
# Attempt to import SentenceTransformer from a known path,
# potentially from the original lib/memory.py or if it's placed in lib/
# Fallback to a dummy if not available or if the full library isn't installed.
try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    _SENTENCE_TRANSFORMER_AVAILABLE = False
    class SentenceTransformer: # Dummy class
        def __init__(self, model_name: str):
            pass
        def encode(self, text: str):
            return [0.0]

class MemoryModule(BaseModule):
    """
    Memory System Coordinator
    
    Manages all 4 tiers and provides memory services to other modules
    """
    
    def __init__(self, name: str, metadata: Dict, message_bus: Any, config: Any, logger: logging.Logger):
        super().__init__(name, metadata, message_bus, config, logger)
        self.logger = logging.getLogger(f"lotus.module.{self.name}") # Ensure dedicated logger

        self.L1: Optional[WorkingMemory] = None
        self.L2: Optional[ShortTermMemory] = None
        self.L3: Any = None # Can be LongTermMemory or NoOpLongTermMemory
        self.L4: Any = None # Can be PersistentMemory or NoOpPersistentMemory
        self.retrieval: Optional[MemoryRetrieval] = None

        self.consolidation_task: Optional[asyncio.Task] = None
        
    @on_event("perception.user_input")
    async def on_user_input(self, event: Event) -> None:
        """Handle user input by storing it in memory"""
        if not event.data:
            return
            
        await self.store_memory({
            "type": "user_input",
            "content": event.data,
            "timestamp": time.time()
        })
        
    async def initialize(self) -> None:
        """Initialize all memory tiers"""
        self.logger.info("Initializing 4-tier memory system")
        
        # Get connections from nucleus (these are populated in Nucleus._init_infrastructure)
        redis_client = self.config.get("services.redis")
        chroma_client = self.config.get("services.chroma")
        postgres_conn = self.config.get("services.db_engine")

        if not redis_client:
            self.logger.critical("Redis client not found in config. Memory system cannot initialize L1/L2.")
            raise RuntimeError("Redis client not available.")
        if not postgres_conn:
            self.logger.critical("PostgreSQL engine not found in config. Memory system cannot initialize L4.")
            # Don't raise immediately, L4 will create a NoOp
        
        # Initialize L1: Working Memory (Redis)
        try:
            self.L1 = WorkingMemory(
                redis_client,
                ttl_seconds=self.config.get("memory.working_memory.ttl_seconds", 600),
                max_items=self.config.get("memory.working_memory.max_items", 100)
            )
            self.logger.debug("L1 WorkingMemory initialized.")
        except Exception as e:
            self.logger.critical(f"Failed to initialize L1 WorkingMemory: {e}", exc_info=True)
            raise # Critical failure, cannot proceed without L1
        
        # Initialize L2: Short-term Memory (Redis Streams)
        try:
            self.L2 = ShortTermMemory(
                redis_client,
                ttl_hours=self.config.get("memory.short_term.ttl_hours", 24),
                max_items=self.config.get("memory.short_term.max_items", 1000)
            )
            self.logger.debug("L2 ShortTermMemory initialized.")
        except Exception as e:
            self.logger.critical(f"Failed to initialize L2 ShortTermMemory: {e}", exc_info=True)
            raise # Critical failure, cannot proceed without L2
        
        # Initialize L3: Long-term Memory (ChromaDB)
        embedding_model_name = self.config.get("memory.long_term.embedding_model", "all-MiniLM-L6-v2")
        if not _SENTENCE_TRANSFORMER_AVAILABLE:
            self.logger.warning("SentenceTransformer library not available. L3 LongTermMemory will be in no-op mode if Chroma is enabled.")
            embedding_model_name = None
        elif not embedding_model_name:
             self.logger.warning("No embedding model name provided in config for L3. L3 functionality may be limited if Chroma is enabled.")
             embedding_model_name = None
        else:
            self.logger.debug(f"Attempting to prepare embedding model name for L3: {embedding_model_name}")

        if chroma_client is None:
            self.logger.info("ChromaDB client is None. L3 LongTermMemory will be a No-Op shim.")
            class NoOpLongTermMemory:
                def __init__(self, *args, **kwargs):
                    self.collection = None
                    self.tier_name = "long_term_memory_noop"
                    self.tier_level = 3
                    self.logger = logging.getLogger(f"lotus.memory.{self.tier_name}")
                    self.is_healthy = True # Assume healthy as no-op

                async def initialize(self): return
                async def store(self, memory: MemoryItem) -> Optional[str]:
                    self.logger.debug(f"No-op L3 store called for {memory.id[:15]}...")
                    return memory.id # Simulate success
                async def store_semantic_summary(self, summary: str, original_memory_id: Optional[str], metadata: Dict, source_module: str) -> Optional[str]:
                    self.logger.debug(f"No-op L3 store_semantic_summary called for {summary[:50]}...")
                    return f"noop_summary_id:{int(time.time())}"
                async def retrieve(self, query: str, limit: int = 10, filters: Optional[Dict] = None):
                    self.logger.debug(f"No-op L3 retrieve called for query: {query[:50]}...")
                    return []
                async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]:
                    self.logger.debug(f"No-op L3 get_memories_by_id called for {len(memory_ids)} IDs.")
                    return []
                async def find_similar(self, memory_id: str, limit: int = 5): return []
                async def get_important_memories(self, min_importance: float = 0.7, limit: int = 50): return []
                async def get_by_type(self, memory_type: MemoryType, limit: int = 100): return []
                async def delete(self, memory_id: str) -> bool: return False
                async def get_stats(self) -> Dict[str, Any]: return {"tier": "L3_long_term_noop", "count": 0, "healthy": True}
                async def health_check(self) -> bool: return True
                def should_store_in_tier(self, memory: MemoryItem): return memory.importance >= 0.5 # Default heuristic
            self.L3 = NoOpLongTermMemory()
        else:
            try:
                self.L3 = LongTermMemory(
                    chroma_client,
                    collection_name=self.config.get("memory.long_term.collection_name", "lotus_memories"),
                    embedding_model=embedding_model_name
                )
                self.logger.debug("L3 LongTermMemory (ChromaDB) initialized.")
            except Exception as e:
                self.logger.critical(f"Failed to initialize L3 LongTermMemory (ChromaDB): {e}. L3 will be a No-Op shim.", exc_info=True)
                class NoOpLongTermMemory: # Fallback
                    def __init__(self, *args, **kwargs):
                        self.collection = None
                        self.tier_name = "long_term_memory_noop"
                        self.tier_level = 3
                        self.logger = logging.getLogger(f"lotus.memory.{self.tier_name}")
                        self.is_healthy = False # Mark as unhealthy if actual init failed
                    async def initialize(self): return
                    async def store(self, memory: MemoryItem) -> Optional[str]: return memory.id
                    async def store_semantic_summary(self, summary: str, original_memory_id: Optional[str], metadata: Dict, source_module: str) -> Optional[str]: return f"noop_summary_id:{int(time.time())}"
                    async def retrieve(self, query: str, limit: int = 10, filters: Optional[Dict] = None): return []
                    async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]: return []
                    async def find_similar(self, memory_id: str, limit: int = 5): return []
                    async def get_important_memories(self, min_importance: float = 0.7, limit: int = 50): return []
                    async def get_by_type(self, memory_type: MemoryType, limit: int = 100): return []
                    async def delete(self, memory_id: str) -> bool: return False
                    async def get_stats(self) -> Dict[str, Any]: return {"tier": "L3_long_term_noop_failed_init", "count": 0, "healthy": False}
                    async def health_check(self) -> bool: return False
                    def should_store_in_tier(self, memory: MemoryItem): return False
                self.L3 = NoOpLongTermMemory()

        # Initialize L4: Persistent Memory (PostgreSQL)
        try:
            self.L4 = PersistentMemory(
                postgres_conn,
                table_name=self.config.get("memory.persistent.table_name", "lotus_knowledge")
            )
            self.logger.debug("Initializing L4 PersistentMemory schema.")
            await self.L4.initialize()
            self.logger.debug("L4 PersistentMemory schema initialized.")
        except Exception as e:
            self.logger.critical(f"Failed to initialize L4 PersistentMemory: {e}. L4 will be a No-Op shim or non-functional.", exc_info=True)
            class NoOpPersistentMemory: # Fallback if L4 init fails
                def __init__(self, *args, **kwargs):
                    self.conn = None
                    self.table_name = "lotus_memories_noop"
                    self.tier_name = "persistent_memory_noop"
                    self.tier_level = 4
                    self.logger = logging.getLogger(f"lotus.memory.{self.tier_name}")
                    self.is_healthy = False
                async def initialize(self): return
                async def store(self, memory: MemoryItem) -> Optional[str]: return memory.id
                async def retrieve(self, query: str, limit: int = 10, filters: Optional[Dict] = None) -> List[MemoryItem]: return []
                async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]: return []
                async def delete(self, memory_id: str) -> bool: return False
                async def get_stats(self) -> Dict[str, Any]: return {"tier": "L4_persistent_noop_failed_init", "count": 0, "healthy": False}
                async def get_facts(self, limit: int = 100) -> List[MemoryItem]: return []
                async def get_skills(self, limit: int = 100) -> List[MemoryItem]: return []
                async def get_user_profile_data(self) -> Dict[str, Any]: return {}
                async def store_user_preference(self, key: str, value: Any, importance: float = 0.9) -> Optional[str]: return f"user_pref_noop:{key}"
                async def health_check(self) -> bool: return False
                def should_store_in_tier(self, memory: MemoryItem) -> bool: return False
            self.L4 = NoOpPersistentMemory()


        # Initialize retrieval system
        self.retrieval = MemoryRetrieval(self.L1, self.L2, self.L3, self.L4)
        self.logger.debug("MemoryRetrieval system initialized.")
        
        # Start background consolidation if enabled
        if self.config.get("memory.consolidation.enabled", True):
            interval_minutes = self.config.get("memory.consolidation.interval_minutes", 30)
            self.consolidation_task = asyncio.create_task(self._consolidation_loop(interval_minutes))
            self.logger.info(f"Memory consolidation loop started with {interval_minutes} minute interval.")
        
        self.logger.info("Memory system initialized successfully")

    # Add a facade method to get memories by ID for ReasoningEngine
    async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]:
        """Facade for MemoryRetrieval.get_memories_by_id."""
        if not self.retrieval:
            self.logger.warning("MemoryRetrieval not initialized, cannot get memories by ID.")
            return []
        try:
            return await self.retrieval.get_memories_by_id(memory_ids)
        except Exception as e:
            self.logger.exception(f"Error in MemoryModule.get_memories_by_id for IDs: {memory_ids[:3]}...")
            return []

    # Add a facade method for storing raw data
    async def store_raw_data(self, content: str, memory_type: str, importance: float, metadata: Dict, source_module: str) -> Optional[str]:
        """Facade for storing raw perception data, typically into L2."""
        if not self.L2:
            self.logger.warning("L2 ShortTermMemory not initialized, cannot store raw data.")
            return None
        try:
            return await self.L2.store_raw_data(content, memory_type, importance, metadata, source_module)
        except Exception as e:
            self.logger.exception(f"Error in MemoryModule.store_raw_data for content: {content[:50]}...")
            return None
    
    # Add a facade method for storing semantic summaries directly into L3
    async def store_semantic_summary(self, summary: str, original_memory_id: Optional[str], metadata: Dict, source_module: str) -> Optional[str]:
        """Facade for storing semantic summaries, typically into L3."""
        if not self.L3:
            self.logger.warning("L3 LongTermMemory not initialized, cannot store semantic summary.")
            return None
        try:
            return await self.L3.store_semantic_summary(summary, original_memory_id, metadata, source_module)
        except Exception as e:
            self.logger.exception(f"Error in MemoryModule.store_semantic_summary for summary: {summary[:50]}...")
            return None

    @on_event("memory.store")
    async def handle_store(self, event_data: Dict) -> None:
        """
        Store a memory in appropriate tiers
        """
        try:
            content = event_data.get("content")
            if not content:
                self.logger.warning("Attempted to store memory with no content.")
                return

            memory_type = MemoryType(event_data.get("memory_type", "episodic"))
            importance = event_data.get("importance", 0.5)
            metadata = event_data.get("metadata", {})
            source_module = event_data.get("source_module", self.name)
            
            memory = MemoryItem(
                content=content,
                memory_type=memory_type,
                timestamp=time.time(),
                importance=importance,
                metadata=metadata,
                source_module=source_module
            )
            
            memory_id = await self.L1.store(memory)
            self.logger.debug(f"Stored in L1: {memory_id}")
            
            await self.L2.store(memory)
            self.logger.debug(f"Stored in L2: {memory_id}")
            
            if self.L3 and self.L3.should_store_in_tier(memory):
                await self.L3.store(memory)
                self.logger.debug(f"Stored in L3: {memory_id}")
            
            if self.L4 and self.L4.should_store_in_tier(memory):
                await self.L4.store(memory)
                self.logger.debug(f"Stored in L4: {memory_id}")
            
            await self.publish("memory.stored", {
                "memory_id": memory_id,
                "tiers": self._get_stored_tiers(importance),
                "timestamp": memory.timestamp,
                "content_preview": content[:50],
                "source_module": self.name
            })
            
            self.logger.debug(f"Memory stored: {content[:50]}... (ID: {memory_id})")
        except Exception as e:
            self.logger.exception(f"Error handling memory.store event for content: {event_data.get('content', '')[:50]}...")
            await self.publish("memory.error", {
                "operation": "store",
                "content_preview": event_data.get("content", "")[:50],
                "error": str(e),
                "source_module": self.name
            })
    
    @on_event("memory.retrieve")
    async def handle_retrieve(self, event_data: Dict) -> None:
        """
        Retrieve memories by query
        """
        try:
            query = event_data.get("query")
            if not query:
                self.logger.warning("Retrieve request received with no query.")
                await self.publish("memory.retrieved", {"query": "", "count": 0, "memories": []})
                return

            max_results = event_data.get("max_results", 10)
            strategy = event_data.get("strategy", RetrievalStrategy.COMPREHENSIVE.value)
            
            self.logger.debug(f"Handling memory.retrieve for query: {query[:50]}... with strategy: {strategy}")

            try:
                retrieval_strategy_enum = RetrievalStrategy(strategy)
            except ValueError:
                self.logger.warning(f"Invalid retrieval strategy '{strategy}'. Falling back to COMPREHENSIVE.")
                retrieval_strategy_enum = RetrievalStrategy.COMPREHENSIVE

            config = RetrievalConfig(
                strategy=retrieval_strategy_enum,
                max_results=max_results
            )

            memories = await self.retrieval.retrieve(query, config=config)
            
            await self.publish("memory.retrieved", {
                "query": query,
                "count": len(memories),
                "memories": [m.to_dict() for m in memories],
                "source_module": self.name
            })
            
            self.logger.debug(f"Retrieved {len(memories)} memories for query: {query[:50]}...")
        except Exception as e:
            self.logger.exception(f"Error handling memory.retrieve event for query: {event_data.get('query', '')[:50]}...")
            await self.publish("memory.error", {
                "operation": "retrieve",
                "query_preview": event_data.get("query", "")[:50],
                "error": str(e),
                "source_module": self.name
            })
    
    @on_event("memory.get_context")
    async def handle_get_context(self, event_data: Dict) -> None:
        """
        Get recent context for reasoning engine
        """
        try:
            minutes = event_data.get("minutes", 10)
            self.logger.debug(f"Handling memory.get_context for last {minutes} minutes.")
            
            context = await self.retrieval.get_recent_context(minutes)
            
            await self.publish("memory.context", {
                "minutes": minutes,
                "count": len(context),
                "memories": [m.to_dict() for m in context],
                "source_module": self.name
            })
            self.logger.debug(f"Provided {len(context)} memories as context for {minutes} minutes.")
        except Exception as e:
            self.logger.exception(f"Error handling memory.get_context event for {event_data.get('minutes', 10)} minutes.")
            await self.publish("memory.error", {
                "operation": "get_context",
                "minutes": event_data.get("minutes", 10),
                "error": str(e),
                "source_module": self.name
            })
    
    @tool("get_memory_stats", description="Retrieves comprehensive statistics about the 4-tier memory system.", category="memory", parameters={})
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        try:
            stats = await self.retrieval.get_stats()
            self.logger.debug("Generated memory system statistics.")
            return stats
        except Exception as e:
            self.logger.exception("Error getting memory stats.")
            return {"error": str(e), "message": "Failed to retrieve memory statistics."}
    
    async def _consolidation_loop(self, interval_minutes: int) -> None:
        """Background memory consolidation"""
        interval_seconds = interval_minutes * 60
        self.logger.info(f"Starting memory consolidation loop with interval: {interval_minutes} minutes.")
        
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                
                self.logger.info("Initiating memory consolidation process...")
                
                threshold = self.config.get("memory.consolidation.importance_threshold", 0.5)
                
                l1_promoted = 0
                l2_promoted = 0
                l3_promoted = 0

                self.logger.debug("Consolidating L1 -> L2...")
                l1_memories = await self.L1.get_all_for_consolidation()
                for memory in l1_memories:
                    if self.L2.should_store_in_tier(memory):
                        stored_id = await self.L2.store(memory)
                        if stored_id: l1_promoted += 1
                self.logger.debug(f"L1 -> L2: {l1_promoted} memories promoted.")
                
                self.logger.debug("Consolidating L2 -> L3...")
                l2_memories = await self.L2.retrieve("*", limit=self.L2.max_items, filters={"min_importance": threshold})
                for memory in l2_memories:
                    if self.L3 and self.L3.should_store_in_tier(memory):
                        stored_id = await self.L3.store(memory)
                        if stored_id: l2_promoted += 1
                self.logger.debug(f"L2 -> L3: {l2_promoted} memories promoted.")
                
                self.logger.debug("Consolidating L3 -> L4...")
                if self.L4 and hasattr(self.L4, 'should_store_in_tier') and hasattr(self.L3, 'get_important_memories'):
                    l3_memories = await self.L3.get_important_memories(min_importance=0.8)
                    for memory in l3_memories:
                        try:
                            if self.L4.should_store_in_tier(memory):
                                stored_id = await self.L4.store(memory)
                                if stored_id: l3_promoted += 1
                        except Exception as e:
                            self.logger.warning(f"Error promoting memory to L4 during consolidation: {e}", exc_info=True)
                else:
                    self.logger.debug("L4 or L3 not fully configured for consolidation or missing methods. Skipping L3->L4.")
                self.logger.debug(f"L3 -> L4: {l3_promoted} memories promoted.")
                
                await self.publish("memory.consolidated", {
                    "l1_to_l2": l1_promoted,
                    "l2_to_l3": l2_promoted,
                    "l3_to_l4": l3_promoted,
                    "timestamp": time.time(),
                    "source_module": self.name
                })
                
                self.logger.info(f"Consolidation complete: L1→L2:{l1_promoted}, L2→L3:{l2_promoted}, L3→L4:{l3_promoted}")
                
            except asyncio.CancelledError:
                self.logger.info("Memory consolidation loop cancelled.")
                break
            except Exception as e:
                self.logger.exception(f"Major error in memory consolidation loop: {e}")
                await asyncio.sleep(60)
    
    def _get_stored_tiers(self, importance: float) -> List[str]:
        """Determine which tiers a memory was stored in"""
        tiers = []
        dummy_memory = MemoryItem(content="", memory_type=MemoryType.EPISODIC, timestamp=time.time(), importance=importance)
        if self.L1 and self.L1.should_store_in_tier(dummy_memory): tiers.append("L1")
        if self.L2 and self.L2.should_store_in_tier(dummy_memory): tiers.append("L2")
        if self.L3 and self.L3.should_store_in_tier(dummy_memory): tiers.append("L3")
        if self.L4 and self.L4.should_store_in_tier(dummy_memory): tiers.append("L4")
        return tiers

    async def recall(self, query: str, limit: int = 10, strategy: str = "comprehensive") -> List[Any]:
        """Programmatic retrieval API used by other modules."""
        self.logger.debug(f"[MemoryModule.recall] - Called with query: {query[:50]}... limit: {limit}, strategy: {strategy}")
        if not self.retrieval:
            self.logger.warning("MemoryRetrieval not initialized, cannot perform recall. Returning empty list.")
            return []
        try:
            try: retrieval_strategy_enum = RetrievalStrategy(strategy)
            except ValueError:
                self.logger.warning(f"Invalid retrieval strategy '{strategy}' in recall. Falling back to COMPREHENSIVE.")
                retrieval_strategy_enum = RetrievalStrategy.COMPREHENSIVE

            config = RetrievalConfig(max_results=limit, strategy=retrieval_strategy_enum)
            memories = await self.retrieval.retrieve(query, config=config)
            self.logger.debug(f"[MemoryModule.recall] - Retrieved {len(memories)} memories.")
            return memories or []
        except Exception as e:
            self.logger.exception(f"[MemoryModule.recall] - Error during programmatic recall for query: {query[:50]}...")
            return []

    async def search(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Compatibility wrapper so callers can use memory.search(...)."""
        self.logger.debug(f"[MemoryModule.search] - Called (legacy) with query: {query[:50]}...")
        try:
            strategy = kwargs.get('strategy', 'comprehensive')
            results = await self.recall(query, limit=limit, strategy=strategy)
            return [m.to_dict() for m in (results or [])]
        except Exception as e:
            self.logger.exception(f"[MemoryModule.search] - Error during legacy search for query: {query[:50]}...")
            return []

    async def store(self, payload: Dict[str, Any]) -> Optional[str]:
        """Compatibility wrapper for memory.store(...) used by tools."""
        self.logger.debug(f"[MemoryModule.store] - Called (legacy) with payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'non-dict'}")
        try:
            content = payload.get('content') if isinstance(payload, dict) else str(payload)
            if not content:
                self.logger.warning("[MemoryModule.store] - Legacy store called with no content.")
                return None
            importance = payload.get('importance', 0.5) if isinstance(payload, dict) else 0.5
            memory_type = payload.get('type', payload.get('memory_type', 'episodic')) if isinstance(payload, dict) else 'episodic'
            metadata = payload.get('metadata', {}) if isinstance(payload, dict) else {}
            source_module = payload.get('source_module', self.name)

            return await self.remember(content=content, memory_type=memory_type, importance=importance, metadata=metadata, source_module=source_module)
        except Exception as e:
            self.logger.exception(f"[MemoryModule.store] - Error during legacy store for content: {payload.get('content', '')[:50]}...")
            return None

    async def get_recent(self, type: str = "conversation", limit: int = 10) -> List[Dict[str, Any]]:
        """Convenience wrapper used by ContextBuilder._get_conversation_history"""
        self.logger.debug(f"[MemoryModule.get_recent] - Called (legacy) for type: {type}, limit: {limit}")
        try:
            if type == "conversation" and self.L2 and hasattr(self.L2, 'retrieve_recent'):
                recent = await self.L2.retrieve_recent(count=limit)
                out = []
                for data in recent: # L2.retrieve_recent returns MemoryItem directly
                    out.append({
                        'content': data.content,
                        'timestamp': data.timestamp,
                        'metadata': data.metadata
                    })
                self.logger.debug(f"[MemoryModule.get_recent] - Retrieved {len(out)} recent conversation items.")
                return out
            else:
                return []
        except Exception as e:
            self.logger.exception(f"[MemoryModule.get_recent] - Error during legacy get_recent for type: {type}.")
            return []

    async def get_working_memory(self) -> List[Dict[str, Any]]:
        """Return a small list of working memory entries for context builders."""
        self.logger.debug(f"[MemoryModule.get_working_memory] - Called (legacy).")
        if not self.L1: return []
        try:
            working_mem_items = await self.L1.retrieve("*", limit=10)
            out = []
            for item in working_mem_items:
                out.append(item.to_dict())
            self.logger.debug(f"[MemoryModule.get_working_memory] - Retrieved {len(out)} working memory items.")
            return out
        except Exception as e:
            self.logger.exception(f"[MemoryModule.get_working_memory] - Error during legacy get_working_memory.")
            return []

    async def remember(
        self,
        content: str,
        memory_type: str = "episodic",
        importance: float = 0.5,
        metadata: Optional[Dict] = None,
        source_module: Optional[str] = None
    ) -> Optional[str]:
        """Programmatic store API used by other modules."""
        self.logger.debug(f"[MemoryModule.remember] - Called with content: {content[:50]}... type: {memory_type}")
        metadata = metadata or {}
        source_module = source_module or self.name

        try:
            memory = MemoryItem(
                content=content,
                memory_type=MemoryType(memory_type),
                timestamp=time.time(),
                importance=importance,
                metadata=metadata,
                source_module=source_module
            )

            memory_id = await self.L1.store(memory)
            if self.L2: await self.L2.store(memory)
            if self.L3 and self.L3.should_store_in_tier(memory): await self.L3.store(memory)
            if self.L4 and self.L4.should_store_in_tier(memory): await self.L4.store(memory)
            
            self.logger.debug(f"[MemoryModule.remember] - Memory ID {memory_id} remembered across tiers.")
            return memory_id
        except Exception as e:
            self.logger.exception(f"[MemoryModule.remember] - Error storing memory for content: {content[:50]}...")
            return None

    async def shutdown(self):
        """Clean shutdown for MemoryModule."""
        self.logger.info("Memory system shutting down.")
        if self.consolidation_task:
            self.consolidation_task.cancel()
            try:
                await self.consolidation_task
            except asyncio.CancelledError:
                pass
        
        # Explicitly shut down tiers if they have a shutdown method and are not NoOp
        for tier in [self.L1, self.L2, self.L3, self.L4]:
            if tier and hasattr(tier, 'shutdown') and not tier.tier_name.endswith('_noop'):
                try:
                    await tier.shutdown()
                    self.logger.debug(f"Tier {tier.tier_name} shutdown.")
                except Exception as e:
                    self.logger.error(f"Error shutting down memory tier {tier.tier_name}: {e}", exc_info=True)
        
        self.logger.info("Memory system shutdown complete.")