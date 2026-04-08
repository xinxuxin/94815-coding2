"""Configuration models for provider and runtime settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings for the StockTrader project."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: Literal["groq", "openai", "ollama", "mock"] = "groq"
    groq_api_key: str = ""
    groq_model: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    ollama_base_url: str = ""
    ollama_model: str = ""
    llm_temperature: float = 0.1
    llm_max_retries: int = 1

    def provider_model(self) -> str:
        """Return the configured model name for the active provider."""

        if self.llm_provider == "groq":
            return self.groq_model or "llama-3.1-70b-versatile"
        if self.llm_provider == "openai":
            return self.openai_model or "gpt-4o-mini"
        if self.llm_provider == "ollama":
            return self.ollama_model or "llama3.1:8b"
        return "mock-structured"

    def provider_base_url(self) -> str:
        """Return the OpenAI-compatible base URL for the active provider."""

        if self.llm_provider == "groq":
            return "https://api.groq.com/openai/v1"
        if self.llm_provider == "openai":
            return "https://api.openai.com/v1"
        if self.llm_provider == "ollama":
            return self.ollama_base_url or "http://localhost:11434/v1"
        return ""

    def provider_api_key(self) -> str:
        """Return the API key or placeholder token for the active provider."""

        if self.llm_provider == "groq":
            return self.groq_api_key
        if self.llm_provider == "openai":
            return self.openai_api_key
        if self.llm_provider == "ollama":
            return "ollama"
        return "mock"

    def has_live_credentials(self) -> bool:
        """Return whether the active provider is configured for live calls."""

        if self.llm_provider == "groq":
            return bool(self.groq_api_key)
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider == "ollama":
            return bool(self.ollama_model)
        return False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings loaded from environment variables."""

    return Settings()
