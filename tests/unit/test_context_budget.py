"""Unit tests for prompt context compaction helpers."""

from __future__ import annotations

from uuid import uuid4

from sra.core.context_budget import compact_json, compact_text, compact_tool_result
from sra.models.tools import ToolResult


def test_compact_text_marks_truncation() -> None:
    text = "x" * 100
    out = compact_text(text, max_chars=40)
    assert out.endswith("[truncated]")
    assert len(out) <= 40


def test_compact_json_limits_lists() -> None:
    payload = {"items": list(range(20)), "note": "a" * 500}
    compacted = compact_json(payload, max_chars=80, max_list_items=3)
    assert isinstance(compacted, dict)
    assert len(compacted["items"]) == 4  # 3 kept + omission marker


def test_compact_tool_result_truncates_document_body() -> None:
    result = ToolResult(
        call_id=uuid4(),
        tool_name="website_reader",
        success=True,
        output={"content": "body " * 2000, "title": "Doc"},
    )
    compacted = compact_tool_result(result, max_chars=200)
    assert compacted is not None
    assert (
        "truncated" in str(compacted["output"]["content"]).casefold()
        or len(str(compacted["output"]["content"])) <= 220
    )
