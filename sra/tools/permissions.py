"""Graduated tool autonomy — scope irreversible / high-blast-radius capabilities."""

from __future__ import annotations

from typing import Literal

AutonomyLevel = Literal["safe", "standard", "unrestricted"]

# Tags that require at least this autonomy level.
_TAG_REQUIREMENTS: dict[str, AutonomyLevel] = {
    "local": "safe",
    "compute": "safe",
    "document": "safe",
    "markdown": "safe",
    "reader": "safe",
    "search": "standard",
    "web": "standard",
    "fetch": "standard",
    "network": "standard",
    "side_effect": "unrestricted",
}

_LEVEL_RANK: dict[AutonomyLevel, int] = {
    "safe": 0,
    "standard": 1,
    "unrestricted": 2,
}


def required_autonomy_for_tags(tags: list[str]) -> AutonomyLevel:
    """Return the strictest autonomy level implied by tool tags."""
    required: AutonomyLevel = "safe"
    for tag in tags:
        candidate = _TAG_REQUIREMENTS.get(tag.casefold())
        if candidate is None:
            continue
        if _LEVEL_RANK[candidate] > _LEVEL_RANK[required]:
            required = candidate
    return required


def tool_allowed(*, tags: list[str], autonomy: AutonomyLevel) -> bool:
    """Whether a tool may auto-execute under the configured autonomy level."""
    return _LEVEL_RANK[autonomy] >= _LEVEL_RANK[required_autonomy_for_tags(tags)]
