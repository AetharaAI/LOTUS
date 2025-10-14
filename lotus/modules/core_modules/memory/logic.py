from lib.module import BaseModule
from lib.decorators import on_event, periodic

class MemoryModule(BaseModule):
    """Memory coordinator - wraps the lib/memory.py system"""
    
    async def initialize(self):
        self.logger.info("Memory module initializing...")
        # Memory system is already available via self.memory
        self.logger.info("Memory module ready")
    
    @on_event("memory.store")
    async def on_store_request(self, event):
        """Store a memory"""
        content = event.data.get("content")
        memory_type = event.data.get("type", "episodic")
        importance = event.data.get("importance", 0.5)
        
        memory_id = await self.memory.remember(content, memory_type, importance)
        
        await self.publish("memory.stored", {
            "memory_id": memory_id,
            "content": content
        })
    
    @on_event("memory.recall")
    async def on_recall_request(self, event):
        """Retrieve memories"""
        query = event.data.get("query")
        limit = event.data.get("limit", 10)
        
        memories = await self.memory.recall(query, limit)
        
        await self.publish("memory.recall_result", {
            "query": query,
            "memories": [m.to_dict() for m in memories]
        })
    
    @periodic(interval=300)  # Every 5 minutes
    async def consolidate_memories(self):
        """Move memories from short-term to long-term"""
        await self.memory.consolidate()