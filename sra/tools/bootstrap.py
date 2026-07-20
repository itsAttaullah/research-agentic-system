"""Compose the default tool registry from settings and shared gateways."""

from __future__ import annotations

from pathlib import Path

from sra.core.config import Settings
from sra.tools.compute import (
    CalculatorTool,
    CitationGeneratorTool,
    SummarizerTool,
    TableGeneratorTool,
)
from sra.tools.http import HttpGateway
from sra.tools.readers import (
    HtmlParserTool,
    LocalDocumentSearchTool,
    MarkdownReaderTool,
    PdfReaderTool,
    WebsiteReaderTool,
)
from sra.tools.registry import InMemoryToolRegistry
from sra.tools.search import (
    AcademicPaperSearchTool,
    GitHubSearchTool,
    GoogleSearchTool,
    NewsSearchTool,
    RedditSearchTool,
    YouTubeSearchTool,
)


def create_default_registry(
    settings: Settings | None = None,
    *,
    http: HttpGateway | None = None,
) -> InMemoryToolRegistry:
    """Register all built-in research tools.

    Tools that need missing credentials still register; they fail clearly at
    execution time so the agent can adapt instead of losing capability discovery.
    """
    cfg = settings or Settings()
    gateway = http or HttpGateway()
    registry = InMemoryToolRegistry()

    allowed_roots = [
        Path(part.strip()).expanduser().resolve()
        for part in cfg.local_document_roots.split(",")
        if part.strip()
    ]

    tools = [
        GoogleSearchTool(api_key=cfg.google_search_api_key, cx=cfg.google_search_cx, http=gateway),
        NewsSearchTool(api_key=cfg.google_search_api_key, cx=cfg.google_search_cx, http=gateway),
        AcademicPaperSearchTool(http=gateway),
        RedditSearchTool(http=gateway),
        GitHubSearchTool(token=cfg.github_token, http=gateway),
        YouTubeSearchTool(api_key=cfg.youtube_api_key, http=gateway),
        WebsiteReaderTool(http=gateway),
        PdfReaderTool(http=gateway),
        HtmlParserTool(),
        MarkdownReaderTool(),
        LocalDocumentSearchTool(allowed_roots=allowed_roots),
        CalculatorTool(),
        TableGeneratorTool(),
        CitationGeneratorTool(),
        SummarizerTool(),
    ]
    for tool in tools:
        registry.register(tool)
    return registry
