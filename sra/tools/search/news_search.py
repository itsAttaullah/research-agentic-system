"""News search via Google Programmable Search with news-oriented querying."""

from __future__ import annotations

from pydantic import BaseModel

from sra.core.errors import ConfigurationError, ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool
from sra.tools.http import HttpGateway
from sra.tools.schemas import SearchHit, SearchInput, SearchOutput


class NewsSearchTool(BaseTool):
    name = "news_search"
    description = (
        "Search recent news coverage (not the full historical web). "
        "Use when recency matters: launches, regulations, funding, incidents. "
        "Do not use for evergreen background research — prefer google_search."
    )
    input_schema = SearchInput
    output_schema = SearchOutput
    tags = ["search", "news"]

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
                "News Search requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CX",
            )

        query = f"{payload.query} news"
        _response, body = await self._http.get_json(
            "https://www.googleapis.com/customsearch/v1",
            timeout_seconds=ctx.timeout_seconds,
            max_response_bytes=ctx.max_response_bytes,
            params={
                "key": self._api_key,
                "cx": self._cx,
                "q": query,
                "num": min(payload.limit, 10),
                "dateRestrict": "m6",
            },
        )
        if not isinstance(body, dict):
            raise ToolExecutionError("Unexpected News Search payload")

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
                        source="news",
                        published=_extract_published(item),
                    )
                )
        return SearchOutput(query=payload.query, results=results)


def _extract_published(item: dict[object, object]) -> str:
    pagemap = item.get("pagemap")
    if not isinstance(pagemap, dict):
        return ""
    metatags = pagemap.get("metatags")
    if not isinstance(metatags, list) or not metatags:
        return ""
    first = metatags[0]
    if not isinstance(first, dict):
        return ""
    value = first.get("article:published_time") or first.get("og:updated_time") or ""
    return str(value)
