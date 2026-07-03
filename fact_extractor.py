"""Extract structured facts from free text."""

from __future__ import annotations

import json
import re
from typing import Any


EXTRACTION_PROMPT = """Extract atomic factual claims from the user text.
Return only JSON with this shape:
{"facts":[{"subject":"...","predicate":"...","object_value":"...","normalized_text":"..."}]}
Use short canonical subjects and predicates. If no facts exist, return {"facts":[]}.
"""


async def extract_facts(user_text: str) -> list[dict[str, str]]:
    """
    Extract structured facts from free-form text.

    The function prefers LiteLLM so it can use the same provider configuration as
    Cognee deployments. If LiteLLM or provider configuration is unavailable, it
    falls back to a deterministic extractor that handles common assistant-memory
    statements.
    """

    facts = await _extract_with_litellm(user_text)
    if facts:
        return facts
    return _extract_with_heuristics(user_text)


async def _extract_with_litellm(user_text: str) -> list[dict[str, str]]:
    model = _model_name()
    if not model:
        return []

    try:
        from litellm import acompletion
    except Exception:
        return []

    try:
        response = await acompletion(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": user_text},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        payload = json.loads(_json_object(content))
        return [_coerce_fact(item, user_text) for item in payload.get("facts", [])]
    except Exception:
        return []


def _model_name() -> str:
    import os

    return (
        os.getenv("LITELLM_MODEL")
        or os.getenv("LLM_MODEL")
        or os.getenv("MODEL")
    )


def _json_object(content: str) -> str:
    match = re.search(r"\{.*\}", content or "", flags=re.DOTALL)
    if not match:
        raise ValueError("LLM response did not contain a JSON object")
    return match.group(0)


def _coerce_fact(item: dict[str, Any], original_text: str) -> dict[str, str]:
    subject = str(item.get("subject", "")).strip()
    predicate = str(item.get("predicate", "")).strip()
    object_value = str(item.get("object_value") or item.get("object") or "").strip()
    normalized_text = str(item.get("normalized_text") or "").strip()

    if not normalized_text and subject and predicate and object_value:
        normalized_text = f"{subject} {predicate} {object_value}"
    if not subject or not predicate or not object_value:
        raise ValueError(f"Incomplete fact extracted from: {original_text}")

    return {
        "subject": subject,
        "predicate": predicate,
        "object_value": object_value,
        "normalized_text": normalized_text,
    }


def _extract_with_heuristics(user_text: str) -> list[dict[str, str]]:
    text = user_text.strip()
    if not text:
        return []

    patterns = [
        r"^(?:my|the)?\s*(?P<subject>[\w\s-]+?)\s+(?P<predicate>is|are|was|were)\s+(?P<object>.+)$",
        r"^(?P<subject>[\w\s-]+?)\s+(?P<predicate>equals|=|expires|costs|deadline is)\s+(?P<object>.+)$",
        r"^(?P<subject>[\w\s-]+?)\s+(?P<predicate>has|have)\s+(?P<object>.+)$",
    ]

    for pattern in patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        subject = _clean(match.group("subject"))
        predicate = _clean(match.group("predicate").replace(" ", "_"))
        object_value = _clean(match.group("object").rstrip("."))
        if subject and predicate and object_value:
            return [
                {
                    "subject": subject,
                    "predicate": predicate,
                    "object_value": object_value,
                    "normalized_text": f"{subject} {predicate} {object_value}",
                }
            ]

    return [
        {
            "subject": "statement",
            "predicate": "says",
            "object_value": text.rstrip("."),
            "normalized_text": text.rstrip("."),
        }
    ]


def _clean(value: str) -> str:
    return " ".join(value.strip(" .,:;").lower().split())
