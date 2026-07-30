"""Truncate nested payloads so long-horizon prompts stay within an attention budget."""

from __future__ import annotations

from typing import Any

from sra.models.tools import ToolResult


def compact_text(value: str, *, max_chars: int) -> str:
    """Keep the head of ``value`` and mark truncation explicitly."""
    if max_chars < 1:
        return ""
    text = value.strip()
    if len(text) <= max_chars:
        return text
    marker = "…[truncated]"
    keep = max(0, max_chars - len(marker))
    return f"{text[:keep]}{marker}"


def compact_json(value: Any, *, max_chars: int = 2_000, max_list_items: int = 8) -> Any:
    """Recursively shrink JSON-like structures for prompt inclusion."""
    if isinstance(value, str):
        return compact_text(value, max_chars=max_chars)
    if isinstance(value, dict):
        return {
            str(key): compact_json(item, max_chars=max_chars, max_list_items=max_list_items)
            for key, item in value.items()
        }
    if isinstance(value, list):
        trimmed = value[:max_list_items]
        compacted = [
            compact_json(item, max_chars=max(200, max_chars // 2), max_list_items=max_list_items)
            for item in trimmed
        ]
        omitted = len(value) - len(trimmed)
        if omitted > 0:
            compacted.append(f"…[{omitted} more items omitted]")
        return compacted
    return value


def compact_tool_result(
    result: ToolResult | None,
    *,
    max_chars: int = 2_500,
) -> dict[str, Any] | None:
    """Serialize a tool result for LLM context without dumping full documents."""
    if result is None:
        return None
    return {
        "tool_name": result.tool_name,
        "success": result.success,
        "error": result.error,
        "duration_ms": result.duration_ms,
        "output": compact_json(result.output, max_chars=max_chars, max_list_items=8),
    }
