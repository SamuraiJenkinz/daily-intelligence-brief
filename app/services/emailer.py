"""
Microsoft Graph email service for sending HTML intelligence briefs.

Uses daemon authentication (ClientSecretCredential) for automated
email sending without user interaction. Requires Mail.Send application
permission with admin consent in Azure AD.
"""
import base64
import logging
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog
from azure.identity import ClientSecretCredential
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.config import get_settings

logger = structlog.get_logger(__name__)


class GraphEmailService:
    """
    Service for sending HTML emails via Microsoft Graph API.

    Uses Azure AD app registration with Mail.Send application permission
    for daemon (service-to-service) authentication.

    Prerequisites:
    1. Azure AD app registration with Mail.Send application permission
    2. Admin consent granted for the permission
    3. Sender email must be a valid mailbox the app has access to
    """

    def __init__(self):
        settings = get_settings()

        if not settings.is_graph_configured():
            logger.warning("Microsoft Graph not configured - email will fail")
            self.credential = None
            self.sender_email = None
        else:
            # Daemon app authentication (no user interaction)
            self.credential = ClientSecretCredential(
                tenant_id=settings.microsoft_tenant_id,
                client_id=settings.microsoft_client_id,
                client_secret=settings.microsoft_client_secret,
            )
            self.sender_email = settings.sender_email

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def send_email(
        self,
        to_addresses: list[str],
        subject: str,
        html_body: str,
        audio_path: Optional[Path] = None,
        cc_addresses: list[str] | None = None,
        bcc_addresses: list[str] | None = None,
        save_to_sent: bool = True,
    ) -> dict[str, Any]:
        """
        Send an HTML email via Microsoft Graph.

        Args:
            to_addresses: List of TO recipient email addresses
            subject: Email subject line
            html_body: HTML content for email body
            audio_path: Optional path to MP3 file to attach
            cc_addresses: Optional list of CC recipients
            bcc_addresses: Optional list of BCC recipients
            save_to_sent: Whether to save email to Sent folder

        Returns:
            dict with status and any error message
        """
        if not self.credential:
            logger.error("Graph credential not initialized - check Azure credentials")
            return {"status": "error", "message": "Microsoft Graph not configured"}

        if not to_addresses:
            return {"status": "error", "message": "No recipients specified"}

        # Get access token
        token = self.credential.get_token("https://graph.microsoft.com/.default")

        # Build message payload
        message_payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_body
                },
                "toRecipients": [
                    {"emailAddress": {"address": addr}} for addr in to_addresses
                ]
            },
            "saveToSentItems": save_to_sent
        }

        # Add CC recipients if provided
        if cc_addresses:
            message_payload["message"]["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc_addresses
            ]

        # Add BCC recipients if provided
        if bcc_addresses:
            message_payload["message"]["bccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in bcc_addresses
            ]

        # Attach audio MP3 if provided
        if audio_path and audio_path.exists():
            try:
                audio_bytes = audio_path.read_bytes()
                size_mb = len(audio_bytes) / 1_048_576

                if size_mb > 3.0:
                    # Graph API attachment limit — skip but log warning
                    logger.warning(
                        "audio_attachment_too_large",
                        size_mb=round(size_mb, 2),
                        path=str(audio_path),
                        limit_mb=3.0,
                    )
                else:
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                    message_payload["message"]["attachments"] = [{
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": audio_path.name,
                        "contentType": "audio/mpeg",
                        "contentBytes": audio_base64,
                        "isInline": False,
                    }]
                    logger.info(
                        "audio_attachment_added",
                        filename=audio_path.name,
                        size_mb=round(size_mb, 2),
                    )
            except Exception as e:
                # Attachment failure is a warning, NOT an error — email still sends
                logger.warning(
                    "audio_attachment_failed",
                    path=str(audio_path),
                    error=str(e),
                )

        # Send via Graph API
        logger.info(
            "Sending email",
            recipient_count=len(to_addresses),
            subject=subject,
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.microsoft.com/v1.0/users/{self.sender_email}/sendMail",
                headers={
                    "Authorization": f"Bearer {token.token}",
                    "Content-Type": "application/json"
                },
                json=message_payload,
                timeout=30.0
            )

            if response.status_code == 202:
                logger.info(
                    "Email sent successfully",
                    has_audio=bool(message_payload["message"].get("attachments")),
                )
                return {
                    "status": "ok",
                    "recipients": len(to_addresses),
                    "cc": len(cc_addresses) if cc_addresses else 0,
                    "bcc": len(bcc_addresses) if bcc_addresses else 0,
                }
            elif response.status_code >= 500:
                # Server error - raise to trigger retry
                error_msg = f"Graph API error {response.status_code}: {response.text}"
                logger.error("Email send failed - server error", error=error_msg)
                raise httpx.NetworkError(error_msg)
            else:
                # Client error (4xx) - don't retry
                error_msg = f"Graph API error {response.status_code}: {response.text}"
                logger.error("Email send failed - client error", error=error_msg)
                return {"status": "error", "message": error_msg}

    async def health_check_async(self) -> dict[str, Any]:
        """
        Async health check with actual Graph API test.

        Returns dict with status and any error message.
        """
        if not self.credential:
            return {"status": "error", "message": "Microsoft Graph not configured"}

        try:
            # Get access token and try to fetch user info
            token = self.credential.get_token("https://graph.microsoft.com/.default")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://graph.microsoft.com/v1.0/users/{self.sender_email}",
                    headers={"Authorization": f"Bearer {token.token}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "status": "ok",
                        "sender": self.sender_email,
                        "display_name": user_data.get("displayName"),
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Graph API error {response.status_code}: {response.text}"
                    }

        except Exception as e:
            return {"status": "error", "message": str(e)}
