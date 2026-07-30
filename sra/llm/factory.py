"""Factory for concrete LLMClient adapters from Settings."""

from __future__ import annotations

from sra.core.config import Settings
from sra.core.errors import ConfigurationError
from sra.core.ports.llm import LLMClient
from sra.llm.anthropic_client import AnthropicLLMClient
from sra.llm.openai_client import OpenAILLMClient


def build_llm_client(settings: Settings | None = None) -> LLMClient:
    """Create the configured provider adapter.

    Raises:
        ConfigurationError: when the selected provider key is missing.
    """
    cfg = settings or Settings()
    if cfg.llm_provider == "openai":
        return OpenAILLMClient(api_key=cfg.openai_api_key or "", model=cfg.llm_model)
    if cfg.llm_provider == "anthropic":
        return AnthropicLLMClient(api_key=cfg.anthropic_api_key or "", model=cfg.llm_model)
    raise ConfigurationError(
        f"Unsupported LLM provider: {cfg.llm_provider}",
        details={"supported": ["openai", "anthropic"]},
    )
