"""Prompt construction for the Critic gate."""

from __future__ import annotations

import json

from sra.core.context import RunContext

CRITIC_SYSTEM_PROMPT = """\
You are the Critic for an autonomous Strategic Research Agent.

You are the hard quality gate before any final report is generated.
Critique the research state for:

1. Missing evidence
2. Weak assumptions
3. Unsupported claims
4. Bias or one-sided sourcing
5. Incomplete research relative to the goal and plan

Rules:
- Pass only if the evidence is strong enough for a professional recommendation.
- If research is incomplete or weakly supported, set passed=false and forced_replan=true.
- Provide concrete replan_directives the Planner can act on.
- Finding codes should be snake_case (e.g. missing_evidence, weak_assumption, bias).
- Severity must be one of: low, medium, high, blocker.
- Return ONLY valid JSON matching the required schema. No markdown.
"""


def critique_user_prompt(ctx: RunContext) -> str:
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
            "version": plan.version if plan else None,
            "investigations": [
                {
                    "title": item.title,
                    "status": item.status.value,
                    "priority": item.priority,
                    "success_criteria": item.success_criteria,
                    "hypotheses": item.hypotheses,
                }
                for item in (plan.investigations if plan else [])
            ],
            "open_questions": plan.open_questions if plan else [],
            "assumptions": plan.assumptions if plan else [],
            "out_of_scope": plan.out_of_scope if plan else [],
        },
        "working_memory": {
            "open_questions": working.open_questions,
            "visited_source_count": len(working.visited_source_keys),
            "recent_evidence": [
                {
                    "kind": unit.kind.value,
                    "statement": unit.statement,
                    "topic": unit.topic,
                    "confidence": unit.confidence,
                    "trust_tier": unit.trust_tier.value,
                    "entities": unit.entities,
                }
                for unit in working.recent_evidence[-25:]
            ],
            "notes": working.notes[-10:],
        },
        "confidence": ctx.confidence.model_dump(mode="json"),
        "last_reflection": (
            ctx.last_reflection.model_dump(mode="json") if ctx.last_reflection else None
        ),
        "tool_history_summary": {
            "total_calls": len(ctx.tool_history),
            "successful_calls": sum(1 for item in ctx.tool_history if item.success),
            "failed_calls": sum(1 for item in ctx.tool_history if not item.success),
            "recent_tools": [item.tool_name for item in ctx.tool_history[-10:]],
        },
        "instruction": (
            "Return JSON with keys: passed, findings, forced_replan, "
            "replan_directives, summary. Each finding needs code, severity, "
            "message, related_topics."
        ),
    }
    return json.dumps(payload, indent=2, default=str)
