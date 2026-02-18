"""
OAuth2 client credentials token manager for MMC Core API.

Acquires JWT tokens from the Access Management API using the client_credentials
grant, caches them in memory, and proactively refreshes tokens before expiry.

All enterprise API calls that require Bearer token authentication (Email API)
should call TokenManager.get_token() to obtain a valid JWT.

Auth event recording:
    Every acquisition, refresh, and failure is recorded to the api_events table
    so the Phase 13 admin dashboard can display real-time auth health status.

Security contract:
    - NEVER logs client_id, client_secret, or raw token values
    - Detail strings stored in api_events are JSON-safe and secret-free
    - Credentials are read from Settings at construction time only
"""
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.config import get_settings
from app.database import SessionLocal
from app.models.api_event import ApiEvent, ApiEventType

logger = structlog.get_logger(__name__)


@dataclass
class TokenInfo:
    """Cached JWT token with expiry metadata."""
    access_token: str
    expires_at: float  # Unix timestamp when token expires
    token_type: str = "Bearer"


class TokenManager:
    """
    OAuth2 client credentials token manager for MMC Core API.

    Usage:
        tm = TokenManager()
        token = await tm.get_token()  # Returns cached or fresh JWT string
        if token:
            headers = {"Authorization": f"Bearer {token}"}

    Token lifecycle:
        1. First call to get_token() acquires a token from the Access Management API
        2. Subsequent calls return the cached token (no network request)
        3. When token is within REFRESH_MARGIN_SECONDS of expiry, a fresh token
           is automatically acquired on the next get_token() call
        4. force_refresh() invalidates the cache and acquires a new token immediately

    Error handling:
        - 401/403 (invalid credentials): Returns None immediately, no retry
        - 429/5xx (transient): Retries up to 3 times with exponential backoff
        - Network errors: Retries up to 3 times with exponential backoff
        - All failures: Recorded to api_events table for dashboard visibility
    """

    REFRESH_MARGIN_SECONDS = 300  # Refresh 5 minutes before expiry

    def __init__(self):
        settings = get_settings()
        self._base_url = settings.mmc_api_base_url
        self._client_id = settings.mmc_api_client_id
        self._client_secret = settings.mmc_api_client_secret
        self._token_path = settings.mmc_api_token_path
        self._token: Optional[TokenInfo] = None

        if not settings.is_mmc_auth_configured():
            logger.warning(
                "mmc_auth_not_configured",
                hint="Set MMC_API_BASE_URL, MMC_API_CLIENT_ID, MMC_API_CLIENT_SECRET in .env",
            )

    def is_configured(self) -> bool:
        """Return True if MMC OAuth2 credentials are present in Settings."""
        return get_settings().is_mmc_auth_configured()

    @property
    def is_token_valid(self) -> bool:
        """Return True if the cached token exists and is not near expiry."""
        if self._token is None:
            return False
        return self._token.expires_at > time.time() + self.REFRESH_MARGIN_SECONDS

    async def get_token(self) -> Optional[str]:
        """
        Return a valid JWT access token, acquiring one if necessary.

        Returns:
            JWT token string on success, None on failure.

        This is the primary entry point for all consumers (Phase 12 email service).
        The method is safe to call on every request — it returns the cached token
        when still valid and only makes a network call when acquisition/refresh
        is needed.
        """
        if self.is_token_valid:
            return self._token.access_token

        return await self._acquire_token()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    async def _acquire_token(self) -> Optional[str]:
        """
        POST to Access Management API to obtain a JWT via client_credentials grant.

        Internal method — call get_token() from external code.

        Retry policy:
            - 429 / 5xx / network errors: up to 3 attempts with exponential backoff
            - 401 / 403 (bad credentials): no retry, return None immediately
        """
        is_refresh = self._token is not None  # True if replacing an existing token

        token_url = f"{self._base_url}{self._token_path}"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    token_url,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

            if response.status_code == 200:
                data = response.json()
                expires_in = int(data.get("expires_in", 3600))
                token_type = data.get("token_type", "Bearer")
                access_token = data["access_token"]

                self._token = TokenInfo(
                    access_token=access_token,
                    expires_at=time.time() + expires_in,
                    token_type=token_type,
                )

                event_type = ApiEventType.TOKEN_REFRESHED if is_refresh else ApiEventType.TOKEN_ACQUIRED
                logger.info(
                    "token_acquired" if not is_refresh else "token_refreshed",
                    expires_in_seconds=expires_in,
                    token_type=token_type,
                )
                self._record_event(
                    event_type=event_type,
                    success=True,
                    detail=json.dumps({
                        "expires_in_seconds": expires_in,
                        "token_type": token_type,
                    }),
                )
                return access_token

            elif response.status_code in (401, 403):
                # Invalid credentials — retrying won't help
                logger.error(
                    "token_acquisition_auth_failed",
                    status_code=response.status_code,
                    hint="Check MMC_API_CLIENT_ID and MMC_API_CLIENT_SECRET",
                )
                self._record_event(
                    event_type=ApiEventType.TOKEN_FAILED,
                    success=False,
                    detail=json.dumps({
                        "status_code": response.status_code,
                        "error": "invalid_credentials",
                    }),
                )
                return None

            elif response.status_code == 429:
                # Rate limited — raise to trigger tenacity retry
                logger.warning(
                    "token_acquisition_rate_limited",
                    status_code=response.status_code,
                )
                response.raise_for_status()

            elif response.status_code >= 500:
                # Server error — raise to trigger tenacity retry
                logger.warning(
                    "token_acquisition_server_error",
                    status_code=response.status_code,
                )
                response.raise_for_status()

            else:
                # Unexpected client error — record and return None
                logger.error(
                    "token_acquisition_unexpected_error",
                    status_code=response.status_code,
                )
                self._record_event(
                    event_type=ApiEventType.TOKEN_FAILED,
                    success=False,
                    detail=json.dumps({
                        "status_code": response.status_code,
                        "error": "unexpected_client_error",
                    }),
                )
                return None

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            # Transient network error — raise to trigger tenacity retry
            logger.warning(
                "token_acquisition_network_error",
                error_type=type(exc).__name__,
            )
            raise

        except httpx.HTTPStatusError as exc:
            # Raised by raise_for_status() for 429/5xx — trigger retry
            logger.warning(
                "token_acquisition_http_error",
                status_code=exc.response.status_code,
            )
            raise

        except Exception as exc:
            # Unexpected error — record and return None (do not retry)
            logger.error(
                "token_acquisition_unexpected_exception",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            self._record_event(
                event_type=ApiEventType.TOKEN_FAILED,
                success=False,
                detail=json.dumps({
                    "error": type(exc).__name__,
                    "message": str(exc)[:200],  # Truncate to keep detail field bounded
                }),
            )
            return None

        # After all retries exhausted by tenacity (reraise=False), record failure
        self._record_event(
            event_type=ApiEventType.TOKEN_FAILED,
            success=False,
            detail=json.dumps({"error": "max_retries_exceeded"}),
        )
        return None

    def _record_event(
        self,
        event_type: ApiEventType,
        success: bool,
        detail: Optional[str] = None,
        run_id: Optional[int] = None,
    ) -> None:
        """
        Record an auth event to the api_events table.

        Opens its own DB session so event recording never interferes with
        caller's transaction context. Failures are swallowed — event recording
        must never crash the token acquisition flow.

        Args:
            event_type: One of TOKEN_ACQUIRED, TOKEN_REFRESHED, TOKEN_FAILED
            success: Whether the auth operation succeeded
            detail: JSON-safe string with event context (no secrets)
            run_id: Optional pipeline run ID (None for out-of-pipeline calls)
        """
        try:
            with SessionLocal() as session:
                event = ApiEvent(
                    event_type=event_type,
                    api_name="auth",
                    timestamp=datetime.utcnow(),
                    success=success,
                    detail=detail,
                    run_id=run_id,
                )
                session.add(event)
                session.commit()
        except Exception as exc:
            # Never propagate DB errors into the token flow
            logger.warning(
                "api_event_record_failed",
                event_type=event_type.value,
                error=str(exc),
            )

    async def force_refresh(self) -> Optional[str]:
        """
        Invalidate the cached token and immediately acquire a fresh one.

        Used by scripts/test_auth.py to verify the full refresh cycle works.
        Also useful if a downstream service reports an expired/invalid token
        despite the cache showing it as valid (e.g. server-side revocation).

        Returns:
            Fresh JWT token string on success, None on failure.
        """
        logger.info("token_force_refresh_requested")
        self._token = None
        result = await self._acquire_token()
        if result:
            logger.info("token_force_refresh_succeeded")
        else:
            logger.error("token_force_refresh_failed")
        return result
