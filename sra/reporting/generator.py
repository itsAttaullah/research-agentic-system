"""Concrete ReportGenerator: build from run state and render to multiple formats."""

from __future__ import annotations

from pathlib import Path

from sra.core.context import RunContext
from sra.core.errors import ReportGenerationError
from sra.core.time import utc_now
from sra.models.enums import ReportFormat
from sra.models.reporting import ReportArtifact, ReportDocument
from sra.reporting.builder import build_report_document
from sra.reporting.html_renderer import render_html
from sra.reporting.json_renderer import render_json
from sra.reporting.markdown_renderer import render_markdown
from sra.reporting.pdf_renderer import render_pdf


class ResearchReportGenerator:
    """ReportGenerator port implementation. Performs no new research."""

    def __init__(self, *, output_dir: Path | str | None = None) -> None:
        self._output_dir = Path(output_dir) if output_dir is not None else Path("./reports/out")

    async def build(self, ctx: RunContext) -> ReportDocument:
        return build_report_document(ctx)

    async def render(
        self,
        document: ReportDocument,
        *,
        fmt: ReportFormat,
    ) -> ReportArtifact:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{document.run_id}_{document.report_id}"

        if fmt is ReportFormat.MARKDOWN:
            content = render_markdown(document)
            path = self._output_dir / f"{stem}.md"
            path.write_text(content, encoding="utf-8")
            return ReportArtifact(
                report_id=document.report_id,
                run_id=document.run_id,
                format=fmt,
                path=path,
                content=content,
                created_at=utc_now(),
            )

        if fmt is ReportFormat.HTML:
            content = render_html(document)
            path = self._output_dir / f"{stem}.html"
            path.write_text(content, encoding="utf-8")
            return ReportArtifact(
                report_id=document.report_id,
                run_id=document.run_id,
                format=fmt,
                path=path,
                content=content,
                created_at=utc_now(),
            )

        if fmt is ReportFormat.JSON:
            content = render_json(document)
            path = self._output_dir / f"{stem}.json"
            path.write_text(content, encoding="utf-8")
            return ReportArtifact(
                report_id=document.report_id,
                run_id=document.run_id,
                format=fmt,
                path=path,
                content=content,
                created_at=utc_now(),
            )

        if fmt is ReportFormat.PDF:
            path = self._output_dir / f"{stem}.pdf"
            render_pdf(document, output_path=path)
            return ReportArtifact(
                report_id=document.report_id,
                run_id=document.run_id,
                format=fmt,
                path=path,
                content=None,
                created_at=utc_now(),
            )

        raise ReportGenerationError(
            f"Unsupported report format: {fmt}",
            details={"format": str(fmt)},
        )
