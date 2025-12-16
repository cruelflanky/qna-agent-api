from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI / LLM Configuration
    openai_api_key: str
    openai_base_url: str = "https://openrouter.ai/api/v1"
    openai_model: str = "mistralai/devstral-2512:free"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/qna.db"

    # Knowledge Base
    knowledge_dir: Path = Path("./knowledge")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" for production, "text" for development

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
