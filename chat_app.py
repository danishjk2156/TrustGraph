"""Streamlit chat UI for TrustGraph."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components


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
        border-radius: 8px;
        margin: 0.75rem 0;
    }
    .fact-row, .graph-node {
        border-bottom: 1px solid rgba(148, 163, 184, 0.35);
        padding: 0.5rem 0;
        transition: transform 120ms ease, border-color 120ms ease;
    }
    .graph-node {
        border: 1px solid rgba(148, 163, 184, 0.35);
        border-radius: 8px;
        margin: 0.35rem 0;
        padding: 0.55rem;
    }
    .graph-node:hover {
        transform: translateY(-1px);
        border-color: #22c55e;
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


def looks_like_question(text: str) -> bool:
    normalized = " ".join(text.strip().lower().split())
    question_starts = (
        "what ",
        "when ",
        "where ",
        "who ",
        "why ",
        "how ",
        "which ",
        "is ",
        "are ",
        "can ",
        "could ",
        "do ",
        "does ",
        "did ",
        "should ",
        "will ",
        "latest ",
        "current ",
        "today ",
    )
    return text.strip().endswith("?") or normalized.startswith(question_starts)


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
            with st.spinner("Resolving contradiction..."):
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
            with st.spinner("Resolving contradiction..."):
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
            with st.spinner("Keeping both facts..."):
                api_post(
                    "/api/resolve",
                    {"contradiction_id": contradiction_id, "action": "keep_both"},
                )
            st.rerun()


def render_fact_list(facts_payload: dict[str, Any]) -> None:
    for item in facts_payload["facts"]:
        fact = item["fact"]
        score = item["trust_score"]
        st.markdown(
            f"""
            <div class="fact-row">
                <strong>{fact_text(fact)}</strong><br>
                {badge(score["score"])}<br>
                <span class="muted">{fact["status"]} - {stored_when(fact)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Trust score breakdown"):
            render_trust_breakdown(score)
            if st.button("Reinforce", key=f"reinforce-{fact['fact_id']}"):
                with st.spinner("Reinforcing..."):
                    api_post("/api/reinforce", {"fact_id": fact["fact_id"]})
                st.rerun()


def render_graph_view() -> None:
    try:
        graph = api_get("/api/graph")
    except requests.RequestException as exc:
        st.warning(f"Could not load graph: {exc}")
        return

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    st.caption(f"{len(nodes)} nodes / {len(edges)} edges")
    for node in nodes:
        if node.get("node_type") != "fact":
            continue
        score = float(node.get("trust") or 0)
        st.markdown(
            f"""
            <div class="graph-node">
                <strong>{node.get("label", "Fact")}</strong><br>
                {badge(score)}<br>
                <span class="muted">{node.get("status")} - reinforced {node.get("reinforcement_count", 0)}x</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_resolution_history(facts_payload: dict[str, Any]) -> None:
    try:
        payload = api_get("/api/resolutions")
    except requests.RequestException as exc:
        st.warning(f"Could not load resolution history: {exc}")
        payload = {"resolutions": []}

    resolutions = payload.get("resolutions", [])
    if resolutions:
        for item in resolutions[:10]:
            winner = item.get("winner_text") or "Both facts kept"
            losers = ", ".join(item.get("loser_texts") or [])
            st.markdown(f"**{item['action']}** - {winner}")
            if losers:
                st.caption(f"Forgotten: {losers}")
    else:
        st.caption("No resolved contradictions yet.")

    st.markdown("#### Timeline")
    timeline = sorted(
        facts_payload["facts"],
        key=lambda item: item["fact"].get("timestamp", ""),
        reverse=True,
    )
    for item in timeline:
        fact = item["fact"]
        st.caption(f"{stored_when(fact)} - {fact_text(fact)}")


def render_sidebar() -> None:
    st.sidebar.title("Memory Inspector")

    try:
        with st.sidebar:
            with st.spinner("Loading memory..."):
                facts_payload = api_get("/api/facts")
                contradictions_payload = api_get("/api/contradictions")
    except requests.RequestException as exc:
        st.sidebar.error(f"Backend unavailable: {exc}")
        st.sidebar.caption("Start with: uvicorn trustgraph.api:app --reload")
        return

    st.sidebar.metric("Active contradictions", contradictions_payload["total"])
    st.sidebar.metric("Decayed facts", facts_payload["decayed_count"])

    if st.sidebar.button("Run decay check", use_container_width=True):
        with st.spinner("Checking decay..."):
            api_post("/api/decay")
        st.rerun()

    if st.sidebar.button("Reset memory", use_container_width=True):
        with st.spinner("Resetting memory..."):
            api_post("/api/reset")
        st.session_state.messages = []
        st.rerun()

    tab_facts, tab_graph, tab_history = st.sidebar.tabs(["Facts", "Graph", "History"])
    with tab_facts:
        render_fact_list(facts_payload)
    with tab_graph:
        render_graph_view()
    with tab_history:
        render_resolution_history(facts_payload)


def response_lines(store_result: dict[str, Any], query_result: dict[str, Any]) -> list[str]:
    ranked = query_result.get("ranked_facts", [])
    store_result = store_result or {}
    contradictions = store_result.get("contradictions", [])
    reinforced = store_result.get("reinforced_facts", [])

    if contradictions:
        lines = ["**CONTRADICTION DETECTED**"]
        for item in contradictions[:3]:
            lines.append(
                f"- \"{fact_text(item['fact_a'])}\" (trust: {item['trust_a']:.2f})"
            )
            lines.append(
                f"- \"{fact_text(item['fact_b'])}\" (trust: {item['trust_b']:.2f})"
            )
        lines.append("")
        lines.append("Choose the correct memory in the resolver above.")
        return lines

    if reinforced:
        top = reinforced[0]
        score = next(
            (
                item["trust_score"]["score"]
                for item in ranked
                if item["fact"]["fact_id"] == top["fact_id"]
            ),
            0.0,
        )
        return [f"Reinforced. Trust: {score:.2f}", f"**{fact_text(top)}**"]

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

    answer_text = query_result.get("answer_text")
    if answer_text:
        lines.extend(["", answer_text])
    return lines


def generate_vis_html(nodes: list[dict], edges: list[dict]) -> str:
    vis_nodes = []
    for n in nodes:
        node_type = n.get("node_type")
        label = n.get("label", "")
        display_label = label if len(label) < 30 else label[:27] + "..."
        
        # Color configuration matching styling
        if node_type == "subject":
            color = {"background": "#3b82f6", "border": "#1d4ed8"}  # Blue
            font = {"color": "#ffffff"}
            shape = "dot"
            size = 15
        elif node_type == "contradiction":
            color = {"background": "#f87171", "border": "#dc2626"}  # Red
            font = {"color": "#ffffff"}
            shape = "diamond"
            size = 20
        else: # fact
            trust = n.get("trust", 1.0)
            if trust >= 0.8:
                color = {"background": "#86efac", "border": "#22c55e"}  # Green
            elif trust >= 0.5:
                color = {"background": "#fde68a", "border": "#d97706"}  # Yellow
            else:
                color = {"background": "#fca5a5", "border": "#dc2626"}  # Red
            font = {"color": "#111827"}
            shape = "box"
            size = 12
            
        vis_nodes.append({
            "id": n["id"],
            "label": display_label,
            "title": f"Type: {node_type}<br>Label: {label}<br>Trust: {n.get('trust', 0.0):.2f}<br>Status: {n.get('status')}",
            "color": color,
            "font": font,
            "shape": shape,
            "size": size
        })
        
    vis_edges = []
    for e in edges:
        color = "#94a3b8"  # Slate
        if e.get("relation") == "contradicts":
            color = "#ef4444"  # Red
            
        vis_edges.append({
            "from": e["source"],
            "to": e["target"],
            "label": e.get("relation", ""),
            "color": {"color": color, "highlight": "#3b82f6"},
            "arrows": "to",
            "font": {"size": 10, "align": "top"}
        })
        
    nodes_js = json.dumps(vis_nodes)
    edges_js = json.dumps(vis_edges)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            #mynetwork {{
                width: 100%;
                height: 600px;
                border: 1px solid rgba(148, 163, 184, 0.3);
                background-color: #f8fafc;
                border-radius: 8px;
            }}
            body {{
                margin: 0;
                padding: 0;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }}
        </style>
    </head>
    <body>
    <div id="mynetwork"></div>
    <script type="text/javascript">
        var nodes = new vis.DataSet({nodes_js});
        var edges = new vis.DataSet({edges_js});
        var container = document.getElementById('mynetwork');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            nodes: {{
                font: {{
                    size: 12
                }}
            }},
            edges: {{
                width: 2,
                font: {{
                    strokeWidth: 0,
                    color: '#475569'
                }}
            }},
            physics: {{
                barnesHut: {{
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 95,
                    springConstant: 0.04,
                    damping: 0.09,
                    avoidOverlap: 0.1
                }}
            }}
        }};
        var network = new vis.Network(container, data, options);
    </script>
    </body>
    </html>
    """
    return html


def render_interactive_graph() -> None:
    st.subheader("Memory Knowledge Graph (Vis.js)")
    st.caption("Interactive force-directed visualization. Drag nodes to reposition, hover for details.")
    
    try:
        graph = api_get("/api/graph")
    except requests.RequestException as exc:
        st.warning(f"Could not load graph: {exc}")
        return
        
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    
    if not nodes:
        st.info("No nodes in the graph yet. Try storing some facts first.")
        return
        
    html_content = generate_vis_html(nodes, edges)
    components.html(html_content, height=620, scrolling=False)


def render_chat() -> None:
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

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            with st.spinner("Checking memory and trust..."):
                store_result = {}
                if not looks_like_question(prompt):
                    store_result = api_post("/api/store", {"text": prompt, "source": "chat"})
                query_result = api_post("/api/query", {"query_text": prompt})
        except requests.RequestException as exc:
            answer = f"Backend request failed: `{exc}`"
            st.session_state.messages.append({"role": "assistant", "content": answer})
            placeholder.error(answer)
            return

        answer = "\n".join(response_lines(store_result, query_result))
        st.session_state.messages.append({"role": "assistant", "content": answer})
        placeholder.markdown(answer, unsafe_allow_html=True)


render_sidebar()
st.title("TrustGraph")

tab_chat, tab_vis = st.tabs(["💬 Chat & Resolver", "📊 Interactive Memory Graph"])
with tab_chat:
    render_chat()
with tab_vis:
    render_interactive_graph()
