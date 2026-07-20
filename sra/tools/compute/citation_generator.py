"""Citation generator for research report references."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool


class CitationGeneratorInput(BaseModel):
    title: str = Field(min_length=1)
    url: str = ""
    authors: list[str] = Field(default_factory=list)
    published: str = ""
    publisher: str = ""
    accessed: str = ""
    style: Literal["apa", "markdown", "plain"] = "markdown"


class CitationGeneratorOutput(BaseModel):
    style: str
    citation: str


class CitationGeneratorTool(BaseTool):
    name = "citation_generator"
    description = "Format a bibliographic citation in APA, Markdown, or plain text."
    input_schema = CitationGeneratorInput
    output_schema = CitationGeneratorOutput
    tags = ["compute", "citation"]

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, CitationGeneratorInput)
        authors = ", ".join(payload.authors) if payload.authors else "Unknown author"
        if payload.style == "apa":
            citation = (
                f"{authors} ({payload.published or 'n.d.'}). {payload.title}. "
                f"{payload.publisher + '. ' if payload.publisher else ''}"
                f"{payload.url}"
            ).strip()
        elif payload.style == "markdown":
            label = payload.title
            citation = f"[{label}]({payload.url})" if payload.url else label
            if payload.published or authors != "Unknown author":
                citation += f" — {authors}"
                if payload.published:
                    citation += f" ({payload.published})"
        else:
            parts = [authors, payload.title]
            if payload.publisher:
                parts.append(payload.publisher)
            if payload.published:
                parts.append(payload.published)
            if payload.url:
                parts.append(payload.url)
            if payload.accessed:
                parts.append(f"accessed {payload.accessed}")
            citation = ". ".join(part for part in parts if part)

        return CitationGeneratorOutput(style=payload.style, citation=citation.strip())
