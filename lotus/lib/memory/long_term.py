"""
LOTUS Memory System - L3: Long-term Memory

ChromaDB-backed long-term semantic memory.
"""

import json
import time
import asyncio
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import logging

from .base import MemoryTier, MemoryItem, MemoryType

class DummySentenceTransformerEmbeddingFunction:
    """Dummy embedder for when sentence-transformers is not available."""
    def __init__(self, *args, **kwargs):
        pass
    def __call__(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] * 384 for _ in texts]


class LongTermMemory(MemoryTier):
    """
    L3: Long-term Memory - Semantic memory (permanent, searchable by meaning)
    """
    
    def __init__(self, chroma_client: chromadb.Client, 
                 collection_name: str = "lotus_memories",
                 embedding_model: Optional[str] = "all-MiniLM-L6-v2"):
        super().__init__("long_term_memory", tier_level=3, ttl=None)
        
        self.chroma = chroma_client
        self.collection_name = collection_name
        self.logger = logging.getLogger(f"lotus.memory.{self.tier_name}")

        self.embedding_model_name = embedding_model
        self.embedding_function = None

        if self.embedding_model_name:
            try:
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.embedding_model_name
                )
                self.logger.info(f"L3 Embedding function initialized with model: {self.embedding_model_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize SentenceTransformerEmbeddingFunction for L3: {e}. Using dummy embedder.", exc_info=True)
                self.embedding_function = DummySentenceTransformerEmbeddingFunction()
        else:
            self.logger.warning("No embedding model provided or failed to load for L3. Using dummy embedder.")
            self.embedding_function = DummySentenceTransformerEmbeddingFunction()
        
        try:
            if not self.chroma:
                self.logger.warning("ChromaDB client not provided to LongTermMemory. L3 will be non-functional.")
                self.collection = None
                self.is_healthy = False
                return

            if not self.embedding_function:
                 self.logger.warning("Embedding function not initialized for L3. L3 will be non-functional.")
                 self.collection = None
                 self.is_healthy = False
                 return

            self.collection = self.chroma.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "LOTUS long-term semantic memory"}
            )
            self.logger.info(f"L3 ChromaDB collection '{collection_name}' initialized.")
        except Exception as e:
            self.logger.critical(f"Failed to get/create ChromaDB collection '{collection_name}' for L3: {e}. L3 will be non-functional.", exc_info=True)
            self.collection = None
            self.is_healthy = False
    
    async def store(self, memory: MemoryItem) -> Optional[str]:
        """Store memory in L3 (Long-term Memory)"""
        if not self.collection:
            self.logger.warning(f"Attempted to store memory {memory.id[:15]}... in L3, but collection is not initialized. Skipping.")
            return None
        if not self.embedding_function:
            self.logger.warning(f"Attempted to store memory {memory.id[:15]}... in L3, but embedding function is not initialized. Skipping.")
            return None

        try:
            memory.source_tier = "L3"
            
            metadata = {
                "memory_type": memory.memory_type.value,
                "timestamp": memory.timestamp,
                "importance": memory.importance,
                "access_count": memory.access_count,
                "last_accessed": memory.last_accessed or 0.0,
                "source_module": memory.source_module or "",
                **memory.metadata
            }
            
            await asyncio.to_thread(
                self.collection.add,
                documents=[memory.content],
                metadatas=[metadata],
                ids=[memory.id]
            )
            self.logger.debug(f"Stored memory {memory.id[:15]}... in L3.")
            return memory.id
        except Exception as e:
            self.logger.exception(f"Error storing memory {memory.id[:15]}... in L3.")
            raise
    
    async def store_semantic_summary(self, summary: str, original_memory_id: Optional[str], metadata: Dict, source_module: str) -> Optional[str]:
        """Store a semantic summary directly into L3. Used by the ContextOrchestrator."""
        if not self.collection or not self.embedding_function:
            self.logger.warning(f"Attempted to store semantic summary (original ID: {original_memory_id[:15]}...) in L3, but L3 is not functional. Skipping.")
            return None

        try:
            summary_memory = MemoryItem(
                content=summary,
                memory_type=MemoryType.SEMANTIC,
                timestamp=time.time(),
                importance=0.6,
                metadata={"original_memory_id": original_memory_id, **metadata},
                source_module=source_module
            )
            return await self.store(summary_memory)
        except Exception as e:
            self.logger.exception(f"Error storing semantic summary (original ID: {original_memory_id[:15]}...) in L3.")
            return None

    async def retrieve(self, query: str, limit: int = 10,
                      filters: Optional[Dict] = None) -> List[MemoryItem]:
        """Retrieve memories from long-term memory using semantic search"""
        if not self.collection or not self.embedding_function:
            self.logger.warning(f"Attempted to retrieve from L3 with query: {query[:50]}..., but L3 is not functional. Returning empty list.")
            return []
        
        self.logger.debug(f"Retrieving from L3 with query: {query[:50]}..., limit: {limit}, filters: {filters}")
        memories = []
        try:
            where = {}
            if filters:
                if 'memory_type' in filters: where['memory_type'] = filters['memory_type']
                if 'min_importance' in filters: where['importance'] = {"$gte": filters['min_importance']}
                if 'source_module' in filters: where['source_module'] = filters['source_module']
            
            results = await asyncio.to_thread(self.collection.query,
                query_texts=[query],
                n_results=limit,
                where=where if where else None
            )
            
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i] if 'distances' in results else 0.0
                    
                    memory = MemoryItem(
                        content=doc,
                        memory_type=MemoryType(metadata.get('memory_type', 'semantic')),
                        timestamp=metadata.get('timestamp', time.time()),
                        importance=metadata.get('importance', 0.5),
                        access_count=metadata.get('access_count', 0),
                        last_accessed=metadata.get('last_accessed') or None,
                        id=results['ids'][0][i],
                        source_module=metadata.get('source_module') or None,
                        source_tier="L3",
                        metadata={
                            **{k: v for k, v in metadata.items() 
                               if k not in ['memory_type', 'timestamp', 'importance', 
                                           'access_count', 'last_accessed', 'source_module']},
                            'semantic_distance': distance
                        }
                    )
                    
                    memory.mark_accessed()
                    await asyncio.to_thread(self._update_access, memory.id, memory.access_count, memory.last_accessed)
                    
                    memories.append(memory)
            self.logger.debug(f"Successfully retrieved {len(memories)} memories from L3.")
            return memories
        except Exception as e:
            self.logger.exception(f"Error retrieving from L3 with query: {query[:50]}...")
            return []

    async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]:
        """Retrieve a list of memories by their exact IDs from L3."""
        if not self.collection: return []
        self.logger.debug(f"Getting {len(memory_ids)} memories by ID from L3.")
        memories = []
        if not memory_ids:
            return []
        
        try:
            results = await asyncio.to_thread(self.collection.get, ids=memory_ids, include=['documents', 'metadatas'])
            
            if results and results['documents']:
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i]
                    
                    memory = MemoryItem(
                        content=doc,
                        memory_type=MemoryType(metadata.get('memory_type', 'semantic')),
                        timestamp=metadata.get('timestamp', time.time()),
                        importance=metadata.get('importance', 0.5),
                        access_count=metadata.get('access_count', 0),
                        last_accessed=metadata.get('last_accessed') or None,
                        id=results['ids'][i],
                        source_module=metadata.get('source_module') or None,
                        source_tier="L3",
                        metadata={k: v for k, v in metadata.items() 
                                 if k not in ['memory_type', 'timestamp', 'importance', 
                                             'access_count', 'last_accessed', 'source_module']}
                    )
                    memory.mark_accessed()
                    await asyncio.to_thread(self._update_access, memory.id, memory.access_count, memory.last_accessed)
                    memories.append(memory)
            return memories
        except Exception as e:
            self.logger.exception(f"Error getting memories by ID from L3.")
            return []
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a specific memory from long-term memory"""
        if not self.collection: return False
        try:
            await asyncio.to_thread(self.collection.delete, ids=[memory_id])
            self.logger.debug(f"Deleted memory {memory_id[:15]}... from L3.")
            return True
        except Exception as e:
            self.logger.exception(f"Error deleting memory {memory_id[:15]}... from L3.")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get long-term memory statistics"""
        if not self.collection: return {"tier": "L3_long_term_uninitialized", "count": 0}
        self.logger.debug("Getting L3 statistics.")
        try:
            count = await asyncio.to_thread(self.collection.count)
            
            avg_importance = 0
            oldest_timestamp = None
            newest_timestamp = None
            memory_types = {}

            if count > 0:
                results = await asyncio.to_thread(self.collection.get, limit=min(count, 1000), include=['metadatas'])
                
                if results and results['metadatas']:
                    metadatas = results['metadatas']
                    
                    total_importance = sum(m.get('importance', 0.5) for m in metadatas)
                    avg_importance = total_importance / len(metadatas) if metadatas else 0
                    
                    timestamps = [m.get('timestamp', 0) for m in metadatas]
                    oldest_timestamp = min(timestamps) if timestamps else None
                    newest_timestamp = max(timestamps) if timestamps else None
                    
                    for m in metadatas:
                        mem_type = m.get('memory_type', 'semantic')
                        memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
            
            stats = {
                "tier": "L3_long_term",
                "count": count,
                "max_capacity": "unlimited",
                "avg_importance": avg_importance,
                "oldest_timestamp": oldest_timestamp,
                "newest_timestamp": newest_timestamp,
                "age_days": (time.time() - (oldest_timestamp or time.time())) / 86400 if oldest_timestamp else 0,
                "memory_types": memory_types,
                "storage_type": "chromadb_vectors",
                "embedding_model": self.embedding_model_name or "dummy"
            }
            self.logger.debug("L3 statistics generated.")
            return stats
        except Exception as e:
            self.logger.exception("Error getting L3 statistics.")
            return {"tier": "L3_long_term", "error": str(e), "count": 0}
    
    async def find_similar(self, memory_id: str, limit: int = 5) -> List[MemoryItem]:
        """Find memories similar to a given memory"""
        if not self.collection or not self.embedding_function: return []
        self.logger.debug(f"Finding similar memories to {memory_id[:15]}... in L3.")
        try:
            results = await asyncio.to_thread(self.collection.get, ids=[memory_id], include=['documents'])
            
            if not results or not results['documents']:
                self.logger.debug(f"Source memory {memory_id[:15]}... not found for similarity search.")
                return []
            
            source_content = results['documents'][0][0] # results['documents'] is List[List[str]]
            
            return await self.retrieve(source_content, limit=limit + 1)
        except Exception as e:
            self.logger.exception(f"Error finding similar memories to {memory_id[:15]}... in L3.")
            return []
    
    async def get_by_type(self, memory_type: MemoryType, limit: int = 100) -> List[MemoryItem]:
        """Get all memories of a specific type"""
        if not self.collection or not self.embedding_function: return []
        self.logger.debug(f"Getting L3 memories by type: {memory_type.value}, limit: {limit}.")
        memories = []
        try:
            results = await asyncio.to_thread(self.collection.get,
                where={"memory_type": memory_type.value},
                limit=limit,
                include=['documents', 'metadatas', 'ids'] # Ensure IDs are included
            )
            
            if results and results['documents']:
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i]
                    
                    memory = MemoryItem(
                        content=doc,
                        memory_type=memory_type,
                        timestamp=metadata.get('timestamp', time.time()),
                        importance=metadata.get('importance', 0.5),
                        access_count=metadata.get('access_count', 0),
                        last_accessed=metadata.get('last_accessed') or None,
                        id=results['ids'][i],
                        source_module=metadata.get('source_module') or None,
                        source_tier="L3",
                        metadata={k: v for k, v in metadata.items() 
                                 if k not in ['memory_type', 'timestamp', 'importance', 
                                             'access_count', 'last_accessed', 'source_module']}
                    )
                    memories.append(memory)
            
            memories.sort(key=lambda m: m.importance, reverse=True)
            self.logger.debug(f"Retrieved {len(memories)} L3 memories of type {memory_type.value}.")
            return memories
        except Exception as e:
            self.logger.exception(f"Error getting L3 memories by type {memory_type.value}.")
            return []
    
    async def get_important_memories(self, min_importance: float = 0.7, 
                                    limit: int = 50) -> List[MemoryItem]:
        """Get the most important memories"""
        if not self.collection or not self.embedding_function: return []
        self.logger.debug(f"Getting L3 important memories with min_importance: {min_importance}, limit: {limit}.")
        memories = []
        try:
            results = await asyncio.to_thread(self.collection.get,
                where={"importance": {"$gte": min_importance}},
                limit=limit,
                include=['documents', 'metadatas', 'ids'] # Ensure IDs are included
            )
            
            if results and results['documents']:
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i]
                    
                    memory = MemoryItem(
                        content=doc,
                        memory_type=MemoryType(metadata.get('memory_type', 'semantic')),
                        timestamp=metadata.get('timestamp', time.time()),
                        importance=metadata.get('importance', 0.5),
                        access_count=metadata.get('access_count', 0),
                        last_accessed=metadata.get('last_accessed') or None,
                        id=results['ids'][i],
                        source_module=metadata.get('source_module') or None,
                        source_tier="L3",
                        metadata={k: v for k, v in metadata.items() 
                                 if k not in ['memory_type', 'timestamp', 'importance', 
                                             'access_count', 'last_accessed', 'source_module']}
                    )
                    memories.append(memory)
            
            memories.sort(key=lambda m: m.importance, reverse=True)
            self.logger.debug(f"Retrieved {len(memories)} important L3 memories.")
            return memories
        except Exception as e:
            self.logger.exception(f"Error getting L3 important memories with min_importance {min_importance}.")
            return []
    
    def _update_access(self, memory_id: str, access_count: int, 
                            last_accessed: Optional[float]) -> None:
        """Update access tracking for a memory (synchronous for to_thread)"""
        if not self.collection: return
        try:
            self.collection.update(
                ids=[memory_id],
                metadatas=[{
                    "access_count": access_count,
                    "last_accessed": last_accessed or 0.0
                }]
            )
            self.logger.debug(f"Updated access for {memory_id[:15]}... in L3.")
        except Exception as e:
            self.logger.error(f"Error updating access for memory {memory_id[:15]}... in L3: {e}")
    
    async def health_check(self) -> bool:
        """Check if ChromaDB is accessible"""
        try:
            if not self.chroma or not self.collection:
                self.is_healthy = False
                self.logger.warning("L3 health check: ChromaDB client or collection is None/uninitialized.")
                return False

            await asyncio.to_thread(self.collection.count)
            self.is_healthy = True
            self.logger.debug("L3 health check successful.")
            return True
        except Exception as e:
            self.is_healthy = False
            self.logger.error(f"L3 health check failed: {e}", exc_info=True)
            return False
    
    def should_store_in_tier(self, memory: MemoryItem) -> bool:
        """Long-term memory stores memories that have importance >= 0.5 or are semantic/procedural/raw_perception."""
        return (
            memory.importance >= 0.5 or
            memory.memory_type in [MemoryType.SEMANTIC, MemoryType.PROCEDURAL, MemoryType.RAW_PERCEPTION]
        )