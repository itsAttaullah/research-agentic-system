"""Google Programmable Search tool."""

from __future__ import annotations

from pydantic import BaseModel

from sra.core.errors import ConfigurationError, ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool
from sra.tools.http import HttpGateway
from sra.tools.schemas import SearchHit, SearchInput, SearchOutput


class GoogleSearchTool(BaseTool):
    name = "google_search"
    description = (
        "Search the general public web for discovery. "
        "Use for broad fact-finding and finding candidate URLs. "
        "Prefer news_search for recent coverage and academic_paper_search for papers. "
        "Input: natural-language query + limit."
    )
    input_schema = SearchInput
    output_schema = SearchOutput
    tags = ["search", "web"]

    def __init__(
        self,
        *,
        api_key: str | None,
        cx: str | None,
        http: HttpGateway | None = None,
    ) -> None:
        self._api_key = api_key
        self._cx = cx
        self._http = http or HttpGateway()

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, SearchInput)
        if not self._api_key or not self._cx:
            raise ConfigurationError(
                "Google Search requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CX",
            )

        _response, body = await self._http.get_json(
            "https://www.googleapis.com/customsearch/v1",
            timeout_seconds=ctx.timeout_seconds,
            max_response_bytes=ctx.max_response_bytes,
            params={
                "key": self._api_key,
                "cx": self._cx,
                "q": payload.query,
                "num": min(payload.limit, 10),
            },
        )
        if not isinstance(body, dict):
            raise ToolExecutionError("Unexpected Google Search payload")

        items = body.get("items") or []
        results: list[SearchHit] = []
        if isinstance(items, list):
            for item in items[: payload.limit]:
                if not isinstance(item, dict):
                    continue
                results.append(
                    SearchHit(
                        title=str(item.get("title") or ""),
                        url=str(item.get("link") or ""),
                        snippet=str(item.get("snippet") or ""),
                        source="google",
                    )
                )
        return SearchOutput(query=payload.query, results=results)
