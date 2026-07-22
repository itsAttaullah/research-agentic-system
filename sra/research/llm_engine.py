"""LLM-backed Research Engine — proposes the next validated AgentAction."""

from __future__ import annotations

from sra.core.context import RunContext
from sra.core.errors import InvalidActionError, LLMError
from sra.core.ports.llm import LLMClient, LLMMessage, LLMRequest
from sra.core.structured import parse_llm_model
from sra.models.actions import AgentAction
from sra.models.tools import ToolDescriptor
from sra.research.assembly import draft_to_action
from sra.research.prompts import RESEARCH_ENGINE_SYSTEM_PROMPT, propose_action_user_prompt
from sra.research.schemas import DraftAgentAction

_SCHEMA_NAME = "DraftAgentAction"


class LLMResearchEngine:
    """ResearchEngine port implementation driven by an injected LLMClient."""

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

    async def propose_action(
        self,
        ctx: RunContext,
        *,
        available_tools: list[ToolDescriptor],
    ) -> AgentAction:
        draft = await self._request_draft(
            [
                LLMMessage(role="system", content=RESEARCH_ENGINE_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=propose_action_user_prompt(
                        ctx,
                        available_tools=available_tools,
                    ),
                ),
            ]
        )
        try:
            return draft_to_action(draft)
        except InvalidActionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise InvalidActionError(
                "Failed to assemble agent action from research engine draft",
                details={"error": str(exc)},
            ) from exc

    async def _request_draft(self, messages: list[LLMMessage]) -> DraftAgentAction:
        attempt = 0
        conversation = list(messages)
        last_error: Exception | None = None

        while attempt <= self._max_repair_attempts:
            response = await self._llm.complete(
                LLMRequest(
                    messages=conversation,
                    temperature=self._temperature,
                    response_schema_name=_SCHEMA_NAME,
                    metadata={"component": "research_engine", "attempt": attempt},
                )
            )
            try:
                return parse_llm_model(response, DraftAgentAction)
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
                            "Return ONLY a corrected JSON object for DraftAgentAction."
                        ),
                    ),
                ]

        raise InvalidActionError(
            "Research Engine could not obtain a valid structured action from the LLM",
            details={"error": str(last_error) if last_error else "unknown"},
        )
