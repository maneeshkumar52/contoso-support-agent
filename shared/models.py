"""Shared Pydantic models across all agents."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class Channel(str, Enum):
    EMAIL = "email"
    CHAT = "chat"
    PHONE = "phone"


class Tier(int, Enum):
    TIER_1 = 1  # Auto-resolve
    TIER_2 = 2  # RAG-assisted
    TIER_3 = 3  # Human escalation


class CustomerQuery(BaseModel):
    """Incoming customer support query."""
    customer_id: str = Field(..., description="Unique customer identifier")
    message: str = Field(..., description="Customer's message/query")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel: Channel = Field(default=Channel.CHAT)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class TriageResult(BaseModel):
    """Result from triage agent classification."""
    tier: Tier
    category: str = Field(..., description="Category of the support query")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    auto_resolve_action: Optional[str] = None


class RetrievedDocument(BaseModel):
    """A document retrieved from Azure AI Search."""
    title: str
    content: str
    relevance_score: float
    source_url: Optional[str] = None
    category: Optional[str] = None


class ToolCall(BaseModel):
    """Record of a tool call made by the agent."""
    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ResolutionResult(BaseModel):
    """Result from resolution agent."""
    answer: str
    sources: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    tool_calls_made: List[ToolCall] = Field(default_factory=list)
    tokens_used: int = 0


class DraftResult(BaseModel):
    """Result from draft agent for human review."""
    draft_response: str
    review_notes: str
    suggested_tier: Optional[Tier] = None
    priority: str = Field(default="normal")


class AuditRecord(BaseModel):
    """Complete audit record for compliance."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    customer_id: str
    session_id: str
    correlation_id: str
    query: str
    response: str
    tier: int
    agent_chain: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    token_usage: int = 0
    channel: str = "chat"


class PipelineResult(BaseModel):
    """Final result from the orchestrator pipeline."""
    final_response: str
    tier: Tier
    agents_used: List[str] = Field(default_factory=list)
    total_latency_ms: float = 0.0
    audit_id: str
    session_id: str
    sources: List[str] = Field(default_factory=list)
