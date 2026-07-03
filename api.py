"""FastAPI backend for the TrustGraph hackathon demo."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from trustgraph.models import ContradictionPair, FactStatus, TrustMetadata, TrustScore
from trustgraph.trust_memory import TrustMemory


app = FastAPI(title="TrustGraph", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory = TrustMemory()


class StoreRequest(BaseModel):
    text: str = Field(min_length=1)
    source: str = "user"
    importance_weight: float = Field(default=1.0, ge=0.0, le=10.0)


class QueryRequest(BaseModel):
    query_text: str = Field(min_length=1)
    feedback_influence: float = Field(default=0.5, ge=0.0, le=1.0)


class ResolveRequest(BaseModel):
    contradiction_id: str = Field(min_length=1)
    winner_id: str | None = None
    action: Literal["keep_winner", "keep_both"] = "keep_winner"
    feedback_alpha: float = Field(default=0.1, ge=0.0, le=1.0)


class ReinforceRequest(BaseModel):
    fact_id: str = Field(min_length=1)
    feedback_alpha: float = Field(default=0.1, ge=0.0, le=1.0)


class FactWithTrust(BaseModel):
    fact: TrustMetadata
    trust_score: TrustScore


class FactsResponse(BaseModel):
    facts: list[FactWithTrust]
    total: int
    active_count: int
    contradicted_count: int
    decayed_count: int


class GraphNode(BaseModel):
    id: str
    label: str
    node_type: Literal["fact", "subject", "contradiction"]
    trust: float
    status: FactStatus | None = None
    source: str
    timestamp: str
    reinforcement_count: int


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    weight: float = 1.0


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/store")
async def store_fact(request: StoreRequest):
    return await memory.store(
        request.text,
        source=request.source,
        importance_weight=request.importance_weight,
    )


@app.post("/api/query")
async def query_memory(request: QueryRequest):
    result = await memory.query(
        request.query_text,
        feedback_influence=request.feedback_influence,
    )
    return result.model_dump(mode="json", exclude={"raw_results"})


@app.get("/api/facts", response_model=FactsResponse)
async def list_facts() -> FactsResponse:
    facts = memory._load_facts()
    scored = [
        FactWithTrust(fact=fact, trust_score=memory.scorer.score(fact, facts))
        for fact in facts
    ]
    scored.sort(key=lambda item: item.fact.timestamp, reverse=True)

    counts = Counter(fact.status for fact in facts)
    return FactsResponse(
        facts=scored,
        total=len(facts),
        active_count=counts[FactStatus.ACTIVE],
        contradicted_count=counts[FactStatus.CONTRADICTED],
        decayed_count=counts[FactStatus.DECAYED],
    )


@app.get("/api/contradictions")
async def list_contradictions():
    facts = memory._load_facts()
    contradictions = await memory._active_contradictions(facts)
    contradictions = [
        pair
        for pair in contradictions
        if pair.fact_a.contradiction_group or pair.fact_b.contradiction_group
    ]
    contradictions = _dedupe_contradictions(contradictions)
    return {
        "contradictions": [_contradiction_payload(pair) for pair in contradictions],
        "total": len(contradictions),
    }


@app.post("/api/resolve")
async def resolve_contradiction(request: ResolveRequest):
    if request.action == "keep_both":
        changed = _keep_both(request.contradiction_id)
        if not changed:
            raise HTTPException(status_code=404, detail="Unknown contradiction_id")
        return {"resolved": True, "action": "keep_both"}

    if not request.winner_id:
        raise HTTPException(
            status_code=422,
            detail="winner_id is required when action is keep_winner",
        )

    try:
        await memory.resolve_contradiction(
            request.contradiction_id,
            request.winner_id,
            feedback_alpha=request.feedback_alpha,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "resolved": True,
        "action": "keep_winner",
        "winner_id": request.winner_id,
    }


@app.post("/api/reinforce")
async def reinforce_fact(request: ReinforceRequest):
    try:
        await memory.reinforce(request.fact_id, feedback_alpha=request.feedback_alpha)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"reinforced": True, "fact_id": request.fact_id}


@app.post("/api/decay")
async def run_decay_check():
    decayed = await memory.decay_check()
    return {"decayed_fact_ids": decayed, "count": len(decayed)}


@app.post("/api/reset")
async def reset_memory():
    try:
        import cognee

        await cognee.forget(everything=True)
    except Exception:
        pass

    path = Path(memory.metadata_path)
    if path.exists():
        path.unlink()
    return {"reset": True}


@app.get("/api/graph", response_model=GraphResponse)
async def graph_data() -> GraphResponse:
    facts = memory._load_facts()
    nodes_by_id: dict[str, GraphNode] = {}
    edges = []

    for fact in facts:
        score = memory.scorer.score(fact, facts)
        subject_id = f"subject:{fact.subject}"
        nodes_by_id.setdefault(
            subject_id,
            GraphNode(
                id=subject_id,
                label=fact.subject,
                node_type="subject",
                trust=1.0,
                source="trustgraph",
                timestamp=fact.timestamp.isoformat(),
                reinforcement_count=0,
            ),
        )
        nodes_by_id[fact.fact_id] = GraphNode(
            id=fact.fact_id,
            label=fact.normalized_text,
            node_type="fact",
            trust=score.score,
            status=fact.status,
            source=fact.source,
            timestamp=fact.timestamp.isoformat(),
            reinforcement_count=fact.reinforcement_count,
        )
        edges.append(
            GraphEdge(
                source=subject_id,
                target=fact.fact_id,
                relation=fact.predicate,
                weight=score.score,
            )
        )
        if fact.contradiction_group:
            contradiction_id = f"contradiction:{fact.contradiction_group}"
            nodes_by_id.setdefault(
                contradiction_id,
                GraphNode(
                    id=contradiction_id,
                    label="Contradiction",
                    node_type="contradiction",
                    trust=0.0,
                    source="trustgraph",
                    timestamp=fact.timestamp.isoformat(),
                    reinforcement_count=0,
                ),
            )
            edges.append(
                GraphEdge(
                    source=fact.fact_id,
                    target=contradiction_id,
                    relation="contradicts",
                    weight=1.0 - score.consistency_component,
                )
            )

    return GraphResponse(nodes=list(nodes_by_id.values()), edges=edges)


def _contradiction_payload(pair: ContradictionPair) -> dict:
    contradiction_id = (
        pair.fact_a.contradiction_group
        or pair.fact_b.contradiction_group
        or f"{pair.fact_a.fact_id}:{pair.fact_b.fact_id}"
    )
    return {
        "contradiction_id": contradiction_id,
        "fact_a": pair.fact_a.model_dump(mode="json"),
        "fact_b": pair.fact_b.model_dump(mode="json"),
        "trust_a": pair.trust_a,
        "trust_b": pair.trust_b,
        "subject": pair.subject,
        "predicate": pair.predicate,
        "explanation": pair.explanation,
        "resolved": pair.resolved,
        "winner_id": pair.winner_id,
    }


def _dedupe_contradictions(
    contradictions: list[ContradictionPair],
) -> list[ContradictionPair]:
    seen: set[tuple[str, str]] = set()
    deduped: list[ContradictionPair] = []
    for pair in contradictions:
        key = tuple(sorted([pair.fact_a.fact_id, pair.fact_b.fact_id]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(pair)
    return deduped


def _keep_both(contradiction_id: str) -> bool:
    facts = memory._load_facts()
    changed = False

    for fact in facts:
        if fact.contradiction_group != contradiction_id:
            continue
        fact.status = FactStatus.ACTIVE
        fact.contradiction_group = None
        changed = True

    if changed:
        memory._save_facts(facts)
    return changed
