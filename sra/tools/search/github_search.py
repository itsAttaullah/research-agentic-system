"""GitHub repository search."""

from __future__ import annotations

from pydantic import BaseModel

from sra.core.errors import ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool
from sra.tools.http import HttpGateway
from sra.tools.schemas import SearchHit, SearchInput, SearchOutput


class GitHubSearchTool(BaseTool):
    name = "github_search"
    description = "Search GitHub repositories relevant to a research query."
    input_schema = SearchInput
    output_schema = SearchOutput
    tags = ["search", "github", "code"]

    def __init__(
        self,
        *,
        token: str | None = None,
        http: HttpGateway | None = None,
    ) -> None:
        self._token = token
        self._http = http or HttpGateway()

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, SearchInput)
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        _response, body = await self._http.get_json(
            "https://api.github.com/search/repositories",
            timeout_seconds=ctx.timeout_seconds,
            max_response_bytes=ctx.max_response_bytes,
            headers=headers,
            params={
                "q": payload.query,
                "per_page": payload.limit,
                "sort": "stars",
                "order": "desc",
            },
        )
        if not isinstance(body, dict):
            raise ToolExecutionError("Unexpected GitHub Search payload")

        items = body.get("items") or []
        results: list[SearchHit] = []
        if isinstance(items, list):
            for item in items[: payload.limit]:
                if not isinstance(item, dict):
                    continue
                results.append(
                    SearchHit(
                        title=str(item.get("full_name") or ""),
                        url=str(item.get("html_url") or ""),
                        snippet=str(item.get("description") or ""),
                        source="github",
                        metadata={
                            "stars": str(item.get("stargazers_count") or ""),
                            "language": str(item.get("language") or ""),
                        },
                    )
                )
        return SearchOutput(query=payload.query, results=results)
