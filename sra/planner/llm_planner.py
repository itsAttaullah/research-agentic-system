"""LLM-backed Planner implementation.

The model chooses investigations; this class only requests structured output,
validates it, and maps it onto durable ResearchPlan objects.
"""

from __future__ import annotations

from sra.core.context import RunContext
from sra.core.errors import LLMError, PlanningError
from sra.core.ports.llm import LLMClient, LLMMessage, LLMRequest
from sra.core.structured import parse_llm_model
from sra.models.plan import ResearchPlan
from sra.models.reflection import CritiqueResult, ReflectionResult
from sra.planner.assembly import apply_draft_revision, draft_to_plan
from sra.planner.prompts import (
    PLANNER_SYSTEM_PROMPT,
    create_plan_user_prompt,
    revise_plan_user_prompt,
)
from sra.planner.schemas import DraftPlan

_SCHEMA_NAME = "DraftPlan"


class LLMPlanner:
    """Planner port implementation driven by an injected :class:`LLMClient`."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        temperature: float = 0.2,
        max_repair_attempts: int = 1,
    ) -> None:
        if max_repair_attempts < 0:
            msg = "max_repair_attempts cannot be negative"
            raise ValueError(msg)
        self._llm = llm
        self._temperature = temperature
        self._max_repair_attempts = max_repair_attempts

    async def create_plan(self, ctx: RunContext) -> ResearchPlan:
        draft = await self._request_draft(
            [
                LLMMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
                LLMMessage(role="user", content=create_plan_user_prompt(ctx)),
            ]
        )
        try:
            return draft_to_plan(draft)
        except PlanningError:
            raise
        except Exception as exc:  # noqa: BLE001 - map unexpected assembly failures
            raise PlanningError(
                "Failed to assemble initial research plan",
                details={"error": str(exc)},
            ) from exc

    async def revise_plan(
        self,
        ctx: RunContext,
        *,
        reason: str,
        reflection: ReflectionResult | None = None,
        critique: CritiqueResult | None = None,
    ) -> ResearchPlan:
        current = ctx.plan
        if current is None:
            # First revision without a prior plan is treated as create.
            return await self.create_plan(ctx)

        triggered_by = (
            "critic" if critique is not None else "reflection" if reflection else "planner"
        )
        draft = await self._request_draft(
            [
                LLMMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=revise_plan_user_prompt(
                        ctx,
                        reason=reason,
                        current_plan=current,
                        reflection=reflection,
                        critique=critique,
                    ),
                ),
            ]
        )
        try:
            return apply_draft_revision(
                current,
                draft,
                reason=reason,
                triggered_by=triggered_by,
            )
        except PlanningError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PlanningError(
                "Failed to assemble revised research plan",
                details={"error": str(exc)},
            ) from exc

    async def _request_draft(self, messages: list[LLMMessage]) -> DraftPlan:
        attempt = 0
        conversation = list(messages)
        last_error: Exception | None = None

        while attempt <= self._max_repair_attempts:
            response = await self._llm.complete(
                LLMRequest(
                    messages=conversation,
                    temperature=self._temperature,
                    response_schema_name=_SCHEMA_NAME,
                    metadata={"component": "planner", "attempt": attempt},
                )
            )
            try:
                return parse_llm_model(response, DraftPlan)
            except LLMError as exc:
                last_error = exc
                attempt += 1
                if attempt > self._max_repair_attempts:
                    break
                conversation = [
                    *messages,
                    LLMMessage(role="assistant", content=response.content),
                    LLMMessage(
                        role="user",
                        content=(
                            "Your previous response was invalid. "
                            f"Error: {exc.message}. "
                            "Return ONLY a corrected JSON object for DraftPlan."
                        ),
                    ),
                ]

        raise PlanningError(
            "Planner could not obtain a valid structured plan from the LLM",
            details={"error": str(last_error) if last_error else "unknown"},
        )
