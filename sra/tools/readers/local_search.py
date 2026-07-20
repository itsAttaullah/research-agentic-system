"""Local document search within configured roots."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from sra.core.errors import ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool

_TEXT_SUFFIXES = {".md", ".txt", ".markdown", ".json", ".csv", ".html", ".htm", ".py", ".rst"}


class LocalDocumentSearchInput(BaseModel):
    query: str = Field(min_length=1)
    root: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)


class LocalDocumentHit(BaseModel):
    path: str
    score: int
    snippet: str = ""


class LocalDocumentSearchOutput(BaseModel):
    query: str
    root: str
    results: list[LocalDocumentHit] = Field(default_factory=list)


class LocalDocumentSearchTool(BaseTool):
    name = "local_document_search"
    description = "Search local text documents under a root directory by filename and content."
    input_schema = LocalDocumentSearchInput
    output_schema = LocalDocumentSearchOutput
    tags = ["search", "local", "document"]

    def __init__(self, *, allowed_roots: list[Path] | None = None) -> None:
        self._allowed_roots = [path.resolve() for path in (allowed_roots or [])]

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, LocalDocumentSearchInput)
        root = Path(payload.root).expanduser().resolve()
        if not root.is_dir():
            raise ToolExecutionError(f"Search root is not a directory: {root}")
        if self._allowed_roots and not _is_under_allowed_roots(root, self._allowed_roots):
            raise ToolExecutionError(
                "Search root is outside the allowed local document roots",
                details={"root": str(root)},
            )

        query = payload.query.casefold()
        hits: list[LocalDocumentHit] = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.casefold() not in _TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 1_000_000:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            score = 0
            if query in path.name.casefold():
                score += 5
            lowered = text.casefold()
            if query in lowered:
                score += 3 + lowered.count(query)
            if score <= 0:
                continue
            snippet = _snippet(text, payload.query)
            hits.append(LocalDocumentHit(path=str(path), score=score, snippet=snippet))

        hits.sort(key=lambda item: (-item.score, item.path))
        return LocalDocumentSearchOutput(
            query=payload.query,
            root=str(root),
            results=hits[: payload.limit],
        )


def _is_under_allowed_roots(root: Path, allowed_roots: list[Path]) -> bool:
    for allowed in allowed_roots:
        try:
            root.relative_to(allowed)
        except ValueError:
            continue
        else:
            return True
    return False


def _snippet(text: str, query: str, *, radius: int = 120) -> str:
    lowered = text.casefold()
    index = lowered.find(query.casefold())
    if index < 0:
        return text[: radius * 2].strip()
    start = max(0, index - radius)
    end = min(len(text), index + len(query) + radius)
    return text[start:end].strip()
