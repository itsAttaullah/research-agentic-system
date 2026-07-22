"""Unit tests for research-engine action assembly."""

from __future__ import annotations

import json

import pytest
from sra.core.context import RunContext
from sra.core.errors import InvalidActionError
from sra.core.ports.llm import LLMRequest, LLMResponse
from sra.models.actions import FinalizeAction, InvokeToolAction
from sra.models.goal import ResearchGoal
from sra.research import LLMResearchEngine
from sra.research.assembly import draft_to_action
from sra.research.schemas import DraftAgentAction


class ScriptedLLM:
    def __init__(self, *payloads: dict[str, object]) -> None:
        self.payloads = list(payloads)
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        payload = self.payloads.pop(0)
        return LLMResponse(content=json.dumps(payload), raw_json=payload, model="fake")


def test_draft_to_action_supports_tool_and_finalize() -> None:
    tool = draft_to_action(
        DraftAgentAction.model_validate(
            {
                "kind": "invoke_tool",
                "tool_name": "google_search",
                "arguments": {"query": "dental AI"},
            }
        )
    )
    assert isinstance(tool, InvokeToolAction)
    assert tool.tool_name == "google_search"

    final = draft_to_action(
        DraftAgentAction.model_validate({"kind": "finalize", "summary": "done"})
    )
    assert isinstance(final, FinalizeAction)


@pytest.mark.asyncio
async def test_llm_research_engine_proposes_finalize() -> None:
    llm = ScriptedLLM({"kind": "finalize", "summary": "Enough evidence"})
    engine = LLMResearchEngine(llm)
    ctx = RunContext.create(ResearchGoal(question="Dental AI?"))
    action = await engine.propose_action(ctx, available_tools=[])
    assert isinstance(action, FinalizeAction)
    assert llm.requests[0].response_schema_name == "DraftAgentAction"


@pytest.mark.asyncio
async def test_llm_research_engine_rejects_tool_without_name() -> None:
    llm = ScriptedLLM({"kind": "invoke_tool", "tool_name": ""})
    engine = LLMResearchEngine(llm, max_repair_attempts=0)
    ctx = RunContext.create(ResearchGoal(question="Dental AI?"))
    with pytest.raises(InvalidActionError):
        await engine.propose_action(ctx, available_tools=[])
