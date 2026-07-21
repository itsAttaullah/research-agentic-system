"""Unit tests for the LLM-backed Critic gate."""

from __future__ import annotations

import json

import pytest
from sra.core.context import RunContext
from sra.core.errors import CritiqueError
from sra.core.ports.llm import LLMRequest, LLMResponse
from sra.critic import LLMCritic
from sra.critic.assembly import draft_to_critique
from sra.critic.schemas import DraftCritique
from sra.models.enums import KnowledgeKind, TrustTier
from sra.models.goal import ResearchGoal
from sra.models.knowledge import KnowledgeUnit
from sra.models.plan import Investigation, ResearchPlan
from sra.models.reflection import ConfidenceMap, TopicConfidence


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


def sample_pass_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "passed": True,
        "findings": [
            {
                "code": "minor_gap",
                "severity": "low",
                "message": "Secondary regional data could be stronger.",
                "related_topics": ["Market size"],
            }
        ],
        "forced_replan": False,
        "replan_directives": [],
        "summary": "Evidence is sufficient for a recommendation.",
    }
    payload.update(overrides)
    return payload


def sample_fail_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "passed": False,
        "findings": [
            {
                "code": "missing_evidence",
                "severity": "blocker",
                "message": "No willingness-to-pay evidence was found.",
                "related_topics": ["Willingness to pay"],
            },
            {
                "code": "weak_assumption",
                "severity": "high",
                "message": "Assumes dentists will buy SaaS without validation.",
                "related_topics": ["Customer pain points"],
            },
        ],
        "forced_replan": True,
        "replan_directives": [
            "Collect pricing and willingness-to-pay evidence",
            "Interview or survey-derived pain-point sources",
        ],
        "summary": "Cannot finalize without pricing evidence.",
    }
    payload.update(overrides)
    return payload


def _ctx() -> RunContext:
    ctx = RunContext.create(ResearchGoal(question="Should I build an AI startup for dentists?"))
    ctx.plan = ResearchPlan(
        goal_summary="Dental AI feasibility",
        investigations=[
            Investigation(title="Market size", success_criteria=["Credible TAM estimate"]),
            Investigation(title="Willingness to pay"),
        ],
        assumptions=["Dentists will adopt cloud SaaS quickly"],
        open_questions=["What will clinics pay?"],
    )
    ctx.memory.working.recent_evidence = [
        KnowledgeUnit(
            kind=KnowledgeKind.CLAIM,
            statement="Some clinics use imaging AI.",
            topic="Competitors",
            confidence=0.4,
            trust_tier=TrustTier.BLOG,
        )
    ]
    ctx.confidence = ConfidenceMap(
        topics=[
            TopicConfidence(topic="Market size", score=0.8),
            TopicConfidence(topic="Willingness to pay", score=0.3, needs_more_research=True),
        ],
        overall=0.55,
    )
    return ctx


def test_draft_to_critique_pass_and_blocker_normalization() -> None:
    passed = draft_to_critique(DraftCritique.model_validate(sample_pass_payload()))
    assert passed.passed is True
    assert passed.forced_replan is False
    assert passed.findings[0].severity == "low"

    # Blocker forces failure even if model claimed passed=true.
    blocked = draft_to_critique(
        DraftCritique.model_validate(
            sample_pass_payload(
                findings=[
                    {
                        "code": "bias",
                        "severity": "blocker",
                        "message": "All sources are vendor blogs.",
                        "related_topics": ["Competitors"],
                    }
                ]
            )
        )
    )
    assert blocked.passed is False
    assert blocked.forced_replan is True
    assert blocked.replan_directives


def test_failed_critique_without_directives_gets_defaults() -> None:
    result = draft_to_critique(
        DraftCritique.model_validate(
            {
                "passed": False,
                "findings": [
                    {
                        "code": "incomplete_research",
                        "severity": "high",
                        "message": "Competitor landscape is incomplete.",
                        "related_topics": ["Competitors"],
                    }
                ],
                "forced_replan": False,
                "replan_directives": [],
                "summary": "",
            }
        )
    )
    assert result.passed is False
    assert result.forced_replan is True
    assert "Competitor landscape is incomplete." in result.replan_directives
    assert "insufficient" in result.summary.lower()


@pytest.mark.asyncio
async def test_llm_critic_pass() -> None:
    llm = ScriptedLLM(sample_pass_payload())
    critic = LLMCritic(llm)
    result = await critic.critique(_ctx())
    assert result.passed is True
    assert llm.requests[0].response_schema_name == "DraftCritique"
    assert llm.requests[0].metadata["component"] == "critic"
    assert "Willingness to pay" in llm.requests[0].messages[-1].content


@pytest.mark.asyncio
async def test_llm_critic_fail_forces_replan() -> None:
    llm = ScriptedLLM(sample_fail_payload())
    critic = LLMCritic(llm)
    result = await critic.critique(_ctx())
    assert result.passed is False
    assert result.forced_replan is True
    assert any(item.code == "missing_evidence" for item in result.findings)
    assert "pricing" in result.summary.lower()


@pytest.mark.asyncio
async def test_llm_critic_repairs_invalid_payload_once() -> None:
    llm = ScriptedLLM(
        {"passed": True, "findings": "not-a-list"},
        sample_pass_payload(),
    )
    critic = LLMCritic(llm, max_repair_attempts=1)
    result = await critic.critique(_ctx())
    assert result.passed is True
    assert len(llm.requests) == 2


@pytest.mark.asyncio
async def test_llm_critic_raises_when_repair_exhausted() -> None:
    llm = ScriptedLLM(
        {"passed": True, "findings": "not-a-list"},
        {"passed": False, "findings": [{"code": ""}]},
    )
    critic = LLMCritic(llm, max_repair_attempts=1)
    with pytest.raises(CritiqueError):
        await critic.critique(_ctx())
