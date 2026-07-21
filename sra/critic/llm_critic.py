"""LLM-backed Critic implementation — hard gate before report generation."""

from __future__ import annotations

from sra.core.context import RunContext
from sra.core.errors import CritiqueError, LLMError
from sra.core.ports.llm import LLMClient, LLMMessage, LLMRequest
from sra.core.structured import parse_llm_model
from sra.critic.assembly import draft_to_critique
from sra.critic.prompts import CRITIC_SYSTEM_PROMPT, critique_user_prompt
from sra.critic.schemas import DraftCritique
from sra.models.reflection import CritiqueResult

_SCHEMA_NAME = "DraftCritique"


class LLMCritic:
    """Critic port implementation driven by an injected LLMClient."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        temperature: float = 0.0,
        max_repair_attempts: int = 1,
    ) -> None:
        if max_repair_attempts < 0:
            msg = "max_repair_attempts cannot be negative"
            raise ValueError(msg)
        self._llm = llm
        self._temperature = temperature
        self._max_repair_attempts = max_repair_attempts

    async def critique(self, ctx: RunContext) -> CritiqueResult:
        draft = await self._request_draft(
            [
                LLMMessage(role="system", content=CRITIC_SYSTEM_PROMPT),
                LLMMessage(role="user", content=critique_user_prompt(ctx)),
            ]
        )
        try:
            return draft_to_critique(draft)
        except CritiqueError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise CritiqueError(
                "Failed to assemble critique result",
                details={"error": str(exc)},
            ) from exc

    async def _request_draft(self, messages: list[LLMMessage]) -> DraftCritique:
        attempt = 0
        conversation = list(messages)
        last_error: Exception | None = None

        while attempt <= self._max_repair_attempts:
            response = await self._llm.complete(
                LLMRequest(
                    messages=conversation,
                    temperature=self._temperature,
                    response_schema_name=_SCHEMA_NAME,
                    metadata={"component": "critic", "attempt": attempt},
                )
            )
            try:
                return parse_llm_model(response, DraftCritique)
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
                            "Return ONLY a corrected JSON object for DraftCritique."
                        ),
                    ),
                ]

        raise CritiqueError(
            "Critic could not obtain a valid structured result from the LLM",
            details={"error": str(last_error) if last_error else "unknown"},
        )
