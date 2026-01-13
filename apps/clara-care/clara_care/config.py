"""Configuration management for ClaraCare agent.

Uses pydantic-settings for environment variable management with
validation and type safety. Required settings will fail-fast if not provided.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required settings (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY,
    GOOGLE_CLOUD_PROJECT) must be provided via environment variables or .env file.
    The application will fail-fast if any required setting is missing or empty.
    """

    # Supabase configuration (required)
    supabase_url: str
    supabase_service_role_key: str

    # OpenAI configuration for embeddings (required)
    openai_api_key: str

    # Google Cloud configuration (required)
    google_cloud_project: str

    # Model configuration (optional with defaults)
    model_name: str = "gemini-2.5-flash"

    # Confidence threshold for auto-submit vs human review (optional)
    confidence_threshold: float = 0.80

    # Embedding configuration (optional with defaults)
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "supabase_url",
        "supabase_service_role_key",
        "openai_api_key",
        "google_cloud_project",
        mode="after",
    )
    @classmethod
    def validate_required_not_empty(cls, v: str, info: object) -> str:
        """Validate that required settings are not empty strings."""
        if not v or not v.strip():
            field_name = getattr(info, "field_name", "field")
            raise ValueError(
                f"{field_name.upper()} is required and cannot be empty. "
                f"Please set it in your .env file or environment variables."
            )
        return v


def get_settings() -> Settings:
    """Get validated settings instance.

    This function creates and validates a Settings instance. It will raise
    a ValidationError if any required settings are missing or empty.

    Returns:
        Settings: Validated settings instance.

    Raises:
        pydantic.ValidationError: If required settings are missing or invalid.
    """
    return Settings()


# Singleton settings instance - will fail-fast if required settings are missing
# Note: Import this only when settings are actually needed to allow testing
# without full configuration
settings = Settings()
