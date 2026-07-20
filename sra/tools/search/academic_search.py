"""Academic paper search via the Semantic Scholar Graph API."""

from __future__ import annotations

from pydantic import BaseModel

from sra.core.errors import ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool
from sra.tools.http import HttpGateway
from sra.tools.schemas import SearchHit, SearchInput, SearchOutput


class AcademicPaperSearchTool(BaseTool):
    name = "academic_paper_search"
    description = "Search academic papers using Semantic Scholar."
    input_schema = SearchInput
    output_schema = SearchOutput
    tags = ["search", "academic"]

    def __init__(self, http: HttpGateway | None = None) -> None:
        self._http = http or HttpGateway()

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, SearchInput)
        _response, body = await self._http.get_json(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            timeout_seconds=ctx.timeout_seconds,
            max_response_bytes=ctx.max_response_bytes,
            params={
                "query": payload.query,
                "limit": payload.limit,
                "fields": "title,url,abstract,year,authors,externalIds",
            },
        )
        if not isinstance(body, dict):
            raise ToolExecutionError("Unexpected Semantic Scholar payload")

        data = body.get("data") or []
        results: list[SearchHit] = []
        if isinstance(data, list):
            for item in data[: payload.limit]:
                if not isinstance(item, dict):
                    continue
                authors = item.get("authors") or []
                author_names = []
                if isinstance(authors, list):
                    author_names = [
                        str(author.get("name"))
                        for author in authors
                        if isinstance(author, dict) and author.get("name")
                    ]
                results.append(
                    SearchHit(
                        title=str(item.get("title") or ""),
                        url=str(item.get("url") or ""),
                        snippet=str(item.get("abstract") or "")[:500],
                        source="semantic_scholar",
                        published=str(item.get("year") or ""),
                        metadata={"authors": ", ".join(author_names[:5])},
                    )
                )
        return SearchOutput(query=payload.query, results=results)
