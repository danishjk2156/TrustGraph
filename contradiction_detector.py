"""Contradiction detection for trust metadata."""

from __future__ import annotations

import json
import os
import re
from uuid import uuid4

from trustgraph.models import ContradictionPair, FactStatus, TrustMetadata
from trustgraph.trust_scorer import TrustScorer


async def detect_contradictions(
    new_fact: TrustMetadata,
    existing_facts: list[TrustMetadata],
    scorer: TrustScorer | None = None,
) -> list[ContradictionPair]:
    """
    Compare a new fact against existing facts.

    Exact contradictions are facts with the same normalized subject and predicate
    but a different object value. Semantic contradiction hooks can be added later
    without changing the public contract.
    """

    scorer = scorer or TrustScorer()
    contradictions: list[ContradictionPair] = []
    exact_ids: set[str] = set()

    for existing in existing_facts:
        if existing.status not in {FactStatus.ACTIVE, FactStatus.CONTRADICTED}:
            continue
        if not _same_slot(new_fact, existing):
            continue
        if _normalize(new_fact.object_value) == _normalize(existing.object_value):
            continue

        trust_new = scorer.score(new_fact, existing_facts).score
        trust_existing = scorer.score(existing, existing_facts + [new_fact]).score
        contradictions.append(
            ContradictionPair(
                fact_a=existing,
                fact_b=new_fact,
                trust_a=trust_existing,
                trust_b=trust_new,
                subject=new_fact.subject,
                predicate=new_fact.predicate,
                explanation=(
                    f"Both facts describe {new_fact.subject}.{new_fact.predicate} "
                    f"but disagree: {existing.object_value!r} vs "
                    f"{new_fact.object_value!r}."
                ),
            )
        )
        exact_ids.add(existing.fact_id)

    semantic = await _detect_semantic_contradictions(
        new_fact,
        [
            fact
            for fact in existing_facts
            if fact.fact_id not in exact_ids
            and fact.status in {FactStatus.ACTIVE, FactStatus.CONTRADICTED}
        ],
        scorer,
    )
    contradictions.extend(semantic)

    if contradictions and not new_fact.contradiction_group:
        new_fact.contradiction_group = str(uuid4())

    return contradictions


async def _detect_semantic_contradictions(
    new_fact: TrustMetadata,
    existing_facts: list[TrustMetadata],
    scorer: TrustScorer,
) -> list[ContradictionPair]:
    candidates = [fact for fact in existing_facts if _is_semantic_candidate(new_fact, fact)]
    if not candidates or not _model_name():
        return []

    contradictions: list[ContradictionPair] = []
    for existing in candidates:
        explanation = await _llm_contradiction_explanation(existing, new_fact)
        if not explanation:
            continue

        contradictions.append(
            ContradictionPair(
                fact_a=existing,
                fact_b=new_fact,
                trust_a=scorer.score(existing, existing_facts + [new_fact]).score,
                trust_b=scorer.score(new_fact, existing_facts).score,
                subject=new_fact.subject,
                predicate=new_fact.predicate,
                explanation=explanation,
            )
        )
    return contradictions


def _is_semantic_candidate(a: TrustMetadata, b: TrustMetadata) -> bool:
    if _normalize(a.subject) == _normalize(b.subject):
        return True
    a_tokens = set(_normalize(a.normalized_text).split())
    b_tokens = set(_normalize(b.normalized_text).split())
    if not a_tokens or not b_tokens:
        return False
    overlap = len(a_tokens & b_tokens) / max(len(a_tokens | b_tokens), 1)
    return overlap >= 0.35


async def _llm_contradiction_explanation(
    existing: TrustMetadata, new_fact: TrustMetadata
) -> str | None:
    try:
        from litellm import acompletion
    except Exception:
        return None

    try:
        response = await acompletion(
            model=_model_name(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Decide if two facts contradict. Return only JSON: "
                        "{\"contradicts\": true|false, \"explanation\": \"...\"}."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Fact A: {existing.normalized_text}\n"
                        f"Fact B: {new_fact.normalized_text}"
                    ),
                },
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        payload = json.loads(_json_object(content))
        if payload.get("contradicts") is True:
            return str(payload.get("explanation") or "The facts semantically conflict.")
    except Exception:
        return None
    return None


def _model_name() -> str | None:
    return os.getenv("LITELLM_MODEL") or os.getenv("LLM_MODEL") or os.getenv("MODEL")


def _json_object(content: str) -> str:
    match = re.search(r"\{.*\}", content or "", flags=re.DOTALL)
    if not match:
        raise ValueError("LLM response did not contain a JSON object")
    return match.group(0)


def _same_slot(a: TrustMetadata, b: TrustMetadata) -> bool:
    return _normalize(a.subject) == _normalize(b.subject) and _normalize(
        a.predicate
    ) == _normalize(b.predicate)


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())
