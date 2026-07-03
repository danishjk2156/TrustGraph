"""Composite trust scoring for stored facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp

from trustgraph.models import FactStatus, TrustMetadata, TrustScore


@dataclass(frozen=True)
class TrustScorer:
    """Scores facts from recency, reinforcement, and consistency signals."""

    w_recency: float = 0.40
    w_reinforce: float = 0.35
    w_consistency: float = 0.25
    recency_lambda: float = 0.1
    reinforcement_alpha: float = 0.5

    def score(
        self,
        fact: TrustMetadata,
        all_facts: list[TrustMetadata] | None = None,
        now: datetime | None = None,
    ) -> TrustScore:
        now = now or datetime.utcnow()
        all_facts = all_facts or []

        days_since_stored = max((now - fact.timestamp).total_seconds() / 86400, 0.0)
        recency = exp(-self.recency_lambda * days_since_stored)
        reinforcement = 1 - exp(-self.reinforcement_alpha * fact.reinforcement_count)
        consistency = self._consistency_score(fact, all_facts)

        score = (
            self.w_recency * recency
            + self.w_reinforce * reinforcement
            + self.w_consistency * consistency
        )
        score = max(0.0, min(1.0, score))

        reasoning = (
            f"recency={recency:.2f}, reinforcement={reinforcement:.2f}, "
            f"consistency={consistency:.2f}"
        )
        return TrustScore(
            fact_id=fact.fact_id,
            score=score,
            recency_component=recency,
            reinforcement_component=reinforcement,
            consistency_component=consistency,
            reasoning=reasoning,
        )

    def _consistency_score(
        self, fact: TrustMetadata, all_facts: list[TrustMetadata]
    ) -> float:
        if fact.status == FactStatus.RESOLVED:
            return 0.0
        if fact.status in {FactStatus.CONTRADICTED, FactStatus.DECAYED}:
            return 0.5

        normalized_subject = _normalize_key(fact.subject)
        normalized_predicate = _normalize_key(fact.predicate)
        normalized_object = _normalize_key(fact.object_value)

        for candidate in all_facts:
            if candidate.fact_id == fact.fact_id:
                continue
            if candidate.status not in {FactStatus.ACTIVE, FactStatus.CONTRADICTED}:
                continue
            same_slot = (
                _normalize_key(candidate.subject) == normalized_subject
                and _normalize_key(candidate.predicate) == normalized_predicate
            )
            if same_slot and _normalize_key(candidate.object_value) != normalized_object:
                return 0.5

        return 1.0


def _normalize_key(value: str) -> str:
    return " ".join(value.strip().lower().split())
