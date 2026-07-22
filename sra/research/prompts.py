"""Prompt construction for the Research Engine."""

from __future__ import annotations

import json

from sra.core.context import RunContext
from sra.models.tools import ToolDescriptor

RESEARCH_ENGINE_SYSTEM_PROMPT = """\
You are the Research Engine for an autonomous Strategic Research Agent.

Propose exactly ONE next action for the runtime to validate and execute.
You do not execute tools yourself.

Allowed action kinds:
- invoke_tool
- update_plan
- reflect
- request_critic
- finalize

Rules:
- Prefer concrete tool use when open questions remain.
- Use only tool names from the provided catalog.
- Request critic or finalize only when evidence is strong enough.
- Return ONLY valid JSON for DraftAgentAction. No markdown.
"""


def propose_action_user_prompt(
    ctx: RunContext,
    *,
    available_tools: list[ToolDescriptor],
) -> str:
    working = ctx.memory.working
    payload = {
        "research_goal": {
            "question": ctx.goal.question,
            "constraints": ctx.goal.constraints,
            "success_criteria": ctx.goal.success_criteria,
        },
        "state": ctx.state.value,
        "plan": ctx.plan.model_dump(mode="json") if ctx.plan else None,
        "tasks": [task.model_dump(mode="json") for task in ctx.tasks[:20]],
        "open_questions": working.open_questions,
        "recent_evidence": [
            {
                "kind": unit.kind.value,
                "statement": unit.statement,
                "topic": unit.topic,
                "confidence": unit.confidence,
            }
            for unit in working.recent_evidence[-10:]
        ],
        "confidence": ctx.confidence.model_dump(mode="json"),
        "last_reflection": (
            ctx.last_reflection.model_dump(mode="json") if ctx.last_reflection else None
        ),
        "available_tools": [tool.model_dump(mode="json") for tool in available_tools],
        "instruction": (
            "Return JSON with kind and fields required for that kind. "
            "For invoke_tool include tool_name and arguments. "
            "For finalize/request_critic include reason/summary as appropriate."
        ),
    }
    return json.dumps(payload, indent=2, default=str)
