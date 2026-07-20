"""Shared schemas used by multiple tools."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    title: str
    url: str = ""
    snippet: str = ""
    source: str = ""
    published: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchInput(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SearchOutput(BaseModel):
    query: str
    results: list[SearchHit] = Field(default_factory=list)


class TextDocumentInput(BaseModel):
    url: str = Field(min_length=1)
    max_chars: int = Field(default=20_000, ge=500, le=200_000)


class TextDocumentOutput(BaseModel):
    url: str
    title: str = ""
    content: str
    content_type: str = ""
    status_code: int = 200


class ParseTextInput(BaseModel):
    text: str = Field(min_length=1)
    max_chars: int = Field(default=20_000, ge=100, le=200_000)


class ParseTextOutput(BaseModel):
    title: str = ""
    content: str
    links: list[str] = Field(default_factory=list)
