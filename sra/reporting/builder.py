"""Assemble a structured ReportDocument from run state. Presentation only."""

from __future__ import annotations

from collections import defaultdict

from sra.core.context import RunContext
from sra.core.errors import ReportGenerationError
from sra.models.enums import KnowledgeKind
from sra.models.knowledge import KnowledgeUnit
from sra.models.reporting import ReportDocument, ReportSection
from sra.models.sources import SourceRecord


def build_report_document(ctx: RunContext) -> ReportDocument:
    """Create the canonical in-memory report from durable run context."""
    if not ctx.goal.question.strip():
        raise ReportGenerationError("Cannot build a report without a research goal")

    evidence = list(ctx.memory.working.recent_evidence)
    by_kind = _group_by_kind(evidence)
    by_topic = _group_by_topic(evidence)
    references = _collect_references(ctx)

    sections = [
        ReportSection(title="Executive Summary", body_markdown=_executive_summary(ctx), order=10),
        ReportSection(title="Research Goal", body_markdown=_research_goal(ctx), order=20),
        ReportSection(title="Methodology", body_markdown=_methodology(ctx), order=30),
        ReportSection(
            title="Market Analysis",
            body_markdown=_topic_section(by_topic, preferred=("market", "market size", "tam")),
            order=40,
        ),
        ReportSection(
            title="Competitors",
            body_markdown=_competitors_section(by_kind, by_topic),
            order=50,
        ),
        ReportSection(title="SWOT", body_markdown=_swot_section(by_kind), order=60),
        ReportSection(
            title="Risks",
            body_markdown=_bullets(by_kind.get(KnowledgeKind.RISK, []), empty="No risks recorded."),
            order=70,
        ),
        ReportSection(
            title="Opportunities",
            body_markdown=_bullets(
                by_kind.get(KnowledgeKind.ADVANTAGE, []),
                empty="No opportunities recorded.",
            ),
            order=80,
        ),
        ReportSection(title="Evidence", body_markdown=_evidence_section(evidence), order=90),
        ReportSection(
            title="Confidence Scores",
            body_markdown=_confidence_section(ctx),
            order=100,
        ),
        ReportSection(
            title="Recommendation",
            body_markdown=_recommendation(ctx),
            order=110,
        ),
        ReportSection(
            title="References",
            body_markdown=_references_section(references),
            order=120,
        ),
    ]

    return ReportDocument(
        run_id=ctx.run_id,
        title=f"Research Report: {ctx.goal.question}",
        sections=sections,
        confidence=ctx.confidence,
        references=references,
    )


def _executive_summary(ctx: RunContext) -> str:
    lines = [
        f"**Goal:** {ctx.goal.question}",
        "",
        f"**Overall confidence:** {_pct(ctx.confidence.overall)}",
    ]
    if ctx.last_critique is not None:
        lines.append(f"**Critic:** {'passed' if ctx.last_critique.passed else 'did not pass'}")
        if ctx.last_critique.summary:
            lines.append(f"**Critic summary:** {ctx.last_critique.summary}")
    if ctx.last_reflection is not None and ctx.last_reflection.notes:
        lines.append(f"**Latest reflection:** {ctx.last_reflection.notes}")
    if ctx.plan is not None:
        lines.append("")
        lines.append(
            f"The investigation covered {len(ctx.plan.active_investigations())} active "
            f"research areas across plan version {ctx.plan.version}."
        )
    return "\n".join(lines)


def _research_goal(ctx: RunContext) -> str:
    lines = [f"**Question:** {ctx.goal.question}"]
    if ctx.goal.success_criteria:
        lines.append("")
        lines.append("**Success criteria**")
        lines.extend(f"- {item}" for item in ctx.goal.success_criteria)
    if ctx.goal.constraints:
        lines.append("")
        lines.append("**Constraints**")
        for key, value in ctx.goal.constraints.items():
            lines.append(f"- **{key}:** {value}")
    if ctx.plan is not None and ctx.plan.out_of_scope:
        lines.append("")
        lines.append("**Out of scope**")
        lines.extend(f"- {item}" for item in ctx.plan.out_of_scope)
    return "\n".join(lines)


