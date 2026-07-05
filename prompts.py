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

TRUST_AWARE_RESPONSE_PROMPT = """Answer the user using the supplied local memory context.
Prefer active local facts with the highest trust score.
When local memory and the user's claim disagree, state the discrepancy clearly and avoid presenting the contradicted item as certain.
Keep the answer concise.
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

