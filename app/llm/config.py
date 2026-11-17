import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """Configuration settings for LLM Core."""

    llm_mode: str = Field(default="fake", description="Mode: 'fake' or 'real'")
    llm_api_key: str = Field(default="", description="Anthropic API key")
    llm_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Anthropic model name",
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout in seconds for LLM calls",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_llm_config() -> LLMConfig:
    """Returns singleton-like configuration instance."""
    return LLMConfig()
