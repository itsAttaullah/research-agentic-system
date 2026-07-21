"""Prompt construction for the Reflection Engine."""

from __future__ import annotations

import json

from sra.core.context import RunContext
from sra.models.tools import ToolResult

REFLECTION_SYSTEM_PROMPT = """\
You are the Reflection Engine for an autonomous Strategic Research Agent.

After each research step, evaluate progress honestly and decide what should
happen next. Your output influences planning and task selection.

Evaluate:
1. Which open questions were answered by the latest evidence?
2. Which new questions appeared?
3. Do we trust the latest source / tool result?
4. Is evidence quality sufficient to continue on the current path?
5. Should the research strategy change?

Rules:
- Be concrete. Prefer specific questions over vague advice.
- Do not invent tool calls.
- If strategy should change, explain why in strategy_change_summary.
- Return ONLY valid JSON matching the required schema. No markdown.
"""


def reflection_user_prompt(
    ctx: RunContext,
    *,
    latest_tool_result: ToolResult | None,
) -> str:
    plan = ctx.plan
    working = ctx.memory.working
    payload = {
        "research_goal": {
            "question": ctx.goal.question,
            "constraints": ctx.goal.constraints,
            "success_criteria": ctx.goal.success_criteria,
        },
        "plan": {
            "goal_summary": plan.goal_summary if plan else None,
            "investigations": [
                {
                    "title": item.title,
                    "status": item.status.value,
                    "priority": item.priority,
                    "related_open_questions": item.related_open_questions,
                }
                for item in (plan.investigations if plan else [])
            ],
            "open_questions": plan.open_questions if plan else [],
            "assumptions": plan.assumptions if plan else [],
        },
        "working_memory": {
            "objective": working.objective,
            "open_questions": working.open_questions,
            "visited_source_keys": working.visited_source_keys[-20:],
            "recent_evidence": [
                {
                    "kind": unit.kind.value,
                    "statement": unit.statement,
                    "topic": unit.topic,
                    "confidence": unit.confidence,
                    "trust_tier": unit.trust_tier.value,
                    "entities": unit.entities,
                }
                for unit in working.recent_evidence[-15:]
            ],
            "notes": working.notes[-10:],
            "active_task": (
                {
                    "title": working.active_task.title,
                    "description": working.active_task.description,
                    "priority": working.active_task.priority,
                }
                if working.active_task
                else None
            ),
        },
        "latest_tool_result": (
            latest_tool_result.model_dump(mode="json") if latest_tool_result else None
        ),
        "current_confidence": ctx.confidence.model_dump(mode="json"),
        "instruction": (
            "Return JSON with keys: answered_questions, new_questions, "
            "should_continue, strategy_should_change, strategy_change_summary, "
            "source_trust_notes, evidence_quality (0..1), notes."
        ),
    }
    return json.dumps(payload, indent=2, default=str)
