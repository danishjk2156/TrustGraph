"""Pydantic models used by the trust memory layer."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class FactStatus(str, Enum):
    ACTIVE = "active"
    CONTRADICTED = "contradicted"
    RESOLVED = "resolved"
    DECAYED = "decayed"


class TrustMetadata(BaseModel):
    """Metadata attached to every fact stored in memory."""

    fact_id: str
    original_text: str
    normalized_text: str
    subject: str
    predicate: str
    object_value: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reinforcement_count: int = 0
    source: str = "user"
    status: FactStatus = FactStatus.ACTIVE
    contradiction_group: Optional[str] = None
    cognee_data_id: Optional[str] = None


class TrustScore(BaseModel):
    """Computed trust score for a fact."""

    fact_id: str
    score: float = Field(ge=0.0, le=1.0)
    recency_component: float = Field(ge=0.0, le=1.0)
    reinforcement_component: float = Field(ge=0.0, le=1.0)
    consistency_component: float = Field(ge=0.0, le=1.0)
    reasoning: str


class ContradictionPair(BaseModel):
    """A detected contradiction between two facts."""

    fact_a: TrustMetadata
    fact_b: TrustMetadata
    trust_a: float
    trust_b: float
    subject: str
    predicate: str
    explanation: str
    resolved: bool = False
    winner_id: Optional[str] = None


class RankedFact(BaseModel):
    """A fact plus its computed score for query responses."""

    fact: TrustMetadata
    trust_score: TrustScore
    memory_result: Optional[Any] = None


class StoreResult(BaseModel):
    """Result returned after storing text in trust-aware memory."""

    stored_facts: list[TrustMetadata]
    contradictions: list[ContradictionPair] = Field(default_factory=list)


class QueryResult(BaseModel):
    """Trust-ranked query response."""

    query_text: str
    ranked_facts: list[RankedFact]
    contradictions: list[ContradictionPair] = Field(default_factory=list)
    raw_results: list[Any] = Field(default_factory=list)
