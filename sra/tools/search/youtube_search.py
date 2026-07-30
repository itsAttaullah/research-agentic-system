"""YouTube search via the YouTube Data API v3."""

from __future__ import annotations

from pydantic import BaseModel

from sra.core.errors import ConfigurationError, ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool
from sra.tools.http import HttpGateway
from sra.tools.schemas import SearchHit, SearchInput, SearchOutput


class YouTubeSearchTool(BaseTool):
    name = "youtube_search"
    description = (
        "Search YouTube for talks/demos relevant to the query. "
        "Useful for product walkthroughs; weak for quantitative claims."
    )
    input_schema = SearchInput
    output_schema = SearchOutput
    tags = ["search", "youtube", "media"]

    def __init__(
        self,
        *,
        api_key: str | None,
        http: HttpGateway | None = None,
    ) -> None:
        self._api_key = api_key
        self._http = http or HttpGateway()

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, SearchInput)
        if not self._api_key:
            raise ConfigurationError(
                "YouTube Search requires YOUTUBE_API_KEY",
            )

        _response, body = await self._http.get_json(
            "https://www.googleapis.com/youtube/v3/search",
            timeout_seconds=ctx.timeout_seconds,
            max_response_bytes=ctx.max_response_bytes,
            params={
                "key": self._api_key,
                "part": "snippet",
                "q": payload.query,
                "type": "video",
                "maxResults": min(payload.limit, 25),
            },
        )
        if not isinstance(body, dict):
            raise ToolExecutionError("Unexpected YouTube Search payload")

        items = body.get("items") or []
        results: list[SearchHit] = []
        if isinstance(items, list):
            for item in items[: payload.limit]:
                if not isinstance(item, dict):
                    continue
                video_id = ""
                raw_id = item.get("id")
                if isinstance(raw_id, dict):
                    video_id = str(raw_id.get("videoId") or "")
                raw_snippet = item.get("snippet")
                snippet = raw_snippet if isinstance(raw_snippet, dict) else {}
                results.append(
                    SearchHit(
                        title=str(snippet.get("title") or ""),
                        url=f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
                        snippet=str(snippet.get("description") or "")[:400],
                        source="youtube",
                        published=str(snippet.get("publishedAt") or ""),
                        metadata={"channel": str(snippet.get("channelTitle") or "")},
                    )
                )
        return SearchOutput(query=payload.query, results=results)
