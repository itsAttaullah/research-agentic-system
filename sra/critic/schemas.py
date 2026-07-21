"""LLM-facing draft schemas for critic results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DraftFinding(BaseModel):
    code: str = Field(min_length=1)
    severity: Literal["low", "medium", "high", "blocker"] = "medium"
    message: str = Field(min_length=1)
    related_topics: list[str] = Field(default_factory=list)


class DraftCritique(BaseModel):
    """Structured critic output before domain identity is assigned."""

    passed: bool
    findings: list[DraftFinding] = Field(default_factory=list)
    forced_replan: bool = False
    replan_directives: list[str] = Field(default_factory=list)
    summary: str = ""
