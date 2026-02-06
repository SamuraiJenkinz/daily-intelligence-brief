"""
Application configuration loaded from environment variables.

Uses pydantic-settings for validation and .env file loading.
All external service credentials centralized here.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Allow extra env vars without error
    )

    # Database
    database_url: str = "sqlite:///./data/mdinsights.db"
    data_dir: str = "./data"

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-08-01-preview"

    # Microsoft Graph (for email delivery in Phase 5)
    microsoft_tenant_id: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    sender_email: str = ""

    # Apify (for web scraping)
    apify_token: str = ""

    # Application
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8001

    # Report settings
    company_name: str = "Marsh"

    def is_azure_openai_configured(self) -> bool:
        """Check if Azure OpenAI is fully configured."""
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_deployment
        )

    def is_graph_configured(self) -> bool:
        """Check if Microsoft Graph email is fully configured."""
        return bool(
            self.microsoft_tenant_id
            and self.microsoft_client_id
            and self.microsoft_client_secret
            and self.sender_email
        )

    def is_apify_configured(self) -> bool:
        """Check if Apify is configured."""
        return bool(self.apify_token)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure only one Settings object is created.
    """
    return Settings()
