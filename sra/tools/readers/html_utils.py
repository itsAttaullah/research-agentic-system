"""HTML cleaning helpers shared by website/html/markdown readers."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

_WHITESPACE = re.compile(r"\s+")


def html_to_text(html: str, *, max_chars: int) -> tuple[str, str, list[str]]:
    """Return title, visible text, and absolute-ish hrefs from HTML."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        if href and href not in links:
            links.append(href)

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    collapsed = _WHITESPACE.sub(" ", "\n".join(line for line in lines if line)).strip()
    if len(collapsed) > max_chars:
        collapsed = collapsed[:max_chars].rstrip() + "…"
    return title, collapsed, links[:100]
