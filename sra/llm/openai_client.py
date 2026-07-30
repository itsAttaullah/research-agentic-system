"""OpenAI Chat Completions adapter."""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from sra.core.errors import ConfigurationError, LLMError
from sra.core.ports.llm import LLMRequest, LLMResponse
from sra.llm.json_utils import extract_json_object


class OpenAILLMClient:
    """LLMClient backed by the OpenAI SDK."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: AsyncOpenAI | None = None,
    ) -> None:
        if not api_key.strip():
            raise ConfigurationError("OPENAI_API_KEY is required for the OpenAI provider")
        self._model = model
        self._client = client or AsyncOpenAI(api_key=api_key)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self._model
        messages: list[dict[str, str]] = [
            {"role": message.role, "content": message.content} for message in request.messages
        ]
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            create_kwargs["max_tokens"] = request.max_tokens
        if request.response_schema_name:
            create_kwargs["response_format"] = {"type": "json_object"}

        try:
            completion = await self._client.chat.completions.create(**create_kwargs)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(
                "OpenAI completion failed",
                details={"error": str(exc), "model": model},
            ) from exc

        choice = completion.choices[0].message.content or ""
        usage = completion.usage
        return LLMResponse(
            content=choice,
            raw_json=extract_json_object(choice),
            model=completion.model or model,
            prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )
