"""Prompt construction for the Research Engine."""

from __future__ import annotations

import json

from sra.core.context import RunContext
from sra.models.tools import ToolDescriptor

RESEARCH_ENGINE_SYSTEM_PROMPT = """\
You are the Research Engine for an autonomous Strategic Research Agent.

Propose exactly ONE next action for the runtime to validate and execute.
You do not execute tools yourself.

## Allowed action kinds
- invoke_tool
- update_plan
- reflect
- request_critic
- finalize

## Judgment heuristics
- Prefer search tools to discover sources; then use reader tools on the best URLs.
- Do not re-search the same query/source pair if it is already in visited sources.
- If open questions remain and confidence is low, gather evidence — do not finalize.
- If evidence is contradictory, prefer reflect or update_plan over finalize.
- Request critic when the main investigations have supporting evidence and open
  questions are mostly answered; use finalize only after a successful critic path
  is the intended terminal move from your side (prefer request_critic first).
- Use calculator/table/citation tools only when they materially help the answer.
- Prefer the narrowest tool that fits: academic_paper_search for papers,
  news_search for recent coverage, google_search for general web discovery,
  github_search for software/repos, reddit_search for practitioner anecdotes.

## Output rules
- Use only tool names from the provided catalog.
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
        "plan_summary": {
            "goal_summary": ctx.plan.goal_summary if ctx.plan else None,
            "version": ctx.plan.version if ctx.plan else None,
            "investigations": [
                {
                    "title": item.title,
                    "status": item.status.value,
                    "priority": item.priority,
                }
                for item in (ctx.plan.investigations if ctx.plan else [])[:12]
            ],
            "open_questions": (ctx.plan.open_questions if ctx.plan else [])[:12],
        },
        "active_tasks": [
            {
                "title": task.title,
                "status": task.status.value,
                "priority": task.priority,
                "suggested_tools": task.suggested_tools,
            }
            for task in ctx.tasks[:12]
            if task.status.value in {"pending", "in_progress"}
        ],
        "open_questions": working.open_questions[:20],
        "visited_source_keys": working.visited_source_keys[-20:],
        "recent_evidence": [
            {
                "kind": unit.kind.value,
                "statement": unit.statement,
                "topic": unit.topic,
                "confidence": unit.confidence,
                "trust_tier": unit.trust_tier.value,
            }
            for unit in working.recent_evidence[-8:]
        ],
        "confidence": {
            "overall": ctx.confidence.overall,
            "low_topics": [
                {"topic": topic.topic, "score": topic.score}
                for topic in ctx.confidence.topics
                if topic.score < 0.7 or topic.needs_more_research
            ][:10],
        },
        "last_reflection_notes": (
            {
                "should_continue": ctx.last_reflection.should_continue,
                "new_questions": ctx.last_reflection.new_questions[:8],
                "notes": ctx.last_reflection.notes,
                "evidence_quality": ctx.last_reflection.evidence_quality,
            }
            if ctx.last_reflection
            else None
        ),
        "budget": {
            "remaining_iterations": ctx.budget.remaining_iterations(),
            "iterations": ctx.budget.usage.iterations,
            "sources_visited": ctx.budget.usage.sources_visited,
        },
        "available_tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "tags": tool.tags,
            }
            for tool in available_tools
        ],
        "instruction": (
            "Return JSON with kind and fields required for that kind. "
            "For invoke_tool include tool_name and arguments. "
            "For finalize/request_critic include reason/summary as appropriate."
        ),
    }
    return json.dumps(payload, indent=2, default=str)
