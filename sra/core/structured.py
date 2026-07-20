"""Shared helpers for parsing structured LLM JSON into Pydantic models."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from sra.core.errors import LLMError
from sra.core.ports.llm import LLMResponse

T = TypeVar("T", bound=BaseModel)


def parse_llm_model(response: LLMResponse, model_type: type[T]) -> T:
    """Parse ``raw_json`` or JSON ``content`` into ``model_type``.

    Raises:
        LLMError: if the payload is missing, malformed, or fails validation.
    """
    payload = response.raw_json
    if payload is None:
        payload = _load_json_object(response.content)
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise LLMError(
            f"LLM response failed {model_type.__name__} validation",
            details={"errors": exc.errors()},
        ) from exc


def _load_json_object(content: str) -> dict[str, object]:
    text = content.strip()
    if not text:
        raise LLMError("LLM returned an empty response")

    # Tolerate fenced markdown blocks from models that ignore instructions.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(
            "LLM returned non-JSON content",
            details={"content_preview": text[:500]},
        ) from exc

    if not isinstance(loaded, dict):
        raise LLMError(
            "LLM JSON payload must be an object",
            details={"type": type(loaded).__name__},
        )
    return loaded
