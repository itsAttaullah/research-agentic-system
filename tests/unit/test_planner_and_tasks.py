"""Unit tests for planner assembly, LLM planner, and task manager."""

from __future__ import annotations

import json

import pytest
from sra.core.context import RunContext
from sra.core.errors import PlanningError
from sra.core.ports.llm import LLMRequest, LLMResponse
from sra.core.structured import parse_llm_model
from sra.models.enums import TaskStatus
from sra.models.goal import ResearchGoal
from sra.models.plan import Investigation, ResearchPlan
from sra.models.reflection import CritiqueResult
from sra.planner import DraftPlan, LLMPlanner
from sra.planner.assembly import apply_draft_revision, draft_to_plan
from sra.tasks import DefaultTaskManager


class ScriptedLLM:
    def __init__(self, *payloads: dict[str, object]) -> None:
        self.payloads = list(payloads)
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self.payloads:
            raise AssertionError("ScriptedLLM ran out of payloads")
        payload = self.payloads.pop(0)
        return LLMResponse(
            content=json.dumps(payload),
            raw_json=payload,
            model="fake",
        )


def sample_draft_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "goal_summary": "Evaluate an AI product for dental clinics",
        "investigations": [
            {
                "title": "Market size",
                "rationale": "Need TAM/SAM/SOM",
                "hypotheses": ["Clinic software spend is growing"],
                "success_criteria": ["Credible market estimate with sources"],
                "priority": 90,
                "related_open_questions": ["What is US dental clinic count?"],
                "suggested_tools": ["google_search"],
            },
            {
                "title": "Competitors",
                "rationale": "Identify existing vendors",
                "priority": 80,
                "suggested_tools": ["google_search", "website_reader"],
            },
        ],
        "open_questions": ["Who pays for dental AI tools?"],
        "assumptions": ["Primary market is the United States"],
        "out_of_scope": ["Hardware dental devices"],
        "revision_summary": "",
    }
    payload.update(overrides)
    return payload


def test_parse_llm_model_accepts_fenced_json() -> None:
    response = LLMResponse(
        content='```json\n{"goal_summary":"x","investigations":[{"title":"A"}]}\n```'
    )
    draft = parse_llm_model(response, DraftPlan)
    assert draft.goal_summary == "x"
    assert draft.investigations[0].title == "A"


def test_draft_to_plan_builds_domain_plan() -> None:
    draft = DraftPlan.model_validate(sample_draft_payload())
    plan = draft_to_plan(draft)
    assert plan.version == 1
    assert len(plan.investigations) == 2
    assert plan.investigations[0].suggested_tools == ["google_search"]
    assert plan.open_questions == ["Who pays for dental AI tools?"]


def test_apply_draft_revision_preserves_plan_id_and_increments_version() -> None:
    current = draft_to_plan(DraftPlan.model_validate(sample_draft_payload()))
    revised_draft = DraftPlan.model_validate(
        sample_draft_payload(
            investigations=[
                {
                    "title": "Willingness to pay",
                    "priority": 95,
                    "rationale": "Pricing evidence is required",
                }
            ],
            revision_summary="Shifted toward pricing evidence",
        )
    )
    revised = apply_draft_revision(
        current,
        revised_draft,
        reason="Critic found weak pricing evidence",
        triggered_by="critic",
    )
    assert revised.plan_id == current.plan_id
    assert revised.version == 2
    assert revised.investigations[0].title == "Willingness to pay"
    assert revised.revisions[-1].triggered_by == "critic"
    assert "pricing" in revised.revisions[-1].summary.lower()


