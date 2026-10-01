"""
SDE-SQL Configuration Management
Loads all settings from environment variables (via .env file or shell).
No secrets are ever hardcoded here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Ollama LLM settings
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # Database settings
    database_path: str = "data/college.db"

    # Execution constraints
    max_rows: int = 100
    query_timeout_seconds: int = 5

    # Exploration constraints
    max_probes: int = 5

    # Application metadata
    app_name: str = "SDE-SQL"
    app_version: str = "0.1.0"
    app_description: str = (
        "Self-Driven Database Exploration for Accurate Text-to-SQL"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


# Global singleton settings instance
settings = Settings()
