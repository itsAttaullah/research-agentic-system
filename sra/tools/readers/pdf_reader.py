"""PDF reader using PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import fitz
from pydantic import BaseModel, Field, model_validator

from sra.core.errors import ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool
from sra.tools.http import HttpGateway


class PdfReaderInput(BaseModel):
    path: str | None = None
    url: str | None = None
    max_chars: int = Field(default=30_000, ge=500, le=300_000)
    max_pages: int = Field(default=25, ge=1, le=100)

    @model_validator(mode="after")
    def require_source(self) -> PdfReaderInput:
        if not self.path and not self.url:
            raise ValueError("Provide either path or url")
        return self


class PdfReaderOutput(BaseModel):
    source: str
    page_count: int
    content: str


class PdfReaderTool(BaseTool):
    name = "pdf_reader"
    description = "Extract text from a local PDF path or a PDF URL."
    input_schema = PdfReaderInput
    output_schema = PdfReaderOutput
    tags = ["reader", "pdf", "document"]

    def __init__(self, http: HttpGateway | None = None) -> None:
        self._http = http or HttpGateway()

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, PdfReaderInput)
        if payload.path:
            path = Path(payload.path)
            if not path.is_file():
                raise ToolExecutionError(f"PDF not found: {payload.path}")
            data = path.read_bytes()
            source = str(path)
        else:
            assert payload.url is not None
            response = await self._http.get(
                payload.url,
                timeout_seconds=ctx.timeout_seconds,
                max_response_bytes=ctx.max_response_bytes,
            )
            if response.status_code >= 400:
                raise ToolExecutionError(
                    f"Failed to download PDF: HTTP {response.status_code}",
                )
            data = response.content
            source = response.url

        try:
            document = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:  # noqa: BLE001
            raise ToolExecutionError(f"Could not open PDF: {exc}") from exc

        chunks: list[str] = []
        page_count = document.page_count
        try:
            for page_index in range(min(page_count, payload.max_pages)):
                chunks.append(document.load_page(page_index).get_text("text"))
        finally:
            document.close()

        content = "\n\n".join(part.strip() for part in chunks if part.strip())
        if not content:
            raise ToolExecutionError("PDF contained no extractable text")
        if len(content) > payload.max_chars:
            content = content[: payload.max_chars].rstrip() + "…"
        return PdfReaderOutput(source=source, page_count=page_count, content=content)
