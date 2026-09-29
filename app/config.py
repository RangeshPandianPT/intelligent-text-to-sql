"""
SDE-SQL Configuration Management
Loads all settings from environment variables (via .env file or shell).
No secrets are ever hardcoded here.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Ollama LLM settings
    ollama_host: str = Field(default="http://localhost:11434", env="OLLAMA_HOST")
    ollama_model: str = Field(default="qwen2.5:7b", env="OLLAMA_MODEL")

    # Database settings
    database_path: str = Field(default="data/college.db", env="DATABASE_PATH")

    # Execution constraints
    max_rows: int = Field(default=100, env="MAX_ROWS")
    query_timeout_seconds: int = Field(default=5, env="QUERY_TIMEOUT_SECONDS")

    # Exploration constraints
    max_probes: int = Field(default=5, env="MAX_PROBES")

    # Application metadata
    app_name: str = "SDE-SQL"
    app_version: str = "0.1.0"
    app_description: str = (
        "Self-Driven Database Exploration for Accurate Text-to-SQL"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global singleton settings instance
settings = Settings()
