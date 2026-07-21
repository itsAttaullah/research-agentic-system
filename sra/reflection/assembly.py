"""Convert LLM draft reflections into durable ReflectionResult objects."""

from __future__ import annotations

from sra.core.errors import ReflectionError
from sra.core.time import utc_now
from sra.models.reflection import ReflectionResult
from sra.reflection.schemas import DraftReflection


def draft_to_reflection(draft: DraftReflection) -> ReflectionResult:
    """Validate and normalize a draft into a domain ReflectionResult."""
    if draft.strategy_should_change and not draft.strategy_change_summary.strip():
        raise ReflectionError(
            "strategy_should_change requires a non-empty strategy_change_summary",
        )

    answered = _dedupe(draft.answered_questions)
    new_questions = _dedupe(draft.new_questions)
    # A question cannot be both answered and newly opened in the same step.
    answered_keys = {item.casefold() for item in answered}
    new_questions = [item for item in new_questions if item.casefold() not in answered_keys]

    return ReflectionResult(
        at=utc_now(),
        answered_questions=answered,
        new_questions=new_questions,
        should_continue=draft.should_continue,
        strategy_should_change=draft.strategy_should_change,
        strategy_change_summary=draft.strategy_change_summary.strip(),
        source_trust_notes=_dedupe(draft.source_trust_notes),
        evidence_quality=draft.evidence_quality,
        notes=draft.notes.strip(),
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
