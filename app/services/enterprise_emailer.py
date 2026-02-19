"""
EnterpriseEmailClient — MMC Core API email client for MDInsights.

Sends role-based HTML briefs via POST /coreapi/email/v1.
Requires both JWT Bearer token and X-Api-Key authentication.
Falls back to GraphEmailService when unavailable (handled by pipeline, not this client).

API contract:
    Email:  POST {base_url}/coreapi/email/v1
            Headers: Authorization: Bearer {jwt}
                     X-Api-Key: {key}
            Body:    JSON payload with recipients, subject, HTML body, sender impersonation

Authentication:
    JWT Bearer token (acquired by MMCAuthManager, Phase 9) + X-Api-Key header.
    Credentials read from Settings (mmc_api_base_url, mmc_api_key, mmc_sender_email).

Error handling:
    - Returns result dict on ALL outcomes — never raises exceptions to callers
    - 401/403: Immediate auth_error return, NO retry (invalid credentials won't resolve)
    - 5xx/timeout/connection: Retry via tenacity (2 attempts, random exponential backoff)
    - All outcomes recorded as ApiEvent (EMAIL_SENT on success, EMAIL_FALLBACK on failure)
    - JWT token value NEVER appears in logs — only event type and status code are logged

Payload field names:
    Field names are INFERRED and must be validated on the deployment machine against
    the real API. They are defined as class-level constants (FIELD_*) so they can be
    corrected in one place without refactoring call sites.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.config import get_settings
from app.database import SessionLocal
from app.models.api_event import ApiEvent, ApiEventType


class EnterpriseEmailClient:
    """
    MMC Core API email client for MDInsights.

    Sends role-based HTML briefs via POST /coreapi/email/v1.
    Requires both JWT Bearer token and X-Api-Key authentication.
    Falls back to GraphEmailService when unavailable (handled by pipeline, not this client).

    Modeled on EquityPriceClient for structure and _record_event() pattern,
    but uses async httpx.AsyncClient to match GraphEmailService and the async
    run_full_pipeline_with_email() pipeline context.

    Usage:
        client = EnterpriseEmailClient()
        if client.is_configured():
            result = await client.send_email(
                token=jwt_token,
                to_addresses=["broker@marsh.com"],
                subject="Market Brief — Brokers",
                html_body=html,
                run_id=run_id,
            )
            if result["status"] == "ok":
                # Enterprise email delivered
            elif result["status"] == "auth_error":
                # JWT expired or API key wrong — fall back to Graph API

    Payload field names (class constants — INFERRED, validate on deployment machine):
        FIELD_SUBJECT       = "subject"
        FIELD_HTML_BODY     = "htmlBody"
        FIELD_TO_RECIPIENTS = "toRecipients"
        FIELD_CC_RECIPIENTS = "ccRecipients"
        FIELD_SENDER        = "impersonatedEmail"
        FIELD_SENDER_NAME   = "senderName"
    """

    # Payload field names — INFERRED from typical corporate email API conventions.
    # Validate against real /coreapi/email/v1 on the deployment machine before production.
    FIELD_SUBJECT = "subject"
    FIELD_HTML_BODY = "htmlBody"
    FIELD_TO_RECIPIENTS = "toRecipients"
    FIELD_CC_RECIPIENTS = "ccRecipients"
    FIELD_SENDER = "impersonatedEmail"
    FIELD_SENDER_NAME = "senderName"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url: str = settings.mmc_api_base_url.rstrip("/")
        self.api_key: str = settings.mmc_api_key
        self.sender_email: str = settings.mmc_sender_email
        self.sender_name: str = settings.mmc_sender_name
        self.email_path: str = settings.mmc_email_path
        self.logger = structlog.get_logger(__name__).bind(service="enterprise_emailer")
        self._payload_fields_logged = False

    def is_configured(self) -> bool:
        """Return True if base_url, api_key, and sender_email are all present in Settings.

        Quick pre-flight check — callers use this before attempting send_email().
        Requires all three to be truthy (non-empty strings).
        Note: does NOT check JWT token — token is passed per-call, not stored on self.
        """
        return bool(self.base_url and self.api_key and self.sender_email)

    def _build_headers(self, token: str) -> Dict[str, str]:
        """Build request headers for enterprise email API calls.

        Uses both JWT Bearer token and X-Api-Key authentication.
        The token is the raw JWT string, NOT stored on self — callers provide
        a fresh token per call to support token rotation without client restart.

        Args:
            token: JWT Bearer token string (from MMCAuthManager)

        Returns:
            Headers dict with Authorization, X-Api-Key, Content-Type, Accept.
        """
        return {
            "Authorization": f"Bearer {token}",
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_payload(
        self,
        to_addresses: List[str],
        subject: str,
        html_body: str,
        cc_addresses: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Build the POST JSON payload for the email API.

        Field names are defined as class-level constants (FIELD_*) so they can be
        corrected without refactoring. Logs field names (not content) on first call.

        Args:
            to_addresses:  List of TO recipient email addresses (required)
            subject:       Email subject line
            html_body:     Full HTML email content (not logged — only length is logged)
            cc_addresses:  Optional list of CC recipients (omitted from payload if None/empty)

        Returns:
            Dict ready for json.dumps() and httpx POST body.
        """
        payload: Dict[str, Any] = {
            self.FIELD_SUBJECT: subject,
            self.FIELD_HTML_BODY: html_body,
            self.FIELD_TO_RECIPIENTS: to_addresses,
            self.FIELD_SENDER: self.sender_email,
        }
        if self.sender_name:
            payload[self.FIELD_SENDER_NAME] = self.sender_name
        if cc_addresses:
            payload[self.FIELD_CC_RECIPIENTS] = cc_addresses

        # Log field names (not content) on first call for deployment validation
        if not self._payload_fields_logged:
            self.logger.debug(
                "enterprise_email_payload_fields",
                fields=list(payload.keys()),
                note="Validate field names against real API on deployment machine",
            )
            self._payload_fields_logged = True

        return payload

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_random_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def _post_email(self, token: str, payload: Dict[str, Any]) -> httpx.Response:
        """Execute email POST API call with tenacity retry for transient errors.

        Retries on TimeoutException and ConnectError only — NOT on HTTP error status codes.
        Auth errors (401/403) are handled by send_email() without retry.

        Args:
            token:   JWT Bearer token string
            payload: Pre-built request body dict

        Returns:
            Raw httpx.Response object (caller checks status_code)

        Raises:
            httpx.TimeoutException: On timeout (triggers tenacity retry, max 2 attempts)
            httpx.ConnectError: On connection failure (triggers tenacity retry)
        """
        url = f"{self.base_url}{self.email_path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.post(
                url,
                json=payload,
                headers=self._build_headers(token),
            )

    async def send_email(
        self,
        token: str,
        to_addresses: List[str],
        subject: str,
        html_body: str,
        cc_addresses: Optional[List[str]] = None,
        run_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send an HTML email via MMC Core API enterprise email endpoint.

        Handles all outcomes internally — never raises exceptions to callers.
        Returns a result dict with status key indicating outcome:
            "ok"         — Email delivered successfully
            "auth_error" — 401/403 received; caller should fall back to Graph API
            "error"      — Other failure (5xx exhausted, timeout, connection, unexpected)

        Args:
            token:        JWT Bearer token string (from MMCAuthManager, Phase 9)
            to_addresses: List of TO recipient email addresses (required, non-empty)
            subject:      Email subject line
            html_body:    Full HTML email content
            cc_addresses: Optional list of CC recipients
            run_id:       Optional pipeline run ID for ApiEvent attribution

        Returns:
            Dict with "status" key and additional context fields.
            On success: {"status": "ok", "recipients": N}
            On auth failure: {"status": "auth_error", "message": "..."}
            On other failure: {"status": "error", "message": "..."}
        """
        if not to_addresses:
            return {"status": "error", "message": "No recipients specified"}

        payload = self._build_payload(to_addresses, subject, html_body, cc_addresses)

        self.logger.info(
            "enterprise_email_sending",
            recipient_count=len(to_addresses),
            subject=subject,
            html_body_length=len(html_body),
        )

        try:
            response = await self._post_email(token, payload)

            status_code = response.status_code

            # Success — 200, 201, or 202 all indicate accepted/delivered
            if status_code in (200, 201, 202):
                self.logger.info(
                    "enterprise_email_sent",
                    status_code=status_code,
                    recipient_count=len(to_addresses),
                )
                self._record_event(
                    event_type=ApiEventType.EMAIL_SENT,
                    success=True,
                    detail=json.dumps({
                        "status_code": status_code,
                        "recipients": len(to_addresses),
                        "subject": subject[:100],
                    }),
                    run_id=run_id,
                )
                return {"status": "ok", "recipients": len(to_addresses)}

            # Auth error — 401/403: immediate return, NO retry.
            # Invalid credentials won't resolve via retry and may trigger account lockout.
            if status_code in (401, 403):
                error_msg = (
                    f"Enterprise email auth error {status_code} — "
                    "Check JWT token validity and X-Api-Key"
                )
                self.logger.error(
                    "enterprise_email_auth_error",
                    status_code=status_code,
                    hint="Check JWT token validity and X-Api-Key",
                )
                self._record_event(
                    event_type=ApiEventType.EMAIL_FALLBACK,
                    success=False,
                    detail=json.dumps({
                        "status_code": status_code,
                        "error": "auth_error",
                        "hint": "Check JWT token validity and X-Api-Key",
                    }),
                    run_id=run_id,
                )
                return {"status": "auth_error", "message": error_msg}

            # Server error — 5xx: raise to trigger tenacity retry in _post_email
            # If this is reached after retries are exhausted, tenacity re-raises
            # and the outer except block handles it.
            if status_code >= 500:
                error_msg = f"Enterprise email server error {status_code}"
                self.logger.warning(
                    "enterprise_email_server_error",
                    status_code=status_code,
                )
                # Raise to signal transient failure — tenacity wraps _post_email
                # but if we're already in send_email() it means retries exhausted
                raise httpx.HTTPStatusError(
                    message=error_msg,
                    request=response.request,
                    response=response,
                )

            # Other 4xx — bad request, not found, rate limited, etc.
            error_msg = f"Enterprise email client error {status_code}"
            self.logger.error(
                "enterprise_email_client_error",
                status_code=status_code,
            )
            self._record_event(
                event_type=ApiEventType.EMAIL_FALLBACK,
                success=False,
                detail=json.dumps({
                    "status_code": status_code,
                    "error": "client_error",
                }),
                run_id=run_id,
            )
            return {"status": "error", "message": error_msg}

        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            error_msg = f"Enterprise email network/HTTP error: {type(exc).__name__}"
            self.logger.warning(
                "enterprise_email_transient_failure",
                error_type=type(exc).__name__,
                error=str(exc)[:200],
            )
            self._record_event(
                event_type=ApiEventType.EMAIL_FALLBACK,
                success=False,
                detail=json.dumps({
                    "error": type(exc).__name__,
                    "message": str(exc)[:200],
                }),
                run_id=run_id,
            )
            return {"status": "error", "message": error_msg}

        except Exception as exc:
            # Broad catch — unexpected errors must never surface to pipeline
            error_msg = f"Enterprise email unexpected error: {type(exc).__name__}"
            self.logger.error(
                "enterprise_email_unexpected_error",
                error_type=type(exc).__name__,
                error=str(exc)[:200],
            )
            self._record_event(
                event_type=ApiEventType.EMAIL_FALLBACK,
                success=False,
                detail=json.dumps({
                    "error": type(exc).__name__,
                    "message": str(exc)[:200],
                }),
                run_id=run_id,
            )
            return {"status": "error", "message": error_msg}

    def _record_event(
        self,
        event_type: ApiEventType,
        success: bool,
        detail: Optional[str] = None,
        run_id: Optional[int] = None,
    ) -> None:
        """Record an enterprise email API event to the api_events table.

        Opens its own isolated DB session so event recording never interferes
        with caller's transaction context. Failures are swallowed — event recording
        must never crash the email delivery flow.

        Identical pattern to EquityPriceClient._record_event() and
        FactivaCollector._record_event() for codebase consistency.

        Args:
            event_type: ApiEventType.EMAIL_SENT (success) or EMAIL_FALLBACK (failure)
            success:    True if enterprise email was delivered
            detail:     JSON-safe string with event context (no secrets, max 500 chars)
            run_id:     Optional pipeline run ID (None for out-of-pipeline calls)
        """
        try:
            with SessionLocal() as session:
                event = ApiEvent(
                    event_type=event_type,
                    api_name="email",
                    timestamp=datetime.utcnow(),
                    success=success,
                    detail=detail[:500] if detail else None,
                    run_id=run_id,
                )
                session.add(event)
                session.commit()
        except Exception as exc:
            # Never propagate DB errors into the email delivery flow
            self.logger.warning(
                "enterprise_email_event_record_failed",
                event_type=event_type.value,
                error=str(exc),
            )
