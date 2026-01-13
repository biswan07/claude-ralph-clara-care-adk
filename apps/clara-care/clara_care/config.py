"""Configuration management for ClaraCare agent.

Uses pydantic-settings for environment variable management with
validation and type safety.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase configuration
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # OpenAI configuration (for embeddings)
    openai_api_key: str = ""

    # Google Cloud configuration
    google_cloud_project: str = ""

    # Model configuration
    model_name: str = "gemini-2.5-flash"

    # Confidence threshold for auto-submit vs human review
    confidence_threshold: float = 0.80

    # Embedding configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton settings instance
settings = Settings()
