"""Unit tests for the tool registry and built-in tools."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sra.core.config import Settings
from sra.core.ports.tools import ToolContext
from sra.models.tools import ToolCall
from sra.tools import create_default_registry
from sra.tools.compute import (
    CalculatorTool,
    CitationGeneratorTool,
    SummarizerTool,
    TableGeneratorTool,
)
from sra.tools.http import HttpGateway, HttpResponse
from sra.tools.readers import HtmlParserTool, LocalDocumentSearchTool, MarkdownReaderTool
from sra.tools.registry import InMemoryToolRegistry
from sra.tools.search import AcademicPaperSearchTool, GoogleSearchTool, RedditSearchTool


class FakeHttp(HttpGateway):
    def __init__(self, payload: object, *, status_code: int = 200) -> None:
        super().__init__()
        self.payload = payload
        self.status_code = status_code
        self.urls: list[str] = []

    async def get_json(self, url: str, **kwargs: object) -> tuple[HttpResponse, object]:
        self.urls.append(url)
        response = HttpResponse(
            url=url,
            status_code=self.status_code,
            content_type="application/json",
            text="",
            content=b"{}",
        )
        if self.status_code >= 400:
            from sra.core.errors import ToolExecutionError

            raise ToolExecutionError(f"HTTP {self.status_code} from {url}")
        return response, self.payload


def _ctx() -> ToolContext:
    return ToolContext(run_id=uuid4(), call_id=uuid4())


@pytest.mark.asyncio
async def test_registry_validates_input_and_executes_calculator() -> None:
    registry = InMemoryToolRegistry()
    registry.register(CalculatorTool())

    ok = await registry.execute(
        ToolCall(tool_name="calculator", arguments={"expression": "2 + 3 * 4"}),
        run_id=uuid4(),
    )
    assert ok.success
    assert ok.output["result"] == 14

    bad = await registry.execute(
        ToolCall(tool_name="calculator", arguments={"expression": "__import__('os')"}),
        run_id=uuid4(),
    )
    assert not bad.success
    assert bad.error is not None


@pytest.mark.asyncio
async def test_registry_rejects_unknown_tool() -> None:
    registry = InMemoryToolRegistry()
    result = await registry.execute(
        ToolCall(tool_name="nope", arguments={}),
        run_id=uuid4(),
    )
    assert not result.success
    assert result.error is not None
    assert "not registered" in result.error.lower()


@pytest.mark.asyncio
async def test_calculator_supports_safe_functions() -> None:
    tool = CalculatorTool()
    output = await tool.execute(
        tool.input_schema(expression="sqrt(16) + abs(-2)"),
        _ctx(),
    )
    assert output.result == 6.0  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_table_citation_and_summarizer_tools() -> None:
    table = await TableGeneratorTool().execute(
        TableGeneratorTool.input_schema(
            columns=["Vendor", "Focus"],
            rows=[["A", "Imaging"], ["B", "Scheduling"]],
            format="markdown",
            title="Competitors",
        ),
        _ctx(),
    )
    assert "Vendor" in table.content  # type: ignore[attr-defined]
    assert table.row_count == 2  # type: ignore[attr-defined]

    citation = await CitationGeneratorTool().execute(
        CitationGeneratorTool.input_schema(
            title="Dental AI Market Report",
            url="https://example.com/report",
            authors=["Smith"],
            published="2024",
            style="markdown",
        ),
        _ctx(),
    )
    assert "Dental AI Market Report" in citation.citation  # type: ignore[attr-defined]

    summary = await SummarizerTool().execute(
        SummarizerTool.input_schema(
            text=(
                "Dentists face scheduling friction. AI can triage intake forms. "
                "Insurance eligibility remains a bottleneck. Vendors compete on workflow. "
                "Regulation around patient data is strict."
            ),
            max_sentences=2,
        ),
        _ctx(),
    )
    assert summary.sentence_count == 2  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_html_markdown_and_local_search(tmp_path: Path) -> None:
    html = await HtmlParserTool().execute(
        HtmlParserTool.input_schema(
            text="<html><head><title>Hello</title></head><body><p>World</p>"
            "<a href='https://example.com'>x</a></body></html>"
        ),
        _ctx(),
    )
    assert html.title == "Hello"  # type: ignore[attr-defined]
    assert "World" in html.content  # type: ignore[attr-defined]
    assert "https://example.com" in html.links  # type: ignore[attr-defined]

    note = tmp_path / "notes.md"
    note.write_text("# Market\n\nDental AI demand is rising.", encoding="utf-8")
    md = await MarkdownReaderTool().execute(
        MarkdownReaderTool.input_schema(path=str(note)),
        _ctx(),
    )
    assert "Dental AI" in md.content  # type: ignore[attr-defined]

    search = LocalDocumentSearchTool(allowed_roots=[tmp_path])
    found = await search.execute(
        search.input_schema(query="Dental AI", root=str(tmp_path), limit=5),
        _ctx(),
    )
    assert found.results  # type: ignore[attr-defined]
    assert found.results[0].path.endswith("notes.md")  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_local_search_blocks_outside_roots(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    tool = LocalDocumentSearchTool(allowed_roots=[allowed])
    with pytest.raises(Exception, match="outside the allowed"):
        await tool.execute(
            tool.input_schema(query="x", root=str(outside)),
            _ctx(),
        )


@pytest.mark.asyncio
async def test_reddit_and_academic_search_with_fake_http() -> None:
    reddit_http = FakeHttp(
        {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Dentists hate intake paperwork",
                            "permalink": "/r/dentistry/comments/1/x/",
                            "selftext": "AI scheduling helped our clinic.",
                            "subreddit": "dentistry",
                            "score": 42,
                        }
                    }
                ]
            }
        }
    )
    reddit = RedditSearchTool(http=reddit_http)
    reddit_out = await reddit.execute(reddit.input_schema(query="dental AI", limit=3), _ctx())
    assert reddit_out.results[0].title.startswith("Dentists")  # type: ignore[attr-defined]

    academic_http = FakeHttp(
        {
            "data": [
                {
                    "title": "AI in Dentistry Survey",
                    "url": "https://semanticscholar.org/paper/1",
                    "abstract": "A survey of clinical AI applications.",
                    "year": 2023,
                    "authors": [{"name": "Lee"}],
                }
            ]
        }
    )
    academic = AcademicPaperSearchTool(http=academic_http)
    papers = await academic.execute(academic.input_schema(query="dentistry AI", limit=3), _ctx())
    assert papers.results[0].source == "semantic_scholar"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_google_search_missing_credentials_returns_failed_result() -> None:
    registry = InMemoryToolRegistry()
    registry.register(GoogleSearchTool(api_key=None, cx=None, http=FakeHttp({})))
    result = await registry.execute(
        ToolCall(tool_name="google_search", arguments={"query": "dental AI market"}),
        run_id=uuid4(),
    )
    assert not result.success
    assert result.error is not None
    assert "GOOGLE_SEARCH" in result.error


def test_default_registry_registers_all_expected_tools() -> None:
    registry = create_default_registry(Settings(local_document_roots="./data"))
    names = {item.name for item in registry.list_descriptors()}
    expected = {
        "google_search",
        "news_search",
        "academic_paper_search",
        "reddit_search",
        "github_search",
        "youtube_search",
        "website_reader",
        "pdf_reader",
        "html_parser",
        "markdown_reader",
        "local_document_search",
        "calculator",
        "table_generator",
        "citation_generator",
        "summarizer",
    }
    assert expected <= names
    assert registry.describe_for_prompt()
