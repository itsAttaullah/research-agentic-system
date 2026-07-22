"""Unit tests for evidence-based confidence estimation."""

from __future__ import annotations

import pytest
from sra.confidence import EvidenceConfidenceEstimator
from sra.core.context import RunContext
from sra.models.enums import KnowledgeKind, TrustTier
from sra.models.goal import ResearchGoal
from sra.models.knowledge import KnowledgeUnit
from sra.models.plan import Investigation, ResearchPlan


@pytest.mark.asyncio
async def test_confidence_increases_with_trusted_evidence() -> None:
    estimator = EvidenceConfidenceEstimator()
    ctx = RunContext.create(ResearchGoal(question="Dental AI?"))
    ctx.plan = ResearchPlan(
        goal_summary="Dental AI",
        investigations=[Investigation(title="Market size")],
    )

    empty = await estimator.estimate(ctx)
    assert empty.topics[0].needs_more_research is True
    assert empty.topics[0].score <= 0.3

    ctx.memory.working.recent_evidence = [
        KnowledgeUnit(
            kind=KnowledgeKind.STATISTIC,
            statement="200k dentists",
            topic="Market size",
            confidence=0.85,
            trust_tier=TrustTier.TRUSTED_PUBLICATION,
        ),
        KnowledgeUnit(
            kind=KnowledgeKind.FACT,
            statement="Clinic software spend is rising",
            topic="Market size",
            confidence=0.8,
            trust_tier=TrustTier.OFFICIAL,
        ),
    ]
    filled = await estimator.estimate(ctx)
    assert filled.topics[0].score > empty.topics[0].score
    assert "Market size" in estimator.below_threshold(empty, threshold=0.7)
