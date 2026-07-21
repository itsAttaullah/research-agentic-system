"""LLM-backed Reflection Engine implementation."""

from __future__ import annotations

from sra.core.context import RunContext
from sra.core.errors import LLMError, ReflectionError
from sra.core.ports.llm import LLMClient, LLMMessage, LLMRequest
from sra.core.structured import parse_llm_model
from sra.models.reflection import ReflectionResult
from sra.models.tools import ToolResult
from sra.reflection.assembly import draft_to_reflection
from sra.reflection.prompts import REFLECTION_SYSTEM_PROMPT, reflection_user_prompt
from sra.reflection.schemas import DraftReflection

_SCHEMA_NAME = "DraftReflection"


class LLMReflectionEngine:
    """ReflectionEngine port implementation driven by an injected LLMClient."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        temperature: float = 0.1,
        max_repair_attempts: int = 1,
    ) -> None:
        if max_repair_attempts < 0:
            msg = "max_repair_attempts cannot be negative"
            raise ValueError(msg)
        self._llm = llm
        self._temperature = temperature
        self._max_repair_attempts = max_repair_attempts

    async def reflect(
        self,
        ctx: RunContext,
        *,
        latest_tool_result: ToolResult | None = None,
    ) -> ReflectionResult:
        draft = await self._request_draft(
            [
                LLMMessage(role="system", content=REFLECTION_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=reflection_user_prompt(
                        ctx,
                        latest_tool_result=latest_tool_result,
                    ),
                ),
            ]
        )
        try:
            return draft_to_reflection(draft)
        except ReflectionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ReflectionError(
                "Failed to assemble reflection result",
                details={"error": str(exc)},
            ) from exc

    async def _request_draft(self, messages: list[LLMMessage]) -> DraftReflection:
        attempt = 0
        conversation = list(messages)
        last_error: Exception | None = None

        while attempt <= self._max_repair_attempts:
            response = await self._llm.complete(
                LLMRequest(
                    messages=conversation,
                    temperature=self._temperature,
                    response_schema_name=_SCHEMA_NAME,
                    metadata={"component": "reflection", "attempt": attempt},
                )
            )
            try:
                return parse_llm_model(response, DraftReflection)
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
                            "Return ONLY a corrected JSON object for DraftReflection."
                        ),
                    ),
                ]

        raise ReflectionError(
            "Reflection Engine could not obtain a valid structured result from the LLM",
            details={"error": str(last_error) if last_error else "unknown"},
        )
