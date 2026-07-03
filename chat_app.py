"""Streamlit chat UI for TrustGraph."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
import streamlit as st


API_BASE = "http://localhost:8000"


st.set_page_config(page_title="TrustGraph", page_icon="TG", layout="wide")

st.markdown(
    """
    <style>
    .trust-badge {
        display: inline-block;
        padding: 0.18rem 0.55rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        color: #111827;
    }
    .trust-high { background: #86efac; }
    .trust-medium { background: #fde68a; }
    .trust-low { background: #fca5a5; }
    .contradiction-card {
        border: 1px solid #f59e0b;
        border-left: 6px solid #f59e0b;
        background: #fffbeb;
        color: #111827;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.75rem 0;
    }
    .fact-row {
        border-bottom: 1px solid rgba(148, 163, 184, 0.35);
        padding: 0.45rem 0;
    }
    .muted { color: #64748b; font-size: 0.86rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str) -> dict[str, Any]:
    response = requests.get(f"{API_BASE}{path}", timeout=15)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.post(f"{API_BASE}{path}", json=payload or {}, timeout=30)
    response.raise_for_status()
    return response.json()


def trust_class(score: float) -> str:
    if score >= 0.8:
        return "trust-high"
    if score >= 0.5:
        return "trust-medium"
    return "trust-low"


def trust_label(score: float) -> str:
    if score >= 0.8:
        return f"High confidence {score:.2f}"
    if score >= 0.5:
        return f"Medium confidence {score:.2f}"
    return f"Low confidence {score:.2f}"


def badge(score: float) -> str:
    return (
        f'<span class="trust-badge {trust_class(score)}">'
        f"{trust_label(score)}</span>"
    )


def fact_text(fact: dict[str, Any]) -> str:
    return fact.get("normalized_text") or fact.get("original_text") or "Untitled fact"


def stored_when(fact: dict[str, Any]) -> str:
    raw = fact.get("timestamp")
    if not raw:
        return "unknown"
    try:
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - timestamp
    except ValueError:
        return raw

    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def render_trust_breakdown(score: dict[str, Any]) -> None:
    st.markdown(
        f"""
        Recency: `{score["recency_component"]:.2f}`
        Reinforcement: `{score["reinforcement_component"]:.2f}`
        Consistency: `{score["consistency_component"]:.2f}`

        Total: `{score["score"]:.2f}`
        """
    )


def render_contradictions() -> None:
    try:
        payload = api_get("/api/contradictions")
    except requests.RequestException as exc:
        st.warning(f"Could not load contradictions: {exc}")
        return

    contradictions = payload.get("contradictions", [])
    if not contradictions:
        return

    st.markdown("### Contradictions")
    for item in contradictions:
        fact_a = item["fact_a"]
        fact_b = item["fact_b"]
        contradiction_id = item["contradiction_id"]
        st.markdown(
            f"""
            <div class="contradiction-card">
                <strong>CONTRADICTION DETECTED</strong><br>
                "{fact_text(fact_a)}" (trust: {item["trust_a"]:.2f}, stored {stored_when(fact_a)})<br>
                "{fact_text(fact_b)}" (trust: {item["trust_b"]:.2f}, stored {stored_when(fact_b)})
            </div>
            """,
            unsafe_allow_html=True,
        )
        cols = st.columns(3)
        if cols[0].button("Keep first", key=f"keep-a-{contradiction_id}"):
            api_post(
                "/api/resolve",
                {
                    "contradiction_id": contradiction_id,
                    "winner_id": fact_a["fact_id"],
                    "action": "keep_winner",
                },
            )
            st.rerun()
        if cols[1].button("Keep second", key=f"keep-b-{contradiction_id}"):
            api_post(
                "/api/resolve",
                {
                    "contradiction_id": contradiction_id,
                    "winner_id": fact_b["fact_id"],
                    "action": "keep_winner",
                },
            )
            st.rerun()
        if cols[2].button("Keep both", key=f"keep-both-{contradiction_id}"):
            api_post(
                "/api/resolve",
                {"contradiction_id": contradiction_id, "action": "keep_both"},
            )
            st.rerun()


def render_sidebar() -> None:
    st.sidebar.title("Memory Inspector")

    try:
        facts_payload = api_get("/api/facts")
    except requests.RequestException as exc:
        st.sidebar.error(f"Backend unavailable: {exc}")
        st.sidebar.caption("Start with: uvicorn trustgraph.api:app --reload")
        return

    st.sidebar.metric("Active contradictions", api_get("/api/contradictions")["total"])
    st.sidebar.metric("Decayed facts", facts_payload["decayed_count"])

    if st.sidebar.button("Run decay check", use_container_width=True):
        api_post("/api/decay")
        st.rerun()

    if st.sidebar.button("Reset memory", use_container_width=True):
        api_post("/api/reset")
        st.session_state.messages = []
        st.rerun()

    with st.sidebar.expander("All stored facts", expanded=True):
        for item in facts_payload["facts"]:
            fact = item["fact"]
            score = item["trust_score"]
            st.markdown(
                f"""
                <div class="fact-row">
                    <strong>{fact_text(fact)}</strong><br>
                    {badge(score["score"])}<br>
                    <span class="muted">{fact["status"]} · {stored_when(fact)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("Trust score breakdown"):
                render_trust_breakdown(score)
                if st.button("Reinforce", key=f"reinforce-{fact['fact_id']}"):
                    api_post("/api/reinforce", {"fact_id": fact["fact_id"]})
                    st.rerun()

    with st.sidebar.expander("Timeline"):
        timeline = sorted(
            facts_payload["facts"],
            key=lambda item: item["fact"].get("timestamp", ""),
            reverse=True,
        )
        for item in timeline:
            fact = item["fact"]
            st.caption(f"{stored_when(fact)} - {fact_text(fact)}")


def render_chat() -> None:
    st.title("TrustGraph")
    render_contradictions()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    prompt = st.chat_input("Store or ask about a fact")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        store_result = api_post("/api/store", {"text": prompt, "source": "chat"})
        query_result = api_post("/api/query", {"query_text": prompt})
    except requests.RequestException as exc:
        answer = f"Backend request failed: `{exc}`"
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.error(answer)
        return

    ranked = query_result.get("ranked_facts", [])
    contradictions = store_result.get("contradictions", [])
    if ranked:
        top = ranked[0]
        score = top["trust_score"]["score"]
        lines = [
            f"{badge(score)}",
            "",
            "Most trusted matching memory:",
            f"**{fact_text(top['fact'])}**",
        ]
        if len(ranked) > 1:
            lines.append("")
            lines.append("Other matching facts:")
            lines.extend(
                f"- {fact_text(item['fact'])} ({item['trust_score']['score']:.2f})"
                for item in ranked[1:4]
            )
    else:
        lines = [badge(0.0), "", "No facts are stored yet."]

    if contradictions:
        lines.append("")
        lines.append("A contradiction was detected. Use the resolver above.")

    answer = "\n".join(lines)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer, unsafe_allow_html=True)


render_sidebar()
render_chat()
