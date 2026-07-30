"""Prompt construction for the research planner.

Prompts describe the *job* of planning; they do not hardcode a fixed
investigation checklist for any industry or question type.
"""

from __future__ import annotations

import json

from sra.core.context import RunContext
from sra.models.plan import ResearchPlan
from sra.models.reflection import CritiqueResult, ReflectionResult

PLANNER_SYSTEM_PROMPT = """\
You are the Planner for an autonomous Strategic Research Agent.

Your job is to convert a research goal into a structured investigation plan,
and later revise that plan when new evidence, reflection, or critique arrives.

## Rules
- Decide WHAT to investigate based on the goal. Do not invent tool calls.
- Prefer concrete, evidence-seeking investigations over vague themes.
- Include open questions the agent still needs to answer.
- Call out assumptions and out-of-scope items explicitly.
- Prioritize investigations from 0-100 (higher = more urgent).

## Judgment heuristics
- Cover decision-critical unknowns first (market reality, alternatives,
  constraints, risks) before nice-to-have color.
- When revising, keep investigations that still have unanswered success criteria;
  cancel only clearly obsolete or duplicated threads.
- suggested_tools should be narrow hints (e.g. academic_paper_search), not a laundry list.
- Return ONLY valid JSON matching the required schema. No markdown.
"""


def create_plan_user_prompt(ctx: RunContext) -> str:
    goal = ctx.goal
    payload = {
        "question": goal.question,
        "constraints": goal.constraints,
        "success_criteria": goal.success_criteria,
        "instruction": (
            "Produce an initial research plan as JSON with keys: "
            "goal_summary, investigations, open_questions, assumptions, "
            "out_of_scope, revision_summary. "
            "Each investigation needs: title, rationale, hypotheses, "
            "success_criteria, priority, related_open_questions, suggested_tools."
        ),
    }
    return json.dumps(payload, indent=2, default=str)


def revise_plan_user_prompt(
    ctx: RunContext,
    *,
    reason: str,
    current_plan: ResearchPlan,
    reflection: ReflectionResult | None,
    critique: CritiqueResult | None,
) -> str:
    payload = {
        "reason": reason,
        "research_goal": {
            "question": ctx.goal.question,
            "constraints": ctx.goal.constraints,
            "success_criteria": ctx.goal.success_criteria,
        },
        "current_plan": current_plan.model_dump(mode="json"),
        "working_memory": {
            "open_questions": ctx.memory.working.open_questions,
            "visited_source_keys": ctx.memory.working.visited_source_keys,
            "recent_notes": ctx.memory.working.notes[-10:],
        },
        "confidence": ctx.confidence.model_dump(mode="json"),
        "reflection": reflection.model_dump(mode="json") if reflection else None,
        "critique": critique.model_dump(mode="json") if critique else None,
        "instruction": (
            "Revise the research plan. Keep useful investigations, cancel or "
            "replace weak ones, add investigations for new gaps, and set "
            "revision_summary to explain the change. Return the full updated "
            "plan JSON (same schema as create)."
        ),
    }
    return json.dumps(payload, indent=2, default=str)
