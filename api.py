"""FastAPI backend for the TrustGraph hackathon demo."""

from __future__ import annotations

import os

# Load .env file
try:
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    from pathlib import Path
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip("'\"")

if os.getenv("LLM_API_KEY") and not os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = os.getenv("LLM_API_KEY")

from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from trustgraph.models import (
    ContradictionPair,
    FactStatus,
    ResolutionEvent,
    TrustMetadata,
    TrustScore,
)
from trustgraph.trust_memory import TrustMemory
from trustgraph.visualization import visualize_graph


app = FastAPI(title="TrustGraph", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory = TrustMemory()
DATA_DIR = Path("trustgraph/data")
STATIC_DIR = Path(__file__).resolve().parent / "static"
CHAT_SESSIONS_PATH = DATA_DIR / "chat_sessions.json"


class StoreRequest(BaseModel):
    text: str = Field(min_length=1)
    source: str = "user"
    importance_weight: float = Field(default=1.0, ge=0.0, le=10.0)


class QueryRequest(BaseModel):
    query_text: str = Field(min_length=1)
    feedback_influence: float = Field(default=0.5, ge=0.0, le=1.0)


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    feedback_influence: float = Field(default=0.5, ge=0.0, le=1.0)


class ChatSessionCreateRequest(BaseModel):
    title: str | None = None


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


class ResolutionsResponse(BaseModel):
    resolutions: list[ResolutionEvent]
    total: int


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="static/index.html not found")
    return FileResponse(index_path)


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


@app.post("/api/chat/sessions")
async def create_chat_session(request: ChatSessionCreateRequest | None = None):
    sessions = _load_chat_sessions()
    now = datetime.utcnow().isoformat()
    session_id = str(uuid4())
    sessions[session_id] = {
        "id": session_id,
        "title": (request.title if request else None) or "New Chat",
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    _save_chat_sessions(sessions)
    return sessions[session_id]


@app.get("/api/chat/sessions")
async def list_chat_sessions():
    sessions = list(_load_chat_sessions().values())
    sessions.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return {
        "sessions": [
            {
                "id": item["id"],
                "title": item.get("title") or "New Chat",
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "message_count": len(item.get("messages", [])),
            }
            for item in sessions
        ]
    }


@app.get("/api/chat/sessions/{session_id}")
async def get_chat_session(session_id: str):
    sessions = _load_chat_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Unknown chat session")
    return sessions[session_id]


@app.post("/api/chat/sessions/{session_id}/messages")
async def append_chat_message(session_id: str, request: ChatMessageRequest):
    sessions = _load_chat_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Unknown chat session")

    now = datetime.utcnow().isoformat()
    user_message = {
        "id": str(uuid4()),
        "role": "user",
        "content": request.content,
        "created_at": now,
    }
    sessions[session_id].setdefault("messages", []).append(user_message)

    result = await memory.query(
        request.content,
        feedback_influence=request.feedback_influence,
        session_id=session_id,
    )
    assistant_message = {
        "id": str(uuid4()),
        "role": "assistant",
        "content": result.answer_text or "",
        "created_at": datetime.utcnow().isoformat(),
        "query": result.model_dump(mode="json", exclude={"raw_results"}),
    }
    sessions[session_id]["messages"].append(assistant_message)
    sessions[session_id]["updated_at"] = assistant_message["created_at"]
    if sessions[session_id].get("title") == "New Chat":
        sessions[session_id]["title"] = request.content[:48]

    _save_chat_sessions(sessions)
    return {"session": sessions[session_id], "message": assistant_message}


@app.post("/api/upload")
async def upload_document(request: Request, filename: str = "document.txt"):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/"):
        raise HTTPException(
            status_code=415,
            detail="Send the file as the raw request body with ?filename=name.txt",
        )

    body = await request.body()
    if not body:
        raise HTTPException(status_code=422, detail="Uploaded document is empty")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="Only UTF-8 text uploads are supported") from exc

    result_cognee = None
    import cognee
    try:
        result_cognee = await cognee.remember(text, self_improvement=True)
    except Exception:
        pass

    result = await memory.store(text, source="document")
    return {
        "filename": filename,
        "bytes": len(body),
        "result": result.model_dump(mode="json"),
        "cognee_result": str(result_cognee) if result_cognee else None,
    }


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


@app.get("/api/stats")
async def get_stats():
    facts = memory._load_facts()
    counts = Counter(fact.status for fact in facts)
    
    # Get active contradictions
    contradictions = await memory._active_contradictions(facts)
    contradictions = _dedupe_contradictions(contradictions)
    
    return {
        "activeFacts": counts[FactStatus.ACTIVE],
        "contradictions": len(contradictions),
        "decayedFacts": counts[FactStatus.DECAYED],
        "totalMemorySize": len(facts),
    }


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


@app.get("/api/resolutions", response_model=ResolutionsResponse)
async def list_resolutions() -> ResolutionsResponse:
    resolutions = memory.load_resolutions()
    resolutions.sort(key=lambda item: item.resolved_at, reverse=True)
    return ResolutionsResponse(resolutions=resolutions, total=len(resolutions))


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
    history_path = Path(memory.history_path)
    if history_path.exists():
        history_path.unlink()
    return {"reset": True}


@app.get("/api/graph", response_model=GraphResponse)
async def graph_data() -> GraphResponse:
    payload = visualize_graph(memory.metadata_path)
    return GraphResponse(nodes=payload["nodes"], edges=payload["edges"])


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

    ids = contradiction_id.split(":") if ":" in contradiction_id else []

    for fact in facts:
        is_in_group = fact.fact_id in ids if ids else fact.contradiction_group == contradiction_id
        if not is_in_group:
            continue
        fact.status = FactStatus.ACTIVE
        fact.contradiction_group = None
        changed = True

    if changed:
        memory._save_facts(facts)
        memory._append_resolution(
            ResolutionEvent(
                contradiction_id=contradiction_id,
                action="keep_both",
            )
        )
    return changed


def _load_chat_sessions() -> dict[str, dict]:
    if not CHAT_SESSIONS_PATH.exists():
        return {}
    return json.loads(CHAT_SESSIONS_PATH.read_text(encoding="utf-8"))


def _save_chat_sessions(sessions: dict[str, dict]) -> None:
    CHAT_SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHAT_SESSIONS_PATH.write_text(
        json.dumps(sessions, indent=2),
        encoding="utf-8",
    )


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
