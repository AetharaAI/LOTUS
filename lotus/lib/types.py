"""
LOTUS Type Definitions

This module contains common type definitions used across the LOTUS system.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

@dataclass
class Thought:
    """Represents a single thought or cognitive process"""
    id: str
    content: str
    type: str  # reasoning, memory, perception, etc
    source: str  # module that generated the thought
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
@dataclass 
class Intent:
    """Represents detected user intent"""
    type: str
    confidence: float
    data: Dict[str, Any]
    
@dataclass
class Response:
    """Represents a system response"""
    content: str
    type: str
    metadata: Dict[str, Any]