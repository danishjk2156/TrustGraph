"""Trust-aware memory helpers for Cognee."""

from trustgraph.models import (
    ContradictionPair,
    FactStatus,
    QueryResult,
    RankedFact,
    ResolutionEvent,
    StoreResult,
    TrustMetadata,
    TrustScore,
)
from trustgraph.trust_memory import TrustMemory
from trustgraph.trust_scorer import TrustScorer
from trustgraph.visualization import install_cognee_visualizer, visualize_graph

install_cognee_visualizer()

__all__ = [
    "ContradictionPair",
    "FactStatus",
    "QueryResult",
    "RankedFact",
    "ResolutionEvent",
    "StoreResult",
    "TrustMemory",
    "TrustMetadata",
    "TrustScore",
    "TrustScorer",
    "visualize_graph",
]

__version__ = "0.1.0"
