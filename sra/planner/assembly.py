"""Convert LLM draft plans into durable ResearchPlan domain objects."""

from __future__ import annotations

from sra.core.errors import PlanningError
from sra.core.time import utc_now
from sra.models.enums import TaskStatus
from sra.models.plan import Investigation, PlanRevision, ResearchPlan
from sra.planner.schemas import DraftInvestigation, DraftPlan


def draft_to_plan(draft: DraftPlan) -> ResearchPlan:
    """Build a brand-new plan from a validated draft."""
    if not draft.investigations:
        raise PlanningError("Planner draft contained no investigations")
    return ResearchPlan(
        goal_summary=draft.goal_summary.strip(),
        investigations=[_to_investigation(item) for item in draft.investigations],
        open_questions=_dedupe(draft.open_questions),
        assumptions=_dedupe(draft.assumptions),
        out_of_scope=_dedupe(draft.out_of_scope),
        revisions=[],
        version=1,
        updated_at=utc_now(),
    )


def apply_draft_revision(
    current: ResearchPlan,
    draft: DraftPlan,
    *,
    reason: str,
    triggered_by: str,
) -> ResearchPlan:
    """Produce the next plan version while preserving plan identity."""
    if not draft.investigations:
        raise PlanningError("Revised planner draft contained no investigations")

    summary = draft.revision_summary.strip() or reason.strip() or "Plan revised"
    revision = PlanRevision(
        reason=reason.strip() or summary,
        summary=summary,
        triggered_by=triggered_by,
    )
    return current.model_copy(
        update={
            "goal_summary": draft.goal_summary.strip() or current.goal_summary,
            "investigations": [_to_investigation(item) for item in draft.investigations],
            "open_questions": _dedupe(draft.open_questions),
            "assumptions": _dedupe(draft.assumptions),
            "out_of_scope": _dedupe(draft.out_of_scope),
            "revisions": [*current.revisions, revision],
            "version": current.version + 1,
            "updated_at": utc_now(),
        }
    )


def _to_investigation(draft: DraftInvestigation) -> Investigation:
    title = draft.title.strip()
    if not title:
        raise PlanningError("Investigation title cannot be empty")
    return Investigation(
        title=title,
        rationale=draft.rationale.strip(),
        hypotheses=_dedupe(draft.hypotheses),
        success_criteria=_dedupe(draft.success_criteria),
        priority=draft.priority,
        status=TaskStatus.PENDING,
        related_open_questions=_dedupe(draft.related_open_questions),
        suggested_tools=_dedupe(draft.suggested_tools),
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result
