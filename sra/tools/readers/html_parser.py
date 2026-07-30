"""HTML parser — parse raw HTML into text and links."""

from __future__ import annotations

from pydantic import BaseModel

from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool
from sra.tools.readers.html_utils import html_to_text
from sra.tools.schemas import ParseTextInput, ParseTextOutput


class HtmlParserTool(BaseTool):
    name = "html_parser"
    description = (
        "Parse raw HTML you already have into title, visible text, and links. "
        "Do not use when you only have a URL — use website_reader instead."
    )
    input_schema = ParseTextInput
    output_schema = ParseTextOutput
    tags = ["parse", "html"]

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, ParseTextInput)
        title, content, links = html_to_text(payload.text, max_chars=payload.max_chars)
        return ParseTextOutput(title=title, content=content, links=links)
