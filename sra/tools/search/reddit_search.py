"""Reddit search via the public JSON search endpoint."""

from __future__ import annotations

from pydantic import BaseModel

from sra.core.errors import ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool
from sra.tools.http import HttpGateway
from sra.tools.schemas import SearchHit, SearchInput, SearchOutput


class RedditSearchTool(BaseTool):
    name = "reddit_search"
    description = (
        "Search Reddit discussions for practitioner anecdotes and objections. "
        "Treat results as weak evidence unless corroborated elsewhere."
    )
    input_schema = SearchInput
    output_schema = SearchOutput
    tags = ["search", "community"]

    def __init__(self, http: HttpGateway | None = None) -> None:
        self._http = http or HttpGateway()

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, SearchInput)
        _response, body = await self._http.get_json(
            "https://www.reddit.com/search.json",
            timeout_seconds=ctx.timeout_seconds,
            max_response_bytes=ctx.max_response_bytes,
            headers={"Accept": "application/json"},
            params={
                "q": payload.query,
                "limit": payload.limit,
                "sort": "relevance",
                "type": "link",
            },
        )
        if not isinstance(body, dict):
            raise ToolExecutionError("Unexpected Reddit payload")

        data = body.get("data") or {}
        children = data.get("children") if isinstance(data, dict) else []
        results: list[SearchHit] = []
        if isinstance(children, list):
            for child in children[: payload.limit]:
                if not isinstance(child, dict):
                    continue
                post = child.get("data") or {}
                if not isinstance(post, dict):
                    continue
                permalink = str(post.get("permalink") or "")
                url = (
                    f"https://www.reddit.com{permalink}"
                    if permalink
                    else str(post.get("url") or "")
                )
                results.append(
                    SearchHit(
                        title=str(post.get("title") or ""),
                        url=url,
                        snippet=str(post.get("selftext") or "")[:400],
                        source=f"reddit:{post.get('subreddit', '')}",
                        published=str(post.get("created_utc") or ""),
                        metadata={"score": str(post.get("score") or "")},
                    )
                )
        return SearchOutput(query=payload.query, results=results)
