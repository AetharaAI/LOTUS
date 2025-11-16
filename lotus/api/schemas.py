"""
LOTUS API - Pydantic Schemas

Data models for API requests and responses.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# CHAT SCHEMAS
# ============================================================================

class ChatMessage(BaseModel):
    """Single chat message"""
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Chat completion request"""
    messages: List[ChatMessage]
    model: str = Field(default="auto", description="Model to use: auto, apriel, grok, or claude")
    stream: bool = Field(default=True, description="Stream response via SSE")
    conversation_id: Optional[str] = Field(default=None, description="Resume existing conversation")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)


class ChatChunk(BaseModel):
    """Streaming chat chunk"""
    type: Literal["thinking", "content", "model", "error"]
    content: Optional[str] = None
    model: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# MODEL SCHEMAS
# ============================================================================

class ModelInfo(BaseModel):
    """Model information"""
    id: str
    name: str
    status: Literal["online", "offline", "degraded"]
    capabilities: List[str]
    hosted: Literal["self", "xai", "anthropic", "openai"]
    description: str
    cost_per_1m_tokens: Optional[float] = None


class ModelsResponse(BaseModel):
    """List of available models"""
    models: List[ModelInfo]


# ============================================================================
# CONVERSATION SCHEMAS
# ============================================================================

class ConversationSummary(BaseModel):
    """Summary of a conversation"""
    id: str
    title: str
    model: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationsResponse(BaseModel):
    """List of conversations"""
    conversations: List[ConversationSummary]


class ConversationDetail(BaseModel):
    """Full conversation with messages"""
    id: str
    title: str
    model: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessage]


# ============================================================================
# HEALTH SCHEMAS
# ============================================================================

class ServiceStatus(BaseModel):
    """Status of a service"""
    name: str
    status: Literal["connected", "disconnected", "degraded"]
    latency_ms: Optional[float] = None


class HealthResponse(BaseModel):
    """System health check"""
    status: Literal["healthy", "degraded", "down"]
    models: Dict[str, str]  # model_id -> status
    services: Dict[str, str]  # service_name -> status
    uptime: int  # seconds
    version: str


# ============================================================================
# MEMORY SCHEMAS
# ============================================================================

class MemoryQuery(BaseModel):
    """Query memory/context"""
    query: str
    limit: int = Field(default=10, gt=0, le=100)
    conversation_id: Optional[str] = None


class MemoryItem(BaseModel):
    """Memory item"""
    content: str
    timestamp: datetime
    relevance_score: float
    source: str  # conversation_id or system


class MemoryResponse(BaseModel):
    """Memory query results"""
    items: List[MemoryItem]
    total: int


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