@pytest.mark.asyncio
async def test_llm_planner_create_and_revise() -> None:
    llm = ScriptedLLM(
        sample_draft_payload(),
        sample_draft_payload(
            investigations=[
                {
                    "title": "Legal risks",
                    "priority": 85,
                    "rationale": "HIPAA and liability",
                }
            ],
            revision_summary="Added legal risk investigation",
        ),
    )
    planner = LLMPlanner(llm)
    ctx = RunContext.create(ResearchGoal(question="Should I build an AI startup for dentists?"))

    plan = await planner.create_plan(ctx)
    ctx.plan = plan
    revised = await planner.revise_plan(
        ctx,
        reason="Need legal coverage",
        critique=CritiqueResult(passed=False, forced_replan=True, summary="Missing legal risks"),
    )

    assert plan.investigations[0].title == "Market size"
    assert revised.version == 2
    assert revised.investigations[0].title == "Legal risks"
    assert llm.requests[0].response_schema_name == "DraftPlan"
    assert llm.requests[1].metadata["component"] == "planner"


@pytest.mark.asyncio
async def test_llm_planner_repairs_invalid_json_once() -> None:
    llm = ScriptedLLM(
        {"not": "a plan"},
        sample_draft_payload(),
    )
    planner = LLMPlanner(llm, max_repair_attempts=1)
    ctx = RunContext.create(ResearchGoal(question="Test repair"))

    plan = await planner.create_plan(ctx)

    assert plan.goal_summary.startswith("Evaluate")
    assert len(llm.requests) == 2


@pytest.mark.asyncio
async def test_llm_planner_raises_when_repair_exhausted() -> None:
    llm = ScriptedLLM({"not": "a plan"}, {"still": "wrong"})
    planner = LLMPlanner(llm, max_repair_attempts=1)
    ctx = RunContext.create(ResearchGoal(question="Test failure"))

    with pytest.raises(PlanningError):
        await planner.create_plan(ctx)


@pytest.mark.asyncio
async def test_task_manager_sync_next_done_and_enqueue() -> None:
    manager = DefaultTaskManager()
    ctx = RunContext.create(ResearchGoal(question="Dental AI"))
    low = Investigation(title="Niche blogs", priority=20)
    high = Investigation(
        title="Market size",
        priority=90,
        suggested_tools=["google_search"],
    )
    ctx.plan = ResearchPlan(goal_summary="Dental AI", investigations=[low, high])

    tasks = await manager.sync_tasks(ctx)
    assert len(tasks) == 2
    assert {task.title for task in tasks} == {"Niche blogs", "Market size"}

    first = await manager.next_task(ctx)
    assert first is not None
    assert first.title == "Market size"
    assert first.status is TaskStatus.IN_PROGRESS
    assert first.suggested_tools == ["google_search"]

    await manager.mark_done(ctx, first.id)
    assert all(task.status is TaskStatus.DONE for task in ctx.tasks if task.id == first.id)

    created = await manager.enqueue_from_questions(
        ctx,
        ["What do dentists currently use?", "What do dentists currently use?"],
        priority=70,
    )
    assert len(created) == 1
    assert any(item.title == "Emerging questions" for item in ctx.plan.investigations)
    assert created[0].priority == 70

    nxt = await manager.next_task(ctx)
    assert nxt is not None
    # Emerging question priority 70 beats remaining investigation priority 20.
    assert nxt.title == "What do dentists currently use?"


@pytest.mark.asyncio
async def test_task_manager_cancels_tasks_for_removed_investigations() -> None:
    manager = DefaultTaskManager()
    ctx = RunContext.create(ResearchGoal(question="Dental AI"))
    old = Investigation(title="Old angle", priority=50)
    ctx.plan = ResearchPlan(goal_summary="Dental AI", investigations=[old])
    await manager.sync_tasks(ctx)

    replacement = Investigation(title="New angle", priority=60)
    ctx.plan = ResearchPlan(goal_summary="Dental AI", investigations=[replacement])
    tasks = await manager.sync_tasks(ctx)

    cancelled = [task for task in tasks if task.title == "Old angle"]
    active = [task for task in tasks if task.title == "New angle"]
    assert len(cancelled) == 1
    assert cancelled[0].status is TaskStatus.CANCELLED
    assert len(active) == 1
    assert active[0].status is TaskStatus.PENDING
