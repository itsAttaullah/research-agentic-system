"""Render a ReportDocument into HTML."""

from __future__ import annotations

import html

import markdown as md

from sra.models.reporting import ReportDocument
from sra.reporting.markdown_renderer import render_markdown

_HTML_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1c1917;
      --muted: #57534e;
      --paper: #fafaf9;
      --line: #e7e5e4;
      --accent: #0f766e;
    }}
    body {{
      margin: 0;
      font-family: "Source Serif 4", "Iowan Old Style", Georgia, serif;
      background: linear-gradient(180deg, #f5f5f4 0%, var(--paper) 240px);
      color: var(--ink);
      line-height: 1.6;
    }}
    main {{
      max-width: 820px;
      margin: 0 auto;
      padding: 48px 24px 72px;
    }}
    h1, h2, h3 {{
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      letter-spacing: -0.02em;
      line-height: 1.25;
    }}
    h1 {{ font-size: 2.1rem; margin-bottom: 0.4rem; }}
    h2 {{
      margin-top: 2.2rem;
      padding-top: 0.8rem;
      border-top: 1px solid var(--line);
      color: var(--accent);
    }}
    em, .meta {{ color: var(--muted); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0;
      font-size: 0.95rem;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 0.55rem 0.7rem;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #f5f5f4; }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.9em;
    }}
  </style>
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>
"""


def render_html(document: ReportDocument) -> str:
    markdown_text = render_markdown(document)
    body = md.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    return _HTML_SHELL.format(
        title=html.escape(document.title),
        body=body,
    )
