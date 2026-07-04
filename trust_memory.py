"""Trust-aware memory layer that wraps Cognee."""

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
    ResolutionEvent,
    StoreResult,
    TrustMetadata,
)
from trustgraph.prompts import (
    TRUST_AWARE_RESPONSE_PROMPT,
    trust_context_block,
    web_context_block,
)
from trustgraph.trust_scorer import TrustScorer
from trustgraph.web_search import search_web


class TrustMemory:
    """Trust-aware memory layer wrapping Cognee."""

    def __init__(
        self,
        metadata_path: str | Path = "trustgraph/data/facts.json",
        scorer: TrustScorer | None = None,
        decay_threshold: float = 0.15,
    ) -> None:
        self.metadata_path = Path(metadata_path)
        self.history_path = self.metadata_path.with_name("resolutions.json")
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
        reinforced_facts: list[TrustMetadata] = []
        contradictions: list[ContradictionPair] = []

        for item in extracted:
            duplicate = self._find_duplicate(existing_facts, item)
            if duplicate:
                was_decayed = (duplicate.status == FactStatus.DECAYED)
                duplicate.reinforcement_count += 1
                if was_decayed:
                    duplicate.status = FactStatus.ACTIVE
                stored_facts.append(duplicate)
                reinforced_facts.append(duplicate)
                if was_decayed:
                    initial_trust = self.scorer.score(duplicate, existing_facts).score
                    duplicate.cognee_data_id = await self._remember(
                        duplicate,
                        importance_weight=min(max(importance_weight * initial_trust, 0.0), 10.0),
                        node_set=node_set,
                    )
                else:
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
                group_id = self._merge_contradiction_groups(facts=existing_facts, pairs=found, new_fact=fact)
                for pair in found:
                    pair.fact_a.status = FactStatus.CONTRADICTED
                    pair.fact_a.contradiction_group = group_id
                    pair.fact_b.contradiction_group = group_id
                contradictions.extend(found)

            existing_facts.append(fact)
            stored_facts.append(fact)
            initial_trust = self.scorer.score(fact, existing_facts).score
            fact.cognee_data_id = await self._remember(
                fact,
                importance_weight=min(max(importance_weight * initial_trust, 0.0), 10.0),
                node_set=node_set,
            )

        self._save_facts(existing_facts)
        return StoreResult(
            stored_facts=stored_facts,
            reinforced_facts=reinforced_facts,
            contradictions=contradictions,
        )

    async def query(
        self,
        query_text: str,
        feedback_influence: float = 0.5,
        session_id: str | None = None,
    ) -> QueryResult:
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
        relevant = [
            f
            for f in facts
            if f.fact_id in relevant_ids
            and f.status in {FactStatus.ACTIVE, FactStatus.CONTRADICTED}
        ]

        ranked = [
            RankedFact(
                fact=fact,
                trust_score=self.scorer.score(fact, facts),
            )
            for fact in relevant
        ]
        ranked.sort(key=lambda item: item.trust_score.score, reverse=True)

        contradictions = await self._active_contradictions(relevant or facts)
        web_results: list[dict[str, str]] = []
        should_use_web = _should_search_web(query_text)
        if should_use_web:
            web_results = await search_web(query_text)

        answer_text = await self._generate_answer(
            query_text,
            ranked,
            contradictions,
            web_results,
            session_id=session_id,
        )
        if should_use_web and web_results and answer_text:
            await self._store_answer_memory(
                query_text=query_text,
                answer_text=answer_text,
                web_results=web_results,
            )

        return QueryResult(
            query_text=query_text,
            ranked_facts=ranked,
            answer_text=answer_text,
            web_results=web_results,
            contradictions=contradictions,
            raw_results=list(raw_results or []),
        )

    async def reinforce(self, fact_id: str, feedback_alpha: float = 0.1) -> None:
        """Bump reinforcement count for a fact and ask Cognee to improve with feedback_alpha."""

        facts = self._load_facts()
        for fact in facts:
            if fact.fact_id == fact_id:
                was_decayed = (fact.status == FactStatus.DECAYED)
                fact.reinforcement_count += 1
                if was_decayed:
                    fact.status = FactStatus.ACTIVE
                self._save_facts(facts)

                if was_decayed:
                    initial_trust = self.scorer.score(fact, facts).score
                    fact.cognee_data_id = await self._remember(
                        fact,
                        importance_weight=min(max(1.0 * initial_trust, 0.0), 10.0),
                    )
                else:
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
        fallback_ids = contradiction_id.split(":") if not group and ":" in contradiction_id else []
        if fallback_ids:
            group = [fact for fact in facts if fact.fact_id in fallback_ids]

        if not group:
            raise ValueError(f"Unknown contradiction_id: {contradiction_id}")
        if winner_id not in {fact.fact_id for fact in group}:
            raise ValueError(f"winner_id is not in contradiction group: {winner_id}")

        winner_seen = False
        winner_text = None
        loser_ids: list[str] = []
        loser_texts: list[str] = []
        remaining: list[TrustMetadata] = []
        for fact in facts:
            is_in_group = fact.fact_id in fallback_ids if fallback_ids else fact.contradiction_group == contradiction_id
            if not is_in_group:
                remaining.append(fact)
                continue
            if fact.fact_id == winner_id:
                fact.status = FactStatus.ACTIVE
                fact.reinforcement_count += 1
                fact.contradiction_group = None
                winner_text = fact.normalized_text
                remaining.append(fact)
                winner_seen = True
                await self._improve(feedback_alpha=feedback_alpha)
            else:
                fact.status = FactStatus.RESOLVED
                loser_ids.append(fact.fact_id)
                loser_texts.append(fact.normalized_text)
                remaining.append(fact)
                await self._forget(fact)

        self._save_facts(remaining)
        self._append_resolution(
            ResolutionEvent(
                contradiction_id=contradiction_id,
                action="keep_winner",
                winner_id=winner_id,
                winner_text=winner_text,
                loser_ids=loser_ids,
                loser_texts=loser_texts,
            )
        )

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
                await self._forget(fact)
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

    def load_resolutions(self) -> list[ResolutionEvent]:
        if not self.history_path.exists():
            return []
        payload = json.loads(self.history_path.read_text(encoding="utf-8"))
        return [ResolutionEvent.model_validate(item) for item in payload]

    def _append_resolution(self, event: ResolutionEvent) -> None:
        events = self.load_resolutions()
        events.append(event)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.model_dump(mode="json") for item in events]
        self.history_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _find_duplicate(
        self, facts: list[TrustMetadata], item: dict[str, str]
    ) -> TrustMetadata | None:
        for fact in facts:
            if (
                fact.status in {FactStatus.ACTIVE, FactStatus.CONTRADICTED, FactStatus.DECAYED}
                and
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
            return []

        relevant = []
        for fact in facts:
            if fact.status not in {FactStatus.ACTIVE, FactStatus.CONTRADICTED}:
                continue
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
        return relevant

    def _merge_contradiction_groups(
        self,
        facts: list[TrustMetadata],
        pairs: list[ContradictionPair],
        new_fact: TrustMetadata,
    ) -> str:
        group_ids = {
            pair.fact_a.contradiction_group
            for pair in pairs
            if pair.fact_a.contradiction_group
        }
        if new_fact.contradiction_group:
            group_ids.add(new_fact.contradiction_group)

        group_id = sorted(group_ids)[0] if group_ids else str(uuid4())
        for fact in facts:
            if fact.contradiction_group in group_ids:
                fact.contradiction_group = group_id
        new_fact.contradiction_group = group_id
        return group_id

    async def _active_contradictions(
        self, facts: list[TrustMetadata]
    ) -> list[ContradictionPair]:
        from collections import defaultdict
        groups = defaultdict(list)
        for fact in facts:
            if fact.status == FactStatus.CONTRADICTED and fact.contradiction_group:
                groups[fact.contradiction_group].append(fact)

        contradictions: list[ContradictionPair] = []
        for group_id, group_facts in groups.items():
            if len(group_facts) < 2:
                continue
            for i in range(len(group_facts)):
                for j in range(i + 1, len(group_facts)):
                    fact_a = group_facts[i]
                    fact_b = group_facts[j]
                    trust_a = self.scorer.score(fact_a, facts).score
                    trust_b = self.scorer.score(fact_b, facts).score
                    contradictions.append(
                        ContradictionPair(
                            fact_a=fact_a,
                            fact_b=fact_b,
                            trust_a=trust_a,
                            trust_b=trust_b,
                            subject=fact_b.subject,
                            predicate=fact_b.predicate,
                            explanation=_contradiction_explanation(fact_a, fact_b),
                            resolved=False,
                            winner_id=None,
                        )
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

            text = (
                f"FACT [{fact.fact_id}]: The user stated that "
                f"'{fact.normalized_text}'. Subject: {fact.subject}. "
                f"Predicate: {fact.predicate}. Value: {fact.object_value}. "
                f"Stored at: {fact.timestamp.isoformat()}. "
                f"Reinforcement count: {fact.reinforcement_count}. "
                f"Status: {fact.status.value}. "
                f"[trust_fact_id={fact.fact_id}; source={fact.source}]"
            )
            result = await cognee.remember(
                text,
                importance_weight=importance_weight,
                node_set=[node_set],
            )
            if result and result.items:
                return result.items[0].get("id")
        except Exception:
            pass
        return None

    async def _remember_text(
        self,
        text: str,
        importance_weight: float = 1.0,
        node_set: str = "trust_answers",
    ) -> str | None:
        try:
            import cognee

            result = await cognee.remember(
                text,
                importance_weight=importance_weight,
                node_set=[node_set],
            )
            if result and result.items:
                return result.items[0].get("id")
        except Exception:
            pass
        return None

    async def _store_answer_memory(
        self,
        query_text: str,
        answer_text: str,
        web_results: list[dict[str, str]],
    ) -> None:
        facts = self._load_facts()
        normalized_query = _normalize(query_text)
        source_urls = [
            item.get("url", "")
            for item in web_results[:3]
            if item.get("url")
        ]
        clean_answer = _strip_web_verification(answer_text)
        if not clean_answer:
            return

        existing = next(
            (
                fact
                for fact in facts
                if fact.source == "web_answer"
                and _normalize(fact.subject) == normalized_query
                and fact.predicate == "answered_by"
            ),
            None,
        )
        if existing:
            existing.object_value = clean_answer
            existing.normalized_text = f"{query_text} -> {clean_answer}"
            existing.original_text = answer_text
            existing.reinforcement_count += 1
            existing.status = FactStatus.ACTIVE
            self._save_facts(facts)
            await self._remember(existing, importance_weight=1.0, node_set="trust_answers")
            await self._improve(feedback_alpha=0.1)
            return

        fact = TrustMetadata(
            fact_id=str(uuid4()),
            original_text=answer_text,
            normalized_text=f"{query_text} -> {clean_answer}",
            subject=query_text,
            predicate="answered_by",
            object_value=clean_answer,
            source="web_answer",
        )
        memory_text = (
            f"ANSWER [{fact.fact_id}]: Question: {query_text}\n"
            f"Answer: {clean_answer}\n"
            f"Sources: {'; '.join(source_urls) if source_urls else 'none'}\n"
            f"[trust_fact_id={fact.fact_id}; source=web_answer]"
        )
        fact.cognee_data_id = await self._remember_text(
            memory_text,
            importance_weight=1.0,
            node_set="trust_answers",
        )
        facts.append(fact)
        self._save_facts(facts)
        await self._improve(feedback_alpha=0.1)

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

    async def _generate_answer(
        self,
        query_text: str,
        ranked: list[RankedFact],
        contradictions: list[ContradictionPair],
        web_results: list[dict[str, str]] | None = None,
        session_id: str | None = None,
    ) -> str:
        web_results = web_results or []
        _ = session_id or "chat_session_1"

        model = _model_name()
        if model:
            try:
                from litellm import acompletion

                context_items = [
                    item.model_dump(mode="json", exclude={"memory_result"})
                    for item in ranked[:6]
                ]
                response = await acompletion(
                    model=model,
                    messages=[
                        {"role": "system", "content": TRUST_AWARE_RESPONSE_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                f"Question: {query_text}\n\n"
                                f"Memory context:\n{trust_context_block(context_items)}\n\n"
                                f"Web search context:\n{web_context_block(web_results)}"
                            ),
                        },
                    ],
                    temperature=0,
                )
                content = response.choices[0].message.content
                if content:
                    return content.strip()
            except Exception:
                pass

        if not ranked:
            return "No relevant trusted local memory was found."

        top = ranked[0]
        fact = top.fact
        score = top.trust_score.score
        unresolved = any(
            pair.fact_a.fact_id == fact.fact_id or pair.fact_b.fact_id == fact.fact_id
            for pair in contradictions
        )
        suffix = "unresolved contradiction" if unresolved else "no contradictions"
        memory_line = (
            f"{fact.normalized_text}. Trust: {score:.2f} | "
            f"Reinforced {fact.reinforcement_count}x | {suffix}"
        )

        if not web_results:
            return f"{memory_line}\n\nWeb Verification: No web results were available."

        citations = "; ".join(
            f"{item.get('title', 'Untitled')} ({item.get('url', '')})"
            for item in web_results[:3]
        )
        return (
            f"{memory_line}\n\n"
            "Web Verification: Web results were retrieved for comparison, but no LLM "
            f"synthesis was available. Review these sources: {citations}"
        )

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


def _has_memory_answer(ranked: list[RankedFact]) -> bool:
    if not ranked:
        return False
    top = ranked[0]
    if top.fact.source == "web_answer":
        return True
    return top.trust_score.score >= 0.45


def _should_search_web(query_text: str) -> bool:
    text = query_text.strip()
    if not text:
        return False

    normalized = _normalize(text)
    casual_messages = {
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "ok",
        "okay",
        "cool",
        "nice",
        "bye",
    }
    if normalized in casual_messages:
        return False

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
    return text.endswith("?") or normalized.startswith(question_starts)


def _strip_web_verification(answer_text: str) -> str:
    marker = "Web Verification"
    if marker in answer_text:
        answer_text = answer_text.split(marker, 1)[0]
    return answer_text.strip(" \n:-")


def _contradiction_explanation(fact_a: TrustMetadata, fact_b: TrustMetadata) -> str:
    if (
        _normalize(fact_a.subject) == _normalize(fact_b.subject)
        and _normalize(fact_a.predicate) == _normalize(fact_b.predicate)
        and _normalize(fact_a.object_value) != _normalize(fact_b.object_value)
    ):
        return (
            f"Both facts describe {fact_b.subject}.{fact_b.predicate} "
            f"but disagree: {fact_a.object_value!r} vs {fact_b.object_value!r}."
        )
    return (
        fact_b.contradiction_explanation
        or fact_a.contradiction_explanation
        or "The facts conflict."
    )


def _model_name() -> str | None:
    import os

    return os.getenv("LITELLM_MODEL") or os.getenv("LLM_MODEL") or os.getenv("MODEL")


async def ask_llm(
    question: str,
    system_prompt: str,
    ranked: list[RankedFact] | None = None,
    web_results: list[dict[str, str]] | None = None,
) -> str:
    from cognee.modules.agent_memory import get_current_agent_memory_context
    context = get_current_agent_memory_context()
    memory_context = context.memory_context if context else ""

    local_facts_str = ""
    if ranked:
        context_items = [
            item.model_dump(mode="json", exclude={"memory_result"})
            for item in ranked[:6]
        ]
        from trustgraph.prompts import trust_context_block
        local_facts_str = trust_context_block(context_items)

    combined_memory_context = f"{memory_context}\n\n{local_facts_str}".strip()

    from trustgraph.prompts import web_context_block
    web_context_str = web_context_block(web_results or [])

    model = _model_name()
    if not model:
        return "LLM model not configured."

    from litellm import acompletion

    enhanced_prompt = (
        f"{system_prompt}\n\n"
        "FACTUAL VERIFICATION RULES:\n"
        "You have access to a memory context containing verified facts (often extracted from uploaded documents).\n"
        "1. If the user makes any statement or claim that contradicts the facts in the memory context, you MUST explicitly tell them they are WRONG, show the contradicting fact, and explain why they are wrong.\n"
        "2. Do not let the user override verified facts in the context with their own statements.\n"
        "3. If their statement is correct or they are just asking a question, answer them helpfully and concisely.\n\n"
        f"Memory Context:\n{combined_memory_context}\n\n"
        f"Web Search Context:\n{web_context_str}"
    )

    response = await acompletion(
        model=model,
        messages=[
            {"role": "system", "content": enhanced_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()
