"""Render a ReportDocument into JSON."""

from __future__ import annotations

from sra.models.reporting import ReportDocument


def render_json(document: ReportDocument) -> str:
    return document.model_dump_json(indent=2)
