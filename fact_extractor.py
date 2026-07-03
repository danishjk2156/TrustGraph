"""Extract structured facts from free text."""

from __future__ import annotations

import json
import re
from typing import Any

from trustgraph.prompts import FACT_EXTRACTION_PROMPT


async def extract_facts(user_text: str) -> list[dict[str, str]]:
    """
    Extract structured facts from free-form text.

    The function prefers LiteLLM so it can use the same provider configuration as
    Cognee deployments. If LiteLLM or provider configuration is unavailable, it
    falls back to a deterministic extractor that handles common assistant-memory
    statements.
    """

    if _looks_like_question(user_text):
        return []

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
                {"role": "system", "content": FACT_EXTRACTION_PROMPT},
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

    model = (
        os.getenv("LITELLM_MODEL")
        or os.getenv("LLM_MODEL")
        or os.getenv("MODEL")
    )
    if model and "groq" in model.lower() and not os.getenv("GROQ_API_KEY"):
        if os.getenv("LLM_API_KEY"):
            os.environ["GROQ_API_KEY"] = os.getenv("LLM_API_KEY")
    return model


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
    if _looks_like_question(text):
        return []

    facts = []
    last_subject: str | None = None
    for clause in _claim_clauses(text):
        fact = _extract_single_clause(clause)
        if fact:
            if fact["subject"] in {"it", "its", "it's", "that"} and last_subject:
                fact["subject"] = last_subject
                fact["normalized_text"] = (
                    f"{fact['subject']} {fact['predicate']} {fact['object_value']}"
                )
            last_subject = fact["subject"]
            facts.append(fact)
    if facts:
        return facts

    return [
        {
            "subject": "statement",
            "predicate": "says",
            "object_value": text.rstrip("."),
            "normalized_text": text.rstrip("."),
        }
    ]


def _claim_clauses(text: str) -> list[str]:
    text = re.sub(
        r"\b(?:actually|correction|update|instead|now)\b[:,]?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    parts = re.split(
        r"\s+(?:but|however|although|though|yet|while|and also)\s+",
        text,
        flags=re.IGNORECASE,
    )
    return [part.strip(" .,:;") for part in parts if part.strip(" .,:;")]


def _looks_like_question(text: str) -> bool:
    lowered = text.strip().lower()
    question_starts = (
        "what ",
        "when ",
        "where ",
        "who ",
        "why ",
        "how ",
        "which ",
        "do ",
        "does ",
        "did ",
        "is ",
        "are ",
        "can ",
        "could ",
        "should ",
    )
    return lowered.endswith("?") or lowered.startswith(question_starts)


def _extract_single_clause(text: str) -> dict[str, str] | None:
    patterns = [
        r"^(?P<subject>it|that|this)\s*(?P<predicate>'s|is)\s+(?P<object>.+)$",
        r"^(?:my|the)?\s*(?P<subject>[\w\s-]+?)\s+(?P<predicate>is|are|was|were)\s+(?P<object>.+)$",
        r"^(?P<subject>[\w\s-]+?)\s+(?P<predicate>equals|=|expires|costs|deadline is)\s+(?P<object>.+)$",
        r"^(?P<subject>[\w\s-]+?)\s+(?P<predicate>has|have)\s+(?P<object>.+)$",
    ]

    for pattern in patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        subject = _canonical_subject(match.group("subject"))
        predicate = _canonical_predicate(match.group("predicate"))
        object_value = _clean(match.group("object").rstrip("."))
        if subject and predicate and object_value:
            return {
                "subject": subject,
                "predicate": predicate,
                "object_value": object_value,
                "normalized_text": f"{subject} {predicate} {object_value}",
            }
    return None


def _canonical_subject(value: str) -> str:
    cleaned = _clean(value)
    cleaned = re.sub(r"^(?:my|the|our|a|an)\s+", "", cleaned)
    if "deadline" in cleaned or "due date" in cleaned:
        return "deadline"
    if "team" in cleaned and ("member" in cleaned or "size" in cleaned):
        return "team"
    return cleaned


def _canonical_predicate(value: str) -> str:
    cleaned = _clean(value.replace(" ", "_"))
    if cleaned == "'s":
        return "is"
    if cleaned == "deadline_is":
        return "is"
    if cleaned in {"has", "have"}:
        return "has"
    return cleaned


def _clean(value: str) -> str:
    return " ".join(value.strip(" .,:;").lower().split())
