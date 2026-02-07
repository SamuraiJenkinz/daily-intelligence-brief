"""
Application configuration loaded from environment variables.

Uses pydantic-settings for validation and .env file loading.
All external service credentials centralized here.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas.delivery import EmailRecipients


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

    # Email recipient configuration (per role)
    report_recipients_brokers: str = ""
    report_recipients_brokers_cc: str = ""
    report_recipients_brokers_bcc: str = ""
    report_recipients_leadership: str = ""
    report_recipients_leadership_cc: str = ""
    report_recipients_leadership_bcc: str = ""
    report_recipients_compliance: str = ""
    report_recipients_compliance_cc: str = ""
    report_recipients_compliance_bcc: str = ""
    report_recipients_underwriting: str = ""
    report_recipients_underwriting_cc: str = ""
    report_recipients_underwriting_bcc: str = ""

    # Admin email for failure alerts
    admin_email: str = ""

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

    def _parse_recipient_list(self, recipients_str: str) -> list[str]:
        """
        Parse comma-separated recipient string into list.

        Args:
            recipients_str: Comma-separated email addresses

        Returns:
            List of email addresses with whitespace stripped
        """
        if not recipients_str:
            return []
        return [addr.strip() for addr in recipients_str.split(",") if addr.strip()]

    def get_email_recipients(self, role: str) -> EmailRecipients:
        """
        Get email recipients for a specific role.

        Args:
            role: Role name (Brokers, Leadership, Compliance, Underwriting)

        Returns:
            EmailRecipients with parsed TO/CC/BCC lists
        """
        # Map role names to field name prefixes
        role_map = {
            "Brokers": "report_recipients_brokers",
            "Leadership": "report_recipients_leadership",
            "Compliance": "report_recipients_compliance",
            "Underwriting": "report_recipients_underwriting",
        }

        prefix = role_map.get(role)
        if not prefix:
            # Unknown role - return empty recipients
            return EmailRecipients(to=[], cc=[], bcc=[])

        # Get field values using getattr with defaults
        to_list = self._parse_recipient_list(getattr(self, prefix, ""))
        cc_list = self._parse_recipient_list(getattr(self, f"{prefix}_cc", ""))
        bcc_list = self._parse_recipient_list(getattr(self, f"{prefix}_bcc", ""))

        return EmailRecipients(to=to_list, cc=cc_list, bcc=bcc_list)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure only one Settings object is created.
    """
    return Settings()
