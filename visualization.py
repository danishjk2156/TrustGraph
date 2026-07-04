"""Knowledge graph export helpers for TrustGraph."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trustgraph.models import FactStatus

try:
    from trustgraph.trust_memory import TrustMemory
except Exception:  # pragma: no cover
    TrustMemory = None


def visualize_graph(metadata_path: str | Path = "trustgraph/data/facts.json") -> dict[str, list[dict[str, Any]]]:
    """Return graph-view nodes and edges derived from the TrustGraph sidecar."""

    if TrustMemory is None:
        return {"nodes": [], "edges": []}

    memory = TrustMemory(metadata_path=metadata_path)
    facts = memory._load_facts()
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    for fact in facts:
        score = memory.scorer.score(fact, facts)
        subject_id = f"subject:{fact.subject}"
        nodes_by_id.setdefault(
            subject_id,
            {
                "id": subject_id,
                "label": fact.subject,
                "node_type": "subject",
                "trust": 1.0,
                "status": None,
                "source": "trustgraph",
                "timestamp": fact.timestamp.isoformat(),
                "reinforcement_count": 0,
            },
        )
        nodes_by_id[fact.fact_id] = {
            "id": fact.fact_id,
            "label": fact.normalized_text,
            "node_type": "fact",
            "trust": score.score,
            "status": fact.status.value,
            "source": fact.source,
            "timestamp": fact.timestamp.isoformat(),
            "reinforcement_count": fact.reinforcement_count,
        }
        edges.append(
            {
                "source": subject_id,
                "target": fact.fact_id,
                "relation": fact.predicate,
                "weight": score.score,
            }
        )
        if fact.contradiction_group:
            contradiction_id = f"contradiction:{fact.contradiction_group}"
            nodes_by_id.setdefault(
                contradiction_id,
                {
                    "id": contradiction_id,
                    "label": "Contradiction",
                    "node_type": "contradiction",
                    "trust": 0.0,
                    "status": FactStatus.CONTRADICTED.value,
                    "source": "trustgraph",
                    "timestamp": fact.timestamp.isoformat(),
                    "reinforcement_count": 0,
                },
            )
            edges.append(
                {
                    "source": fact.fact_id,
                    "target": contradiction_id,
                    "relation": "contradicts",
                    "weight": 1.0 - score.consistency_component,
                }
            )

    return {"nodes": list(nodes_by_id.values()), "edges": edges}


def install_cognee_visualizer() -> bool:
    """Attach visualize_graph to the imported cognee module when available."""

    try:
        import cognee
    except Exception:
        return False

    setattr(cognee, "visualize_graph", visualize_graph)
    return True
