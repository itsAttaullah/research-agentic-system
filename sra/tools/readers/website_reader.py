"""Website reader — fetch a URL and extract readable text."""

from __future__ import annotations

from pydantic import BaseModel

from sra.core.errors import ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool
from sra.tools.http import HttpGateway
from sra.tools.readers.html_utils import html_to_text
from sra.tools.schemas import TextDocumentInput, TextDocumentOutput


class WebsiteReaderTool(BaseTool):
    name = "website_reader"
    description = (
        "Fetch a URL and extract readable page text. "
        "Use after search tools identify promising links. "
        "Prefer this over html_parser when you only have a URL (not raw HTML)."
    )
    input_schema = TextDocumentInput
    output_schema = TextDocumentOutput
    tags = ["fetch", "reader", "web"]

    def __init__(self, http: HttpGateway | None = None) -> None:
        self._http = http or HttpGateway()

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, TextDocumentInput)
        response = await self._http.get(
            payload.url,
            timeout_seconds=ctx.timeout_seconds,
            max_response_bytes=ctx.max_response_bytes,
        )
        if response.status_code >= 400:
            raise ToolExecutionError(
                f"Failed to fetch {payload.url}: HTTP {response.status_code}",
                details={"status_code": response.status_code},
            )
        title, content, _links = html_to_text(response.text, max_chars=payload.max_chars)
        if not content:
            raise ToolExecutionError(f"No readable text extracted from {payload.url}")
        return TextDocumentOutput(
            url=response.url,
            title=title,
            content=content,
            content_type=response.content_type,
            status_code=response.status_code,
        )
