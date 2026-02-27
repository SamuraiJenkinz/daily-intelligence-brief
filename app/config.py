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

    # TTS Settings
    tts_voice: str = "nova"                # Azure OpenAI TTS voice name
    elevenlabs_api_key: str = ""           # ElevenLabs API key for fallback TTS
    elevenlabs_voice_id: str = ""          # ElevenLabs voice ID (find match for "nova")

    # Microsoft Graph (for email delivery in Phase 5)
    microsoft_tenant_id: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    sender_email: str = ""

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

    # Azure Blob Storage (for database backups)
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "mdinsights-backups"
    backup_retention_days: int = 30

    # MMC Core API (Enterprise Integration)
    # Used for Factiva news (X-Api-Key), equity prices (X-Api-Key),
    # and enterprise email delivery (JWT Bearer + X-Api-Key)
    mmc_api_base_url: str = ""
    mmc_api_client_id: str = ""
    mmc_api_client_secret: str = ""
    mmc_api_key: str = ""
    mmc_api_token_path: str = "/coreapi/access-management/v1/token"

    # Enterprise Email Sender (separate from Graph API sender_email)
    mmc_sender_email: str = ""    # Env: MMC_SENDER_EMAIL — enterprise mailbox to send from
    mmc_sender_name: str = "Kevin Taylor"  # Env: MMC_SENDER_NAME — display name
    mmc_email_path: str = "/coreapi/email/v1"  # Env: MMC_EMAIL_PATH — endpoint path

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

    def is_azure_storage_configured(self) -> bool:
        """Check if Azure Blob Storage is configured."""
        return bool(self.azure_storage_connection_string)

    def is_mmc_auth_configured(self) -> bool:
        """Check if MMC Core API OAuth2 (JWT) auth is fully configured.

        Required for the Email API (Phase 12) which uses Bearer + X-Api-Key.
        """
        return bool(
            self.mmc_api_base_url
            and self.mmc_api_client_id
            and self.mmc_api_client_secret
        )

    def is_mmc_api_key_configured(self) -> bool:
        """Check if MMC Core API X-Api-Key is configured.

        Required for Factiva news (Phase 10) and equity prices (Phase 11)
        which use X-Api-Key only (no JWT needed).
        """
        return bool(self.mmc_api_base_url and self.mmc_api_key)

    def is_mmc_email_configured(self) -> bool:
        """Check if enterprise email delivery is fully configured.

        Requires JWT auth (mmc_auth) + API key + enterprise sender email.
        When False, pipeline uses Graph API for email delivery.
        """
        return bool(
            self.is_mmc_auth_configured()
            and self.mmc_api_key
            and self.mmc_sender_email
        )

    def is_elevenlabs_configured(self) -> bool:
        """Check if ElevenLabs TTS fallback is fully configured.

        Requires both API key and voice ID to be set.
        """
        return bool(self.elevenlabs_api_key and self.elevenlabs_voice_id)

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
