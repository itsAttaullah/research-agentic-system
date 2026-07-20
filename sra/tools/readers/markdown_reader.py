"""Markdown reader — load markdown from string or local file path."""

from __future__ import annotations

from pathlib import Path

import markdown as md
from pydantic import BaseModel, Field, model_validator

from sra.core.errors import ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool
from sra.tools.readers.html_utils import html_to_text


class MarkdownReaderInput(BaseModel):
    text: str | None = None
    path: str | None = None
    max_chars: int = Field(default=20_000, ge=100, le=200_000)

    @model_validator(mode="after")
    def require_source(self) -> MarkdownReaderInput:
        if not self.text and not self.path:
            raise ValueError("Provide either text or path")
        return self


class MarkdownReaderOutput(BaseModel):
    path: str | None = None
    content: str
    rendered_text: str


class MarkdownReaderTool(BaseTool):
    name = "markdown_reader"
    description = "Read markdown from text or a local file and return raw + rendered text."
    input_schema = MarkdownReaderInput
    output_schema = MarkdownReaderOutput
    tags = ["reader", "markdown", "local"]

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, MarkdownReaderInput)
        if payload.path:
            path = Path(payload.path)
            if not path.is_file():
                raise ToolExecutionError(f"Markdown file not found: {payload.path}")
            content = path.read_text(encoding="utf-8")
        else:
            content = payload.text or ""

        if len(content) > payload.max_chars:
            content = content[: payload.max_chars].rstrip() + "…"

        html = md.markdown(content)
        _title, rendered, _links = html_to_text(html, max_chars=payload.max_chars)
        return MarkdownReaderOutput(
            path=payload.path,
            content=content,
            rendered_text=rendered,
        )
