"""Render a ReportDocument into Markdown."""

from __future__ import annotations

from sra.models.reporting import ReportDocument


def render_markdown(document: ReportDocument) -> str:
    sections = sorted(document.sections, key=lambda item: item.order)
    parts = [
        f"# {document.title}",
        "",
        f"_Generated at {document.generated_at.isoformat()} · run `{document.run_id}`_",
        "",
    ]
    for section in sections:
        parts.append(f"## {section.title}")
        parts.append("")
        parts.append(section.body_markdown.strip() or "_No content._")
        parts.append("")
    if document.references and not any(section.title == "References" for section in sections):
        parts.append("## References")
        parts.append("")
        parts.extend(f"{index}. {item}" for index, item in enumerate(document.references, start=1))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