def _methodology(ctx: RunContext) -> str:
    lines: list[str] = []
    if ctx.plan is not None:
        lines.append(f"**Plan summary:** {ctx.plan.goal_summary}")
        lines.append("")
        lines.append("**Investigations**")
        for item in ctx.plan.investigations:
            lines.append(
                f"- **{item.title}** (priority {item.priority}, status `{item.status.value}`)"
            )
            if item.rationale:
                lines.append(f"  - Rationale: {item.rationale}")
        if ctx.plan.assumptions:
            lines.append("")
            lines.append("**Assumptions**")
            lines.extend(f"- {item}" for item in ctx.plan.assumptions)
    else:
        lines.append("No formal research plan was recorded.")

    tool_names = [result.tool_name for result in ctx.tool_history if result.success]
    lines.append("")
    lines.append(
        f"**Tool activity:** {len(ctx.tool_history)} calls "
        f"({sum(1 for item in ctx.tool_history if item.success)} successful)."
    )
    if tool_names:
        unique = sorted(set(tool_names))
        lines.append("**Tools used:** " + ", ".join(f"`{name}`" for name in unique))
    lines.append(f"**Sources visited:** {len(ctx.memory.working.visited_source_keys)}")
    return "\n".join(lines)


def _competitors_section(
    by_kind: dict[KnowledgeKind, list[KnowledgeUnit]],
    by_topic: dict[str, list[KnowledgeUnit]],
) -> str:
    units = list(by_kind.get(KnowledgeKind.COMPANY, []))
    units.extend(by_kind.get(KnowledgeKind.PRODUCT, []))
    for topic, items in by_topic.items():
        if "competitor" in topic.casefold():
            units.extend(items)
    # Deduplicate by statement
    seen: set[str] = set()
    unique: list[KnowledgeUnit] = []
    for unit in units:
        key = unit.statement.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(unit)
    return _bullets(unique, empty="No competitor evidence recorded.")


def _swot_section(by_kind: dict[KnowledgeKind, list[KnowledgeUnit]]) -> str:
    strengths = by_kind.get(KnowledgeKind.ADVANTAGE, [])
    weaknesses = [
        unit
        for unit in by_kind.get(KnowledgeKind.CLAIM, [])
        if "weak" in unit.statement.casefold() or "gap" in unit.statement.casefold()
    ]
    opportunities = strengths
    threats = by_kind.get(KnowledgeKind.RISK, [])
    parts = [
        "### Strengths",
        _bullets(strengths, empty="None recorded."),
        "",
        "### Weaknesses",
        _bullets(weaknesses, empty="None recorded."),
        "",
        "### Opportunities",
        _bullets(opportunities, empty="None recorded."),
        "",
        "### Threats",
        _bullets(threats, empty="None recorded."),
    ]
    return "\n".join(parts)


def _evidence_section(evidence: list[KnowledgeUnit]) -> str:
    if not evidence:
        return "No structured evidence units were available."
    lines: list[str] = []
    for unit in evidence:
        trust = unit.trust_tier.value
        lines.append(
            f"- **[{unit.kind.value}]** {unit.statement} "
            f"(topic: {unit.topic or 'n/a'}, confidence: {_pct(unit.confidence)}, trust: `{trust}`)"
        )
    return "\n".join(lines)


def _confidence_section(ctx: RunContext) -> str:
    lines = [f"**Overall:** {_pct(ctx.confidence.overall)}", ""]
    if not ctx.confidence.topics:
        lines.append("No per-topic confidence scores were recorded.")
        return "\n".join(lines)
    lines.append("| Topic | Score | Needs more research | Rationale |")
    lines.append("| --- | --- | --- | --- |")
    for topic in ctx.confidence.topics:
        lines.append(
            f"| {topic.topic} | {_pct(topic.score)} | "
            f"{'yes' if topic.needs_more_research else 'no'} | {topic.rationale or '-'} |"
        )
    return "\n".join(lines)


