"""Unit tests for the LLM-backed Reflection Engine."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sra.core.context import RunContext
from sra.core.errors import ReflectionError
from sra.core.ports.llm import LLMRequest, LLMResponse
from sra.models.enums import KnowledgeKind, TrustTier
from sra.models.goal import ResearchGoal
from sra.models.knowledge import KnowledgeUnit
from sra.models.plan import Investigation, ResearchPlan
from sra.models.tools import ToolResult
from sra.reflection import LLMReflectionEngine
from sra.reflection.assembly import draft_to_reflection
from sra.reflection.schemas import DraftReflection as DraftReflectionModel


class ScriptedLLM:
    def __init__(self, *payloads: dict[str, object]) -> None:
        self.payloads = list(payloads)
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self.payloads:
            raise AssertionError("ScriptedLLM ran out of payloads")
        payload = self.payloads.pop(0)
        return LLMResponse(content=json.dumps(payload), raw_json=payload, model="fake")


def sample_reflection_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "answered_questions": ["What is the US dental clinic count?"],
        "new_questions": ["What do clinics pay for imaging AI?"],
        "should_continue": True,
        "strategy_should_change": False,
        "strategy_change_summary": "",
        "source_trust_notes": ["Official ADA statistics appear credible"],
        "evidence_quality": 0.72,
        "notes": "Market-size question partially answered; pricing still open.",
    }
    payload.update(overrides)
    return payload


def _ctx() -> RunContext:
    ctx = RunContext.create(ResearchGoal(question="Should I build an AI startup for dentists?"))
    ctx.plan = ResearchPlan(
        goal_summary="Dental AI feasibility",
        investigations=[
            Investigation(
                title="Market size",
                related_open_questions=["What is the US dental clinic count?"],
            )
        ],
        open_questions=["What is the US dental clinic count?"],
    )
    ctx.memory.working.open_questions = ["What is the US dental clinic count?"]
    ctx.memory.working.recent_evidence = [
        KnowledgeUnit(
            kind=KnowledgeKind.STATISTIC,
            statement="There are roughly 200,000 dentists in the US.",
            topic="Market size",
            confidence=0.7,
            trust_tier=TrustTier.TRUSTED_PUBLICATION,
        )
    ]
    return ctx


def test_draft_to_reflection_normalizes_and_rejects_bad_strategy_flag() -> None:
    draft = DraftReflectionModel.model_validate(
        sample_reflection_payload(
            answered_questions=["Q1", "q1", ""],
            new_questions=["Q1", "Q2"],
        )
    )
    result = draft_to_reflection(draft)
    assert result.answered_questions == ["Q1"]
    assert result.new_questions == ["Q2"]

    with pytest.raises(ReflectionError):
        draft_to_reflection(
            DraftReflectionModel.model_validate(
                sample_reflection_payload(
                    strategy_should_change=True,
                    strategy_change_summary="",
                )
            )
        )


@pytest.mark.asyncio
async def test_llm_reflection_engine_returns_structured_result() -> None:
    llm = ScriptedLLM(sample_reflection_payload())
    engine = LLMReflectionEngine(llm)
    ctx = _ctx()
    tool_result = ToolResult(
        call_id=uuid4(),
        tool_name="google_search",
        success=True,
        output={"results": [{"title": "ADA stats"}]},
    )

    result = await engine.reflect(ctx, latest_tool_result=tool_result)

    assert result.answered_questions == ["What is the US dental clinic count?"]
    assert result.new_questions == ["What do clinics pay for imaging AI?"]
    assert result.should_continue is True
    assert result.evidence_quality == 0.72
    assert llm.requests[0].response_schema_name == "DraftReflection"
    assert llm.requests[0].metadata["component"] == "reflection"
    assert "ADA stats" in llm.requests[0].messages[-1].content


@pytest.mark.asyncio
async def test_llm_reflection_engine_repairs_invalid_json_once() -> None:
    llm = ScriptedLLM({"evidence_quality": 2.5}, sample_reflection_payload())
    engine = LLMReflectionEngine(llm, max_repair_attempts=1)
    result = await engine.reflect(_ctx())
    assert result.notes.startswith("Market-size")
    assert len(llm.requests) == 2


@pytest.mark.asyncio
async def test_llm_reflection_engine_raises_when_repair_exhausted() -> None:
    llm = ScriptedLLM({"evidence_quality": 2.5}, {"evidence_quality": -1})
    engine = LLMReflectionEngine(llm, max_repair_attempts=1)
    with pytest.raises(ReflectionError):
        await engine.reflect(_ctx())


@pytest.mark.asyncio
async def test_strategy_change_reflection_is_accepted() -> None:
    llm = ScriptedLLM(
        sample_reflection_payload(
            strategy_should_change=True,
            strategy_change_summary="Pricing evidence is missing; prioritize WTP research.",
            should_continue=True,
        )
    )
    engine = LLMReflectionEngine(llm)
    result = await engine.reflect(_ctx())
    assert result.strategy_should_change is True
    assert "WTP" in result.strategy_change_summary
