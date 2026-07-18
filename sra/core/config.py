"""Application settings loaded from environment / .env via pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide configuration. Injected into the DI container; not a singleton
    used directly by domain logic.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        validation_alias="SRA_LLM_PROVIDER",
    )
    llm_model: str = Field(default="gpt-4o", validation_alias="SRA_LLM_MODEL")

    # Search
    google_search_api_key: str | None = Field(
        default=None,
        validation_alias="GOOGLE_SEARCH_API_KEY",
    )
    google_search_cx: str | None = Field(
        default=None,
        validation_alias="GOOGLE_SEARCH_CX",
    )

    # Storage
    data_dir: Path = Field(default=Path("./data"), validation_alias="SRA_DATA_DIR")
    control_db: Path = Field(
        default=Path("./data/control.sqlite3"),
        validation_alias="SRA_CONTROL_DB",
    )
    knowledge_db: Path = Field(
        default=Path("./data/knowledge.duckdb"),
        validation_alias="SRA_KNOWLEDGE_DB",
    )

    # Budget defaults
    max_iterations: int = Field(default=40, validation_alias="SRA_MAX_ITERATIONS")
    max_tokens: int = Field(default=500_000, validation_alias="SRA_MAX_TOKENS")
    max_cost_usd: float = Field(default=5.0, validation_alias="SRA_MAX_COST_USD")
    max_minutes: float = Field(default=30.0, validation_alias="SRA_MAX_MINUTES")
    max_sources: int = Field(default=60, validation_alias="SRA_MAX_SOURCES")

    # Confidence
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        validation_alias="SRA_CONFIDENCE_THRESHOLD",
    )

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
