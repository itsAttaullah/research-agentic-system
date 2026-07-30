"""Shared helpers for provider adapters."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(content: str) -> dict[str, Any] | None:
    """Best-effort extraction of a JSON object from model text."""
    text = content.strip()
    if not text:
        return None
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            loaded = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, dict) else None
