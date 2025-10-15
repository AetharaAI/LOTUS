# 🔌 LOTUS MEMORY SYSTEM - INTEGRATION GUIDE

**Quick Start**: How to integrate the new 4-tier memory system into your existing LOTUS installation

---

## 📋 PREREQUISITES

Before integrating, ensure you have:

```bash
# 1. Redis running
redis-cli ping  # Should return PONG

# 2. PostgreSQL running
psql -U postgres -c "SELECT version();"

# 3. Python dependencies installed
pip install redis chromadb psycopg sentence-transformers
```

---

## 🔧 STEP 1: Copy Memory Files

```bash
# From your LOTUS project root:
cp -r /mnt/user-data/outputs/lib/memory lotus/lib/
```

Verify structure:
```
lotus/
└── lib/
    └── memory/
        ├── __init__.py
        ├── base.py
        ├── working_memory.py
        ├── short_term.py
        ├── long_term.py
        ├── persistent.py
        └── retrieval.py
```

---

## 🔧 STEP 2: Update Memory Module

**File**: `lotus/modules/core_modules/memory/logic.py`

Replace the existing MemoryModule class:

```python
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
        redis_client = self.config.get("connections.redis")
        chroma_client = self.config.get("connections.chromadb")
        postgres_conn = self.config.get("connections.postgres")
        
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
```

---

## 🔧 STEP 3: Update Reasoning Engine

**File**: `lotus/modules/core_modules/reasoning/logic.py`

Add memory retrieval to the `_build_context` method:

```python
async def _build_context(self, user_query: str) -> Dict:
    """
    Build context for reasoning
    
    Now includes memory retrieval!
    """
    # Get recent conversation context (last 10 minutes)
    await self.publish("memory.get_context", {"minutes": 10})
    recent_response = await self.wait_for_event("memory.context", timeout=2.0)
    recent_context = recent_response.get("memories", []) if recent_response else []
    
    # Get relevant memories from all tiers
    await self.publish("memory.retrieve", {
        "query": user_query,
        "max_results": 5,
        "strategy": "comprehensive"
    })
    memory_response = await self.wait_for_event("memory.retrieved", timeout=2.0)
    relevant_memories = memory_response.get("memories", []) if memory_response else []
    
    # Build full context
    context = {
        "query": user_query,
        "recent_context": recent_context,
        "relevant_memories": relevant_memories,
        "timestamp": time.time()
    }
    
    return context
```

And update the thought storage:

```python
async def _store_thought(self, thought: str, importance: float = 0.6):
    """Store a thought/reasoning in memory"""
    await self.publish("memory.store", {
        "content": thought,
        "memory_type": "procedural",
        "importance": importance,
        "source_module": "reasoning"
    })
```

---

## 🔧 STEP 4: Update Configuration

**File**: `lotus/config/system.yaml`

Add memory configuration (if not already present):

```yaml
memory:
  # L1: Working Memory (Redis)
  working_memory:
    ttl_seconds: 600  # 10 minutes
    max_items: 100
  
  # L2: Short-term Memory (Redis Streams)
  short_term:
    ttl_hours: 24
    max_items: 1000
  
  # L3: Long-term Memory (ChromaDB)
  long_term:
    collection_name: "lotus_memories"
    embedding_model: "all-MiniLM-L6-v2"
    distance_metric: "cosine"
  
  # L4: Persistent Memory (PostgreSQL)
  persistent:
    table_name: "lotus_knowledge"
    auto_index: true
  
  # Memory Consolidation
  consolidation:
    enabled: true
    interval_minutes: 30
    importance_threshold: 0.5
```

---

## 🔧 STEP 5: Update Nucleus Connection Setup

**File**: `lotus/nucleus.py`

In the `__init__` method, add connections for memory backends:

