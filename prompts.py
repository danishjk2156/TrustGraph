"""Prompt templates for TrustGraph LLM calls."""

FACT_EXTRACTION_PROMPT = """Extract atomic factual claims from the user text.
Return only JSON with this shape:
{"facts":[{"subject":"...","predicate":"...","object_value":"...","normalized_text":"..."}]}
Use short canonical subjects and predicates. Preserve changed values exactly enough to answer later.
If one message contains multiple conflicting claims, return each claim as a separate fact.
If no facts exist, return {"facts":[]}.
"""

CONTRADICTION_DETECTION_PROMPT = """Decide whether two facts contradict.
Facts contradict when they make incompatible claims about the same subject, property, preference, deadline, count, date, status, or value.
Return only JSON with this shape:
{"contradicts": true|false, "explanation": "..."}.
"""

TRUST_AWARE_RESPONSE_PROMPT = """Answer the user using the supplied local memory and web search context.
Prefer active local facts with the highest trust score when they are compatible with current web results.
Use web search results to verify current or externally checkable claims.
When local memory, the user's claim, or search results disagree, state the discrepancy clearly and avoid presenting the contradicted item as certain.
Keep the answer concise.

End with a short "Web Verification" section:
- Say whether web results support, contradict, or do not verify the answer.
- Cite relevant web result titles and URLs when available.
- Mention unresolved local-memory contradictions when they affect the answer.
"""


def trust_context_block(items: list[dict]) -> str:
    """Render ranked facts into compact context for trust-aware answer generation."""

    if not items:
        return "No relevant trusted memories were found."

    lines = []
    for item in items:
        fact = item["fact"]
        score = item["trust_score"]
        lines.append(
            "- "
            f"{fact['normalized_text']} | trust={score['score']:.2f} | "
            f"status={fact['status']} | reinforced={fact['reinforcement_count']}x | "
            f"reason={score.get('reasoning', '')}"
        )
    return "\n".join(lines)


def web_context_block(items: list[dict[str, str]]) -> str:
    """Render web search results into compact context for verification."""

    if not items:
        return "No web search results were available."

    lines = []
    for item in items:
        lines.append(
            "- "
            f"{item.get('title', 'Untitled')} | {item.get('url', '')} | "
            f"{item.get('snippet', '')}"
        )
    return "\n".join(lines)
