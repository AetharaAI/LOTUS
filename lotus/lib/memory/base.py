"""
LOTUS Memory System - Base Memory Tier

Abstract base class for all memory tiers (L1-L4).
Defines the interface and common functionality that all memory tiers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import time
import hashlib # For a more robust ID generation


class MemoryType(Enum):
    """Types of memories"""
    EPISODIC = "episodic"        # Specific events/interactions
    SEMANTIC = "semantic"        # General knowledge/facts
    PROCEDURAL = "procedural"    # Skills and patterns
    WORKING = "working"          # Immediate context
    RAW_PERCEPTION = "raw_perception" # New: for raw, uncompressed perception data


@dataclass
class MemoryItem:
    """
    Represents a single memory across all tiers
    """
    content: str                      # The actual memory content
    memory_type: MemoryType          # Type of memory
    timestamp: float                 # When it was created
    importance: float = 0.5          # 0.0-1.0, determines tier placement
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    access_count: int = 0
    last_accessed: Optional[float] = None
    
    id: Optional[str] = None
    
    source_module: Optional[str] = None
    source_tier: Optional[str] = None
    
    def __post_init__(self):
        """Generate ID if not provided and ensure memory_type is Enum"""
        if self.id is None:
            # Generate a more robust ID using content hash to identify same content uniquely
            content_hash = hashlib.sha256(self.content.encode('utf-8')).hexdigest()[:12]
            self.id = f"{self.memory_type.value}:{int(self.timestamp * 1000000)}_{content_hash}"
        
        if isinstance(self.memory_type, str):
            self.memory_type = MemoryType(self.memory_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "content": self.content,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "metadata": self.metadata,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "id": self.id,
            "source_module": self.source_module,
            "source_tier": self.source_tier
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryItem':
        """Create from dictionary"""
        return cls(
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            timestamp=data["timestamp"],
            importance=data.get("importance", 0.5),
            metadata=data.get("metadata", {}),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed"),
            id=data.get("id"),
            source_module=data.get("source_module"),
            source_tier=data.get("source_tier")
        )

    def to_short_string(self, max_len: int = 80) -> str:
        """Returns a concise string representation of the memory."""
        content_preview = self.content.replace('\n', ' ')
        if len(content_preview) > max_len:
            content_preview = content_preview[:max_len-3] + "..."
        return f"[ID:{self.id[:8]}...] Type:{self.memory_type.value} Imp:{self.importance:.1f}: {content_preview}"
    
    def mark_accessed(self) -> None:
        """Update access tracking"""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def calculate_relevance(self, query: str, current_time: float = None) -> float:
        """
        Calculate relevance score for retrieval ranking
        """
        if current_time is None:
            current_time = time.time()
        
        age_hours = (current_time - self.timestamp) / 3600
        recency_score = 1.0 / (1.0 + age_hours / 24.0)
        
        frequency_score = min(self.access_count / 10.0, 1.0)
        
        relevance = (
            self.importance * 0.4 +
            recency_score * 0.4 +
            frequency_score * 0.2
        )
        
        return min(relevance, 1.0)


class MemoryTier(ABC):
    """
    Abstract base class for all memory tiers
    """
    
    def __init__(self, tier_name: str, tier_level: int, ttl: Optional[int] = None):
        self.tier_name = tier_name
        self.tier_level = tier_level
        self.ttl = ttl
        self.is_healthy = True
        self._last_health_check = time.time()
    
    @abstractmethod
    async def store(self, memory: MemoryItem) -> Optional[str]: # Changed return to Optional[str]
        """
        Store a memory in this tier.
        Returns the ID of the stored memory, or None if storage failed.
        """
        pass
    
    @abstractmethod
    async def retrieve(self, query: str, limit: int = 10, 
                      filters: Optional[Dict] = None) -> List[MemoryItem]:
        """
        Retrieve memories from this tier.
        """
        pass

    @abstractmethod
    async def get_memories_by_id(self, memory_ids: List[str]) -> List[MemoryItem]:
        """
        Retrieve a list of memories by their exact IDs.
        """
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """
        Delete a memory from this tier.
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get tier-specific statistics.
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Check if tier is healthy.
        """
        self._last_health_check = time.time()
        return self.is_healthy
    
    def should_store_in_tier(self, memory: MemoryItem) -> bool:
        """
        Determine if a memory should be stored in this tier.
        """
        return True
    
    async def consolidate_to_next_tier(self, next_tier: 'MemoryTier', 
                                       importance_threshold: float = 0.5) -> int:
        """
        Consolidate memories to the next tier.
        """
        memories = await self.retrieve("*", limit=1000)
        
        consolidated_count = 0
        current_time = time.time()
        
        for memory in memories:
            age_hours = (current_time - memory.timestamp) / 3600
            
            should_promote = (
                memory.importance >= importance_threshold or
                memory.access_count > 1 or
                (self.ttl and age_hours < (self.ttl / 3600))
            )
            
            if should_promote and next_tier.should_store_in_tier(memory):
                await next_tier.store(memory)
                consolidated_count += 1
        
        return consolidated_count
    
    def __repr__(self) -> str:
        return f"<MemoryTier L{self.tier_level}: {self.tier_name}, TTL={self.ttl}>"