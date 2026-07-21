"""Convert LLM draft critiques into durable CritiqueResult objects."""

from __future__ import annotations

from sra.core.errors import CritiqueError
from sra.core.time import utc_now
from sra.critic.schemas import DraftCritique, DraftFinding
from sra.models.reflection import CritiqueFinding, CritiqueResult

_VALID_SEVERITIES = {"low", "medium", "high", "blocker"}


def draft_to_critique(draft: DraftCritique) -> CritiqueResult:
    """Normalize critic output into a consistent gate decision."""
    findings = [_to_finding(item) for item in draft.findings]
    has_blocker = any(item.severity == "blocker" for item in findings)
    directives = _dedupe(draft.replan_directives)

    passed = draft.passed and not has_blocker
    forced_replan = draft.forced_replan or (not passed) or has_blocker

    if passed and forced_replan:
        # A passing critique cannot simultaneously force replanning.
        forced_replan = False

    if not passed and not directives:
        directives = [
            finding.message for finding in findings if finding.severity in {"high", "blocker"}
        ] or ["Gather stronger evidence before finalizing the report."]

    summary = draft.summary.strip()
    if not summary:
        if passed:
            summary = "Research quality is sufficient to generate the final report."
        else:
            summary = "Research quality is insufficient; return to planning."

    if passed and findings and all(item.severity == "low" for item in findings):
        # Low findings alone do not fail the gate.
        pass

    return CritiqueResult(
        at=utc_now(),
        passed=passed,
        findings=findings,
        forced_replan=forced_replan,
        replan_directives=directives,
        summary=summary,
    )


def _to_finding(draft: DraftFinding) -> CritiqueFinding:
    code = draft.code.strip().lower().replace(" ", "_")
    if not code:
        raise CritiqueError("Critique finding code cannot be empty")
    message = draft.message.strip()
    if not message:
        raise CritiqueError("Critique finding message cannot be empty")
    severity = draft.severity if draft.severity in _VALID_SEVERITIES else "medium"
    return CritiqueFinding(
        code=code,
        severity=severity,
        message=message,
        related_topics=_dedupe(draft.related_topics),
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
