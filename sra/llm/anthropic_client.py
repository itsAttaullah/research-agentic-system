"""Anthropic Messages API adapter."""

from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic

from sra.core.errors import ConfigurationError, LLMError
from sra.core.ports.llm import LLMMessage, LLMRequest, LLMResponse
from sra.llm.json_utils import extract_json_object


class AnthropicLLMClient:
    """LLMClient backed by the Anthropic SDK."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: AsyncAnthropic | None = None,
    ) -> None:
        if not api_key.strip():
            raise ConfigurationError("ANTHROPIC_API_KEY is required for the Anthropic provider")
        self._model = model
        self._client = client or AsyncAnthropic(api_key=api_key)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self._model
        system, messages = _split_system(request.messages)
        if request.response_schema_name:
            system = (
                f"{system}\n\nReturn ONLY a valid JSON object for schema "
                f"{request.response_schema_name}."
            ).strip()

        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 4096,
        }
        if system:
            create_kwargs["system"] = system

        try:
            response = await self._client.messages.create(**create_kwargs)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(
                "Anthropic completion failed",
                details={"error": str(exc), "model": model},
            ) from exc

        content_parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                content_parts.append(text)
        content = "\n".join(content_parts).strip()
        usage = response.usage
        return LLMResponse(
            content=content,
            raw_json=extract_json_object(content),
            model=response.model or model,
            prompt_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        )


def _split_system(messages: list[LLMMessage]) -> tuple[str, list[dict[str, str]]]:
    system_chunks: list[str] = []
    converted: list[dict[str, str]] = []
    for message in messages:
        if message.role == "system":
            system_chunks.append(message.content)
            continue
        role = "assistant" if message.role == "assistant" else "user"
        converted.append({"role": role, "content": message.content})
    if not converted:
        converted.append({"role": "user", "content": "Return the requested JSON object."})
    return "\n\n".join(system_chunks).strip(), converted
