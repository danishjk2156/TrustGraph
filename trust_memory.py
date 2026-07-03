"""Trust-aware memory layer that wraps Cognee."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from trustgraph.contradiction_detector import detect_contradictions
from trustgraph.fact_extractor import extract_facts
from trustgraph.models import (
    ContradictionPair,
    FactStatus,
    QueryResult,
    RankedFact,
    StoreResult,
    TrustMetadata,
)
from trustgraph.trust_scorer import TrustScorer


class TrustMemory:
    """Trust-aware memory layer wrapping Cognee."""

    def __init__(
        self,
        metadata_path: str | Path = ".trustgraph/facts.json",
        scorer: TrustScorer | None = None,
        decay_threshold: float = 0.15,
    ) -> None:
        self.metadata_path = Path(metadata_path)
        self.scorer = scorer or TrustScorer()
        self.decay_threshold = decay_threshold

    async def store(
        self,
        text: str,
        source: str = "user",
        importance_weight: float = 1.0,
        node_set: str = "trust_facts",
    ) -> StoreResult:
        """
        Extract facts, detect contradictions, store through Cognee, and persist
        trust metadata locally.
        """

        existing_facts = self._load_facts()
        extracted = await extract_facts(text)
        stored_facts: list[TrustMetadata] = []
        contradictions: list[ContradictionPair] = []

        for item in extracted:
            duplicate = self._find_duplicate(existing_facts, item)
            if duplicate:
                duplicate.reinforcement_count += 1
                stored_facts.append(duplicate)
                await self._improve(feedback_alpha=0.1)
                continue

            fact = TrustMetadata(
                fact_id=str(uuid4()),
                original_text=text,
                normalized_text=item["normalized_text"],
                subject=item["subject"],
                predicate=item["predicate"],
                object_value=item["object_value"],
                source=source,
            )
            found = await detect_contradictions(fact, existing_facts, self.scorer)
            if found:
                fact.status = FactStatus.CONTRADICTED
                for pair in found:
                    pair.fact_a.status = FactStatus.CONTRADICTED
                    pair.fact_a.contradiction_group = (
                        pair.fact_a.contradiction_group
                        or fact.contradiction_group
                        or str(uuid4())
                    )
                    pair.fact_b.contradiction_group = pair.fact_a.contradiction_group
                contradictions.extend(found)

            existing_facts.append(fact)
            stored_facts.append(fact)
            fact.cognee_data_id = await self._remember(fact, importance_weight, node_set)

        self._save_facts(existing_facts)
        return StoreResult(stored_facts=stored_facts, contradictions=contradictions)

    async def query(self, query_text: str, feedback_influence: float = 0.5) -> QueryResult:
        """
        Recall relevant Cognee memories using feedback_influence and only_context,
        then return trust-ranked local facts.
        """

        facts = self._load_facts()
        raw_results = await self._recall(query_text, feedback_influence=feedback_influence, only_context=True)

        cognee_fact_ids = set()
        import re
        fact_id_pattern = re.compile(r"trust_fact_id=([a-f0-9\-]+)")

        for result in raw_results:
            text = getattr(result, "text", "")
            if not text and hasattr(result, "content"):
                text = result.content
            if text:
                match = fact_id_pattern.search(text)
                if match:
                    cognee_fact_ids.add(match.group(1))

        relevant_local = self._filter_relevant(query_text, facts)
        relevant_ids = cognee_fact_ids.union({f.fact_id for f in relevant_local})
        relevant = [f for f in facts if f.fact_id in relevant_ids]

        if not relevant:
            relevant = [f for f in facts if f.status in {FactStatus.ACTIVE, FactStatus.CONTRADICTED}]

        ranked = [
            RankedFact(
                fact=fact,
                trust_score=self.scorer.score(fact, facts),
            )
            for fact in relevant
        ]
        ranked.sort(key=lambda item: item.trust_score.score, reverse=True)

        contradictions = await self._active_contradictions(relevant or facts)
        return QueryResult(
            query_text=query_text,
            ranked_facts=ranked,
            contradictions=contradictions,
            raw_results=list(raw_results or []),
        )

    async def reinforce(self, fact_id: str, feedback_alpha: float = 0.1) -> None:
        """Bump reinforcement count for a fact and ask Cognee to improve with feedback_alpha."""

        facts = self._load_facts()
        for fact in facts:
            if fact.fact_id == fact_id:
                fact.reinforcement_count += 1
                self._save_facts(facts)
                await self._improve(feedback_alpha=feedback_alpha)
                return
        raise ValueError(f"Unknown fact_id: {fact_id}")

    async def resolve_contradiction(
        self, contradiction_id: str, winner_id: str, feedback_alpha: float = 0.1
    ) -> None:
        """
        Resolve a contradiction group by keeping the winner and forgetting losers.
        """

        facts = self._load_facts()
        group = [
            fact for fact in facts if fact.contradiction_group == contradiction_id
        ]
        if not group:
            raise ValueError(f"Unknown contradiction_id: {contradiction_id}")

        winner_seen = False
        remaining: list[TrustMetadata] = []
        for fact in facts:
            if fact.contradiction_group != contradiction_id:
                remaining.append(fact)
                continue
            if fact.fact_id == winner_id:
                fact.status = FactStatus.ACTIVE
                fact.reinforcement_count += 1
                fact.contradiction_group = None
                remaining.append(fact)
                winner_seen = True
                await self._improve(feedback_alpha=feedback_alpha)
            else:
                fact.status = FactStatus.RESOLVED
                await self._forget(fact)

        if not winner_seen:
            raise ValueError(f"winner_id is not in contradiction group: {winner_id}")
        self._save_facts(remaining)

    async def decay_check(self) -> list[str]:
        """
        Mark active facts below the decay threshold as DECAYED.
        """

        facts = self._load_facts()
        decayed: list[str] = []
        for fact in facts:
            score = self.scorer.score(fact, facts)
            if fact.status == FactStatus.ACTIVE and score.score < self.decay_threshold:
                fact.status = FactStatus.DECAYED
                decayed.append(fact.fact_id)
        self._save_facts(facts)
        return decayed

    def _load_facts(self) -> list[TrustMetadata]:
        if not self.metadata_path.exists():
            return []
        payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        return [TrustMetadata.model_validate(item) for item in payload]

    def _save_facts(self, facts: list[TrustMetadata]) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [fact.model_dump(mode="json") for fact in facts]
        self.metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _find_duplicate(
        self, facts: list[TrustMetadata], item: dict[str, str]
    ) -> TrustMetadata | None:
        for fact in facts:
            if (
                _normalize(fact.subject) == _normalize(item["subject"])
                and _normalize(fact.predicate) == _normalize(item["predicate"])
                and _normalize(fact.object_value) == _normalize(item["object_value"])
            ):
                return fact
        return None

    def _filter_relevant(
        self, query_text: str, facts: list[TrustMetadata]
    ) -> list[TrustMetadata]:
        terms = set(_normalize(query_text).split())
        if not terms:
            return facts

        relevant = []
        for fact in facts:
            haystack = _normalize(
                " ".join(
                    [
                        fact.subject,
                        fact.predicate,
                        fact.object_value,
                        fact.normalized_text,
                    ]
                )
            )
            if any(term in haystack for term in terms):
                relevant.append(fact)
        return relevant or facts

    async def _active_contradictions(
        self, facts: list[TrustMetadata]
    ) -> list[ContradictionPair]:
        contradictions: list[ContradictionPair] = []
        for index, fact in enumerate(facts):
            contradictions.extend(
                await detect_contradictions(fact, facts[:index] + facts[index + 1 :])
            )
        return contradictions

    async def _remember(
        self,
        fact: TrustMetadata,
        importance_weight: float = 1.0,
        node_set: str = "trust_facts",
    ) -> str | None:
        try:
            import cognee

            result = await cognee.remember(
                f"{fact.normalized_text} "
                f"[trust_fact_id={fact.fact_id}; source={fact.source}]",
                importance_weight=importance_weight,
                node_set=[node_set],
            )
            if result and result.items:
                return result.items[0].get("id")
        except Exception:
            pass
        return None

    async def _recall(
        self,
        query_text: str,
        feedback_influence: float = 0.5,
        only_context: bool = True,
    ):
        try:
            import cognee

            return await cognee.recall(
                query_text=query_text,
                feedback_influence=feedback_influence,
                only_context=only_context,
            )
        except Exception:
            return []

    async def _improve(self, feedback_alpha: float = 0.1) -> None:
        try:
            import cognee

            await cognee.improve(feedback_alpha=feedback_alpha)
        except Exception:
            return

    async def _forget(self, fact: TrustMetadata) -> None:
        if not fact.cognee_data_id:
            return
        try:
            import cognee
            from uuid import UUID

            await cognee.forget(
                data_id=UUID(fact.cognee_data_id),
                dataset="main_dataset",
                memory_only=True,
            )
        except Exception:
            return


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())
