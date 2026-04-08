"""Configuration models for provider and runtime settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings for the StockTrader project."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: Literal["groq", "openai", "ollama"] = "groq"
    groq_api_key: str = ""
    groq_model: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    ollama_base_url: str = ""
    ollama_model: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings loaded from environment variables."""

    return Settings()
