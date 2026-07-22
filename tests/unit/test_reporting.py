"""Unit tests for report building and multi-format rendering."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from sra.core.context import RunContext
from sra.models.enums import KnowledgeKind, ReportFormat, TrustTier
from sra.models.goal import ResearchGoal
from sra.models.knowledge import KnowledgeUnit
from sra.models.plan import Investigation, ResearchPlan
from sra.models.reflection import (
    ConfidenceMap,
    CritiqueResult,
    TopicConfidence,
)
from sra.models.sources import SourceRecord
from sra.models.tools import ToolResult
from sra.reporting import ResearchReportGenerator
from sra.reporting.builder import build_report_document


def _ctx() -> RunContext:
    ctx = RunContext.create(
        ResearchGoal(
            question="Should I build an AI startup for dentists?",
            success_criteria=["Clear recommendation with evidence"],
            constraints={"region": "US"},
        )
    )
    ctx.plan = ResearchPlan(
        goal_summary="Dental AI feasibility",
        investigations=[
            Investigation(title="Market size", priority=90, rationale="Need TAM"),
            Investigation(title="Competitors", priority=80),
        ],
        assumptions=["Clinics will buy SaaS"],
        open_questions=["What will clinics pay?"],
        out_of_scope=["Hardware devices"],
    )
    ctx.memory.working.recent_evidence = [
        KnowledgeUnit(
            kind=KnowledgeKind.STATISTIC,
            statement="There are roughly 200,000 dentists in the US.",
            topic="Market size",
            confidence=0.8,
            trust_tier=TrustTier.TRUSTED_PUBLICATION,
        ),
        KnowledgeUnit(
            kind=KnowledgeKind.COMPANY,
            statement="Pearl builds dental AI imaging products.",
            topic="Competitors",
            entities=["Pearl"],
            confidence=0.7,
            trust_tier=TrustTier.OFFICIAL,
        ),
        KnowledgeUnit(
            kind=KnowledgeKind.RISK,
            statement="HIPAA compliance increases go-to-market cost.",
            topic="Legal risks",
            confidence=0.75,
            trust_tier=TrustTier.GOVERNMENT,
        ),
        KnowledgeUnit(
            kind=KnowledgeKind.ADVANTAGE,
            statement="Scheduling automation can reduce front-desk load.",
            topic="Opportunities",
            confidence=0.65,
            trust_tier=TrustTier.BLOG,
        ),
    ]
    ctx.memory.known_sources = [
        SourceRecord(
            url="https://example.com/ada-report",
            title="ADA workforce report",
            trust_tier=TrustTier.TRUSTED_PUBLICATION,
        )
    ]
    ctx.memory.working.visited_source_keys = ["url:https://example.com/ada-report"]
    ctx.confidence = ConfidenceMap(
        topics=[
            TopicConfidence(topic="Market size", score=0.82, rationale="Multiple sources"),
            TopicConfidence(
                topic="Willingness to pay",
                score=0.35,
                needs_more_research=True,
                rationale="Sparse pricing data",
            ),
        ],
        overall=0.58,
    )
    ctx.last_critique = CritiqueResult(
        passed=True,
        summary="Sufficient for a cautious recommendation.",
    )
    ctx.tool_history = [
        ToolResult(call_id=uuid4(), tool_name="google_search", success=True, output={}),
        ToolResult(call_id=uuid4(), tool_name="website_reader", success=True, output={}),
    ]
    return ctx


def test_build_report_contains_required_sections() -> None:
    document = build_report_document(_ctx())
    titles = [section.title for section in document.sections]
    for required in [
        "Executive Summary",
        "Research Goal",
        "Methodology",
        "Market Analysis",
        "Competitors",
        "SWOT",
        "Risks",
        "Opportunities",
        "Evidence",
        "Confidence Scores",
        "Recommendation",
        "References",
    ]:
        assert required in titles
    assert "ADA workforce report" in document.references[0]
    assert "Pearl" in "\n".join(section.body_markdown for section in document.sections)


@pytest.mark.asyncio
async def test_report_generator_renders_all_formats(tmp_path: Path) -> None:
    generator = ResearchReportGenerator(output_dir=tmp_path)
    ctx = _ctx()
    document = await generator.build(ctx)

    md = await generator.render(document, fmt=ReportFormat.MARKDOWN)
    html = await generator.render(document, fmt=ReportFormat.HTML)
    js = await generator.render(document, fmt=ReportFormat.JSON)
    pdf = await generator.render(document, fmt=ReportFormat.PDF)

    assert md.path is not None and md.path.exists()
    assert md.content is not None and md.content.startswith("# Research Report:")
    assert "Executive Summary" in md.content

    assert html.path is not None and html.path.exists()
    assert html.content is not None and "<html" in html.content
    assert "Confidence Scores" in html.content

    assert js.path is not None and js.path.exists()
    payload = json.loads(js.content or "{}")
    assert payload["run_id"] == str(ctx.run_id)
    assert len(payload["sections"]) >= 12

    assert pdf.path is not None and pdf.path.exists()
    assert pdf.path.stat().st_size > 0
    assert pdf.content is None


@pytest.mark.asyncio
async def test_failed_critic_changes_recommendation_language(tmp_path: Path) -> None:
    ctx = _ctx()
    ctx.last_critique = CritiqueResult(
        passed=False,
        forced_replan=True,
        summary="Missing willingness-to-pay evidence.",
        replan_directives=["Collect pricing evidence"],
    )
    generator = ResearchReportGenerator(output_dir=tmp_path)
    document = await generator.build(ctx)
    recommendation = next(
        section for section in document.sections if section.title == "Recommendation"
    )
    assert "critic" in recommendation.body_markdown.casefold()
    assert "Collect pricing evidence" in recommendation.body_markdown
