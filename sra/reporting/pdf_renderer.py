"""Render a ReportDocument into PDF via PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import fitz

from sra.core.errors import ReportGenerationError
from sra.models.reporting import ReportDocument
from sra.reporting.markdown_renderer import render_markdown


def render_pdf(document: ReportDocument, *, output_path: Path) -> Path:
    """Write a multi-page A4 PDF from the Markdown report text."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = render_markdown(document)
    chunks = _paginate(text, max_chars=2800)
    try:
        pdf = fitz.open()
        for chunk in chunks:
            page = pdf.new_page(width=595, height=842)
            margin = 48
            rect = fitz.Rect(margin, margin, page.rect.width - margin, page.rect.height - margin)
            page.insert_textbox(
                rect,
                chunk,
                fontsize=10,
                fontname="helv",
                align=fitz.TEXT_ALIGN_LEFT,
            )
        pdf.save(output_path)
        pdf.close()
    except Exception as exc:  # noqa: BLE001
        raise ReportGenerationError(
            f"Failed to render PDF report: {exc}",
            details={"path": str(output_path)},
        ) from exc
    return output_path


def _paginate(text: str, *, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n\n", 0, max_chars)
        if split_at < max_chars // 2:
            split_at = remaining.rfind("\n", 0, max_chars)
        if split_at < max_chars // 2:
            split_at = max_chars
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    return chunks or [text]
