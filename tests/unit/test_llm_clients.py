"""Unit tests for LLM factory and JSON extraction helpers."""

from __future__ import annotations

import pytest
from sra.core.config import Settings
from sra.core.errors import ConfigurationError
from sra.llm import build_llm_client
from sra.llm.anthropic_client import AnthropicLLMClient
from sra.llm.json_utils import extract_json_object
from sra.llm.openai_client import OpenAILLMClient


def test_extract_json_object_from_fenced_block() -> None:
    payload = extract_json_object('```json\n{"kind": "finalize", "summary": "done"}\n```')
    assert payload == {"kind": "finalize", "summary": "done"}


def test_build_openai_client_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SRA_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings(_env_file=None)
    with pytest.raises(ConfigurationError):
        build_llm_client(settings)


def test_build_openai_client_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SRA_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("SRA_LLM_MODEL", "gpt-4o")
    settings = Settings(_env_file=None)
    client = build_llm_client(settings)
    assert isinstance(client, OpenAILLMClient)


def test_build_anthropic_client_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SRA_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("SRA_LLM_MODEL", "claude-3-5-sonnet-latest")
    settings = Settings(_env_file=None)
    client = build_llm_client(settings)
    assert isinstance(client, AnthropicLLMClient)
