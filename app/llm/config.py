import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """Configuration settings for LLM Core."""

    llm_mode: str = Field(default="fake", description="Mode: 'fake' or 'real'")
    llm_api_key: str = Field(default="", description="OpenRouter API key")
    llm_model: str = Field(
        default="google/gemma-4-26b-a4b-it:free",
        description="OpenRouter model identifier",
    )
    llm_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter base URL (OpenAI-compatible)",
    )
    llm_timeout_seconds: float = Field(
        default=60.0,
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
