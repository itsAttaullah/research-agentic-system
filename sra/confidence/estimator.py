"""Deterministic confidence estimation from plan topics and evidence."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sra.core.context import RunContext
from sra.core.time import utc_now
from sra.models.enums import TrustTier
from sra.models.knowledge import KnowledgeUnit
from sra.models.reflection import ConfidenceMap, TopicConfidence

_TRUST_WEIGHT: dict[TrustTier, float] = {
    TrustTier.OFFICIAL: 1.0,
    TrustTier.GOVERNMENT: 1.0,
    TrustTier.ACADEMIC: 0.95,
    TrustTier.TRUSTED_PUBLICATION: 0.9,
    TrustTier.NEWS: 0.7,
    TrustTier.COMMUNITY: 0.55,
    TrustTier.BLOG: 0.45,
    TrustTier.UNKNOWN: 0.35,
}


class EvidenceConfidenceEstimator:
    """ConfidenceEstimator port: score topics from available structured evidence."""

    def __init__(self, *, default_score: float = 0.25) -> None:
        self._default_score = default_score

    async def estimate(self, ctx: RunContext) -> ConfidenceMap:
        topics = self._topic_names(ctx)
        evidence_by_topic = self._group_evidence(ctx.memory.working.recent_evidence)
        scored: list[TopicConfidence] = []

        for topic in topics:
            units = evidence_by_topic.get(topic.casefold(), [])
            score, rationale, unit_ids, needs_more = self._score_topic(topic, units)
            scored.append(
                TopicConfidence(
                    topic=topic,
                    score=score,
                    rationale=rationale,
                    evidence_unit_ids=unit_ids,
                    needs_more_research=needs_more,
                )
            )

        overall = (
            sum(item.score for item in scored) / len(scored) if scored else self._default_score
        )
        return ConfidenceMap(topics=scored, overall=round(overall, 4), updated_at=utc_now())

    def below_threshold(
        self,
        confidence: ConfidenceMap,
        *,
        threshold: float,
    ) -> list[str]:
        return [
            topic.topic
            for topic in confidence.topics
            if topic.score < threshold or topic.needs_more_research
        ]

    @staticmethod
    def _topic_names(ctx: RunContext) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        if ctx.plan is not None:
            for investigation in ctx.plan.active_investigations():
                key = investigation.title.casefold()
                if key not in seen:
                    seen.add(key)
                    names.append(investigation.title)
        for unit in ctx.memory.working.recent_evidence:
            topic = unit.topic.strip() or "General"
            key = topic.casefold()
            if key not in seen:
                seen.add(key)
                names.append(topic)
        if not names:
            names.append("Overall")
        return names

    @staticmethod
    def _group_evidence(
        units: list[KnowledgeUnit],
    ) -> dict[str, list[KnowledgeUnit]]:
        grouped: dict[str, list[KnowledgeUnit]] = defaultdict(list)
        for unit in units:
            topic = (unit.topic.strip() or "General").casefold()
            grouped[topic].append(unit)
        return grouped

    def _score_topic(
        self,
        topic: str,
        units: list[KnowledgeUnit],
    ) -> tuple[float, str, list[UUID], bool]:
        if not units:
            return (
                self._default_score,
                f"No structured evidence yet for '{topic}'.",
                [],
                True,
            )

        trust_scores = [_TRUST_WEIGHT.get(unit.trust_tier, 0.35) for unit in units]
        confidences = [unit.confidence for unit in units]
        coverage = min(1.0, len(units) / 3.0)
        blended = (
            0.45 * (sum(confidences) / len(confidences))
            + 0.35 * (sum(trust_scores) / len(trust_scores))
            + 0.20 * coverage
        )
        score = round(min(0.98, max(0.05, blended)), 4)
        needs_more = score < 0.7 or len(units) < 2
        avg_trust = sum(trust_scores) / len(trust_scores)
        rationale = (
            f"{len(units)} evidence unit(s); "
            f"avg confidence {sum(confidences) / len(confidences):.2f}; "
            f"avg trust {avg_trust:.2f}."
        )
        return score, rationale, [unit.unit_id for unit in units], needs_more