def _recommendation(ctx: RunContext) -> str:
    overall = ctx.confidence.overall
    if ctx.last_critique is not None and not ctx.last_critique.passed:
        return (
            "No final recommendation should be treated as definitive because the critic "
            "gate did not pass.\n\n"
            f"**Critic summary:** {ctx.last_critique.summary or 'n/a'}\n\n"
            "Replan directives:\n"
            + "\n".join(f"- {item}" for item in ctx.last_critique.replan_directives)
        )

    if overall >= 0.75:
        stance = "Proceed with caution is supported by current evidence."
    elif overall >= 0.5:
        stance = "Further validation is recommended before committing significant resources."
    else:
        stance = "Current evidence is insufficient for a strong go decision."

    lines = [
        stance,
        "",
        f"**Confidence basis:** overall {_pct(overall)} across "
        f"{len(ctx.confidence.topics)} scored topics.",
    ]
    low = ctx.confidence.low_confidence_topics()
    if low:
        lines.append("")
        lines.append("**Low-confidence areas**")
        lines.extend(f"- {topic.topic} ({_pct(topic.score)})" for topic in low)
    open_questions = ctx.memory.working.open_questions or (
        ctx.plan.open_questions if ctx.plan else []
    )
    if open_questions:
        lines.append("")
        lines.append("**Outstanding questions**")
        lines.extend(f"- {item}" for item in open_questions[:10])
    return "\n".join(lines)


def _references_section(references: list[str]) -> str:
    if not references:
        return "No references were recorded."
    return "\n".join(f"{index}. {item}" for index, item in enumerate(references, start=1))


def _collect_references(ctx: RunContext) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()

    def _add(value: str) -> None:
        cleaned = value.strip()
        if not cleaned:
            return
        key = cleaned.casefold()
        if key in seen:
            return
        seen.add(key)
        refs.append(cleaned)

    for source in ctx.memory.known_sources:
        _add(_format_source(source))
    for key in ctx.memory.working.visited_source_keys:
        if key.startswith("url:"):
            _add(key.removeprefix("url:"))
        elif key.startswith("path:"):
            _add(key.removeprefix("path:"))
    for unit in ctx.memory.working.recent_evidence:
        for citation in unit.citations:
            if citation.url:
                _add(str(citation.url))
            elif citation.quote:
                _add(citation.quote)
    return refs


def _format_source(source: SourceRecord) -> str:
    label = source.title or source.url or source.path or str(source.source_id)
    locator = source.url or source.path or ""
    trust = source.trust_tier.value
    if locator:
        return f"{label} — {locator} (`{trust}`)"
    return f"{label} (`{trust}`)"


def _group_by_kind(evidence: list[KnowledgeUnit]) -> dict[KnowledgeKind, list[KnowledgeUnit]]:
    grouped: dict[KnowledgeKind, list[KnowledgeUnit]] = defaultdict(list)
    for unit in evidence:
        grouped[unit.kind].append(unit)
    return grouped


def _group_by_topic(evidence: list[KnowledgeUnit]) -> dict[str, list[KnowledgeUnit]]:
    grouped: dict[str, list[KnowledgeUnit]] = defaultdict(list)
    for unit in evidence:
        topic = unit.topic.strip() or "General"
        grouped[topic].append(unit)
    return grouped


def _topic_section(
    by_topic: dict[str, list[KnowledgeUnit]],
    *,
    preferred: tuple[str, ...],
) -> str:
    selected: list[KnowledgeUnit] = []
    for topic, units in by_topic.items():
        lowered = topic.casefold()
        if any(token in lowered for token in preferred):
            selected.extend(units)
    if not selected:
        # Fall back to statistics/facts if no explicit market topic exists.
        for units in by_topic.values():
            selected.extend(
                unit
                for unit in units
                if unit.kind in {KnowledgeKind.STATISTIC, KnowledgeKind.FACT, KnowledgeKind.CLAIM}
            )
    return _bullets(selected[:30], empty="No market-analysis evidence recorded.")


def _bullets(units: list[KnowledgeUnit], *, empty: str) -> str:
    if not units:
        return empty
    return "\n".join(f"- {unit.statement}" for unit in units)


def _pct(value: float) -> str:
    return f"{round(value * 100):d}%"