```python
async def __init__(self):
    # ... existing code ...
    
    # Initialize memory backends
    self.redis_client = await redis.from_url(
        self.config.get("redis.url", "redis://localhost:6379")
    )
    
    self.chroma_client = chromadb.Client(
        Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.config.get("chromadb.persist_dir", "./data/chromadb")
        )
    )
    
    self.postgres_conn = await psycopg.AsyncConnection.connect(
        self.config.get("postgres.connection_string", 
                       "dbname=lotus user=postgres password=lotus")
    )
    
    # Store connections in config for modules to access
    self.config.set("connections.redis", self.redis_client)
    self.config.set("connections.chromadb", self.chroma_client)
    self.config.set("connections.postgres", self.postgres_conn)
```

---

## ✅ STEP 6: Test Integration

Create `test_integration.py`:

```python
"""Test LOTUS with new memory system"""

import asyncio
import sys
import os

# Add lotus to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lotus'))

from lib.message_bus import MessageBus
from modules.core_modules.memory.logic import MemoryModule


async def test_memory_integration():
    print("🧠 Testing LOTUS Memory Integration\n")
    
    # 1. Initialize message bus
    print("1️⃣ Initializing message bus...")
    message_bus = MessageBus("redis://localhost:6379")
    await message_bus.connect()
    
    # 2. Initialize memory module
    print("2️⃣ Initializing memory module...")
    # ... (create memory module instance)
    
    # 3. Test memory storage
    print("3️⃣ Testing memory storage...")
    await message_bus.publish("memory.store", {
        "content": "Testing LOTUS memory integration",
        "memory_type": "episodic",
        "importance": 0.7,
        "source_module": "test"
    })
    
    # Wait for storage confirmation
    await asyncio.sleep(1)
    
    # 4. Test memory retrieval
    print("4️⃣ Testing memory retrieval...")
    await message_bus.publish("memory.retrieve", {
        "query": "testing memory",
        "max_results": 5
    })
    
    # Wait for results
    await asyncio.sleep(1)
    
    # 5. Test context retrieval
    print("5️⃣ Testing context retrieval...")
    await message_bus.publish("memory.get_context", {
        "minutes": 10
    })
    
    await asyncio.sleep(1)
    
    print("\n✅ Integration test complete!\n")
    
    await message_bus.disconnect()


if __name__ == "__main__":
    asyncio.run(test_memory_integration())
```

---

## 🎯 VERIFICATION CHECKLIST

After integration, verify:

- [ ] Redis is accessible: `redis-cli ping`
- [ ] PostgreSQL is accessible: `psql -U postgres -d lotus -c "SELECT 1"`
- [ ] ChromaDB directory exists: `ls -la ./data/chromadb`
- [ ] Memory module loads: Check LOTUS startup logs
- [ ] Memory events work: Test with integration script
- [ ] Consolidation runs: Check logs after 30 minutes
- [ ] Stats accessible: Query memory stats via CLI

---

## 🐛 TROUBLESHOOTING

### Issue: "Module 'memory' not found"
**Solution**: Ensure `lib/memory/` directory is in place

### Issue: "Redis connection refused"
**Solution**: Start Redis: `redis-server`

### Issue: "PostgreSQL authentication failed"
**Solution**: Check connection string in config

### Issue: "ChromaDB import error"
**Solution**: `pip install chromadb sentence-transformers`

---

## 📚 USAGE EXAMPLES

### Store a memory:
```python
await message_bus.publish("memory.store", {
    "content": "User prefers Claude for coding tasks",
    "memory_type": "semantic",
    "importance": 0.9
})
```

### Retrieve memories:
```python
await message_bus.publish("memory.retrieve", {
    "query": "user preferences",
    "max_results": 5
})
```

### Get recent context:
```python
await message_bus.publish("memory.get_context", {
    "minutes": 10
})
```

---

## ✨ SUCCESS!

Your memory system is now integrated! LOTUS can now remember, learn, and build context over time.

**Next steps**:
1. Boot LOTUS: `python lotus/nucleus.py`
2. Test memory: Have a conversation and check if it remembers
3. Check stats: Query memory statistics
4. Monitor logs: Watch consolidation process

**Welcome to continuous AI consciousness!** 🧠✨