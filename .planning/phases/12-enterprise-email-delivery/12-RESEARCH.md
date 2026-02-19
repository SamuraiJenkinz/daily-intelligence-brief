# Phase 12: Enterprise Email Delivery - Research

**Researched:** 2026-02-18
**Domain:** Enterprise email client (MMC Core API), pipeline delivery step integration, Graph API fallback, ApiEvent recording
**Confidence:** HIGH — all findings based on direct codebase analysis. Email API request schema is LOW confidence (PDFs are image-based, unreadable).

---

## Summary

Phase 12 adds an enterprise email delivery path to the pipeline. The pipeline already collects, classifies, generates role-based HTML briefs, archives them to disk, and sends them via Microsoft Graph API (Step 8). Phase 12 replaces Step 8 with a new delivery layer: try the MMC Core API email endpoint first (`POST /coreapi/email/v1` with JWT Bearer + X-Api-Key), fall back to the existing `GraphEmailService` if the enterprise endpoint is unavailable, and record the delivery outcome as an `ApiEvent` per send.

The codebase is completely prepared for this phase. `ApiEventType` already defines `EMAIL_SENT` and `EMAIL_FALLBACK`. `TokenManager.get_token()` is the entry point for JWT (Phase 9, fully implemented). The `degraded_auth` flag in `run_full_pipeline_with_email()` is the decision point: when `True`, skip the enterprise path entirely and use Graph API. When `False`, attempt enterprise delivery with fallback. `GraphEmailService` is the confirmed fallback implementation, already wired into the pipeline.

The enterprise email API shape (request payload fields, sender identity field names) is NOT confirmed from API documentation — the PDF files are image-based and unreadable by tools. Field names `impersonatedEmail` and `permittedEmailImpersonation` appear only in REQUIREMENTS.md as alternatives — which one the API actually uses must be validated on first test run. The plan must build the client with named constants for these field names so they can be corrected without touching request logic.

**Primary recommendation:** Model `EnterpriseEmailClient` on `EquityPriceClient` and `FactivaCollector` — same httpx + tenacity + structlog + `_record_event` pattern. Replace Step 8 in `run_full_pipeline_with_email()` with a delivery orchestrator that checks `degraded_auth`, attempts enterprise, falls back to Graph, records outcome.

---

## Standard Stack

All libraries already in `requirements.txt`. No new dependencies required.

### Core (already present)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | pinned | Async HTTP client for enterprise email POST | Used by `token_manager.py`, `emailer.py`; async pattern matches pipeline |
| `tenacity` | pinned | Retry with exponential backoff | Used in all collectors and emailer.py; handles 5xx/timeout |
| `structlog` | pinned | Structured logging | Project-wide standard |
| `sqlalchemy` | pinned | ORM for `ApiEvent` recording | Already used by all collectors |
| `pydantic-settings` | pinned | Settings / env var access | `get_settings()` pattern |

### No New Dependencies
Enterprise email is a plain authenticated REST endpoint. All tooling already present.

**Installation:** No new packages.

---

## Architecture Patterns

### Additions to Project Structure

```
app/
├── services/
│   ├── emailer.py             # EXISTING — GraphEmailService (fallback path)
│   └── enterprise_emailer.py  # NEW: EnterpriseEmailClient class
│                               #   OR add to emailer.py as second class
├── config.py                  # UPDATE: add mmc_sender_email, mmc_sender_name,
│                               #   mmc_email_path; add is_mmc_email_configured()
├── services/
│   └── pipeline.py            # UPDATE: replace Step 8 with enterprise-first delivery
└── .env.example               # UPDATE: add new MMC email env vars
```

### Pattern 1: EnterpriseEmailClient (models EquityPriceClient exactly)

The client follows the identical structure as `EquityPriceClient` and `FactivaCollector`, but uses **async httpx** (matching `GraphEmailService`) because `run_full_pipeline_with_email()` is async.

```python
# Source: app/collectors/equity.py — reference sync pattern
# Source: app/services/emailer.py — reference async pattern
# app/services/enterprise_emailer.py

import json
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
    before_sleep_log,
)

from app.config import get_settings
from app.database import SessionLocal
from app.models.api_event import ApiEvent, ApiEventType


class EnterpriseEmailClient:
    """
    MMC Core API email client for MDInsights.

    Sends role-based HTML briefs via POST /coreapi/email/v1.
    Requires both JWT Bearer token and X-Api-Key authentication.

    Usage:
        client = EnterpriseEmailClient()
        if client.is_configured():
            result = await client.send_email(
                token=jwt_token,
                to_addresses=["user@marsh.com"],
                subject="[Marsh] Brokers Brief",
                html_body=html,
            )
            # Returns {"status": "ok"} or {"status": "error", "message": "..."}
    """

    EMAIL_PATH = "/coreapi/email/v1"  # Confirm on deployment

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url: str = settings.mmc_api_base_url.rstrip("/")
        self.api_key: str = settings.mmc_api_key
        self.sender_email: str = settings.mmc_sender_email  # New config field
        self.sender_name: str = settings.mmc_sender_name    # New config field
        self.logger = structlog.get_logger(__name__).bind(service="enterprise_emailer")

    def is_configured(self) -> bool:
        """Return True if enterprise email credentials are present."""
        return bool(self.base_url and self.api_key and self.sender_email)

    def _build_headers(self, token: str) -> Dict[str, str]:
        """Build request headers with JWT Bearer and X-Api-Key."""
        return {
            "Authorization": f"Bearer {token}",
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_random_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def _post_email(
        self,
        token: str,
        payload: Dict[str, Any],
    ) -> httpx.Response:
        """Execute the email POST request with tenacity retry."""
        url = f"{self.base_url}{self.EMAIL_PATH}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers=self._build_headers(token),
                json=payload,
            )
            return response

    async def send_email(
        self,
        token: str,
        to_addresses: list[str],
        subject: str,
        html_body: str,
        cc_addresses: list[str] | None = None,
        run_id: int | None = None,
    ) -> Dict[str, Any]:
        """
        Send an HTML email via the MMC Core API email endpoint.

        Returns {"status": "ok", ...} on success.
        Returns {"status": "error", "message": "..."} on failure.
        Never raises exceptions to callers.
        """
        if not to_addresses:
            return {"status": "error", "message": "No recipients specified"}

        # Build payload — field names inferred, must validate on deployment
        # See Open Questions: actual field names for sender impersonation unknown
        payload = self._build_payload(to_addresses, subject, html_body, cc_addresses)

        try:
            response = await self._post_email(token=token, payload=payload)

            if response.status_code in (200, 201, 202):
                self.logger.info(
                    "enterprise_email_sent",
                    recipient_count=len(to_addresses),
                    subject=subject,
                    status_code=response.status_code,
                )
                self._record_event(
                    event_type=ApiEventType.EMAIL_SENT,
                    success=True,
                    detail=json.dumps({
                        "recipients": len(to_addresses),
                        "subject": subject[:100],
                    }),
                    run_id=run_id,
                )
                return {"status": "ok", "recipients": len(to_addresses)}

            elif response.status_code in (401, 403):
                # Auth error — do NOT retry, signal immediate fallback to Graph
                error_msg = f"Auth error {response.status_code}: {response.text[:200]}"
                self.logger.error(
                    "enterprise_email_auth_failed",
                    status_code=response.status_code,
                    hint="Check JWT token validity and X-Api-Key",
                )
                self._record_event(
                    event_type=ApiEventType.EMAIL_FALLBACK,
                    success=False,
                    detail=json.dumps({
                        "status_code": response.status_code,
                        "error": "auth_failed",
                    }),
                    run_id=run_id,
                )
                return {"status": "auth_error", "message": error_msg}

            elif response.status_code >= 500:
                # Server error — raise to trigger tenacity retry
                error_msg = f"Server error {response.status_code}"
                raise httpx.NetworkError(error_msg)

            else:
                # Other client error (4xx)
                error_msg = f"Client error {response.status_code}: {response.text[:200]}"
                self.logger.error(
                    "enterprise_email_client_error",
                    status_code=response.status_code,
                )
                self._record_event(
                    event_type=ApiEventType.EMAIL_FALLBACK,
                    success=False,
                    detail=json.dumps({
                        "status_code": response.status_code,
                        "error": "client_error",
                    }),
                    run_id=run_id,
                )
                return {"status": "error", "message": error_msg}

        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
            error_msg = f"{type(exc).__name__}: {str(exc)[:200]}"
            self.logger.warning(
                "enterprise_email_network_error",
                error_type=type(exc).__name__,
                error=str(exc)[:200],
            )
            self._record_event(
                event_type=ApiEventType.EMAIL_FALLBACK,
                success=False,
                detail=json.dumps({"error": type(exc).__name__, "message": str(exc)[:200]}),
                run_id=run_id,
            )
            return {"status": "error", "message": error_msg}

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {str(exc)[:200]}"
            self.logger.error(
                "enterprise_email_unexpected_error",
                error_type=type(exc).__name__,
                error=str(exc)[:200],
            )
            self._record_event(
                event_type=ApiEventType.EMAIL_FALLBACK,
                success=False,
                detail=json.dumps({"error": type(exc).__name__, "message": str(exc)[:200]}),
                run_id=run_id,
            )
            return {"status": "error", "message": error_msg}

    def _build_payload(
        self,
        to_addresses: list[str],
        subject: str,
        html_body: str,
        cc_addresses: list[str] | None,
    ) -> Dict[str, Any]:
        """
        Build the email POST payload.

        IMPORTANT: Field names are inferred — must validate against real API.
        The REQUIREMENTS.md references 'impersonatedEmail' and
        'permittedEmailImpersonation' as alternatives for sender identity.
        Log the actual payload structure (minus body) at DEBUG on first successful
        call so the team can verify field names are correct.
        """
        payload: Dict[str, Any] = {
            "subject": subject,
            "htmlBody": html_body,  # Inferred field name — may be "body", "html", "content"
            "toRecipients": to_addresses,  # Inferred — may be "to", "recipients", "toEmails"
            # Sender identity field — one of these, must verify:
            "impersonatedEmail": self.sender_email,
        }

        if cc_addresses:
            payload["ccRecipients"] = cc_addresses  # Inferred — may be "cc"

        return payload

    def _record_event(
        self,
        event_type: ApiEventType,
        success: bool,
        detail: Optional[str] = None,
        run_id: Optional[int] = None,
    ) -> None:
        """
        Record an email API event to api_events.

        Opens own DB session. Failures swallowed — recording never crashes delivery.
        Identical pattern to FactivaCollector._record_event().
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
            self.logger.warning(
                "enterprise_email_event_record_failed",
                event_type=event_type.value,
                error=str(exc),
            )
```

### Pattern 2: New Config Fields

Add enterprise email sender settings to `app/config.py`. The existing `sender_email` is for Graph API only; enterprise uses a separate mailbox.

```python
# In app/config.py Settings class — add after existing MMC Core API section
# Enterprise email sender (separate from Graph API sender_email)
mmc_sender_email: str = ""    # Env var: MMC_SENDER_EMAIL
mmc_sender_name: str = "Kevin Taylor"  # Env var: MMC_SENDER_NAME (display name)
mmc_email_path: str = "/coreapi/email/v1"  # Env var: MMC_EMAIL_PATH (configurable)

def is_mmc_email_configured(self) -> bool:
    """Check if enterprise email is fully configured.

    Requires JWT auth (mmc_auth) + API key + sender email.
    """
    return bool(
        self.is_mmc_auth_configured()
        and self.mmc_api_key
        and self.mmc_sender_email
    )
```

**Env vars to add to `.env.example`:**
```
# Enterprise Email Sender (MMC Core API, separate from Graph API sender)
MMC_SENDER_EMAIL=kevin.taylor@mmc.com    # Enterprise mailbox to send from
MMC_SENDER_NAME=Kevin Taylor             # Display name for enterprise path
```

### Pattern 3: Pipeline Step 8 Replacement

Replace the current Step 8 in `run_full_pipeline_with_email()` with enterprise-first delivery. The `degraded_auth` flag set in Step 0 determines whether to attempt enterprise at all.

```python
# In app/services/pipeline.py — replace current Step 8 block
# Step 8: Send emails per role (enterprise primary, Graph API fallback)
step_start = datetime.utcnow()
self.logger.info("step_8_email_delivery_started")

enterprise_client = EnterpriseEmailClient()
graph_service = GraphEmailService()
settings = get_settings()

for role, html in role_emails.items():
    recipients = settings.get_email_recipients(role)

    if not recipients.has_recipients:
        self.logger.info("skipping_email_no_recipients", role=role)
        result["emails_sent"][role] = {"status": "skipped", "message": "No recipients configured"}
        continue

    subject = f"[{settings.company_name}] {role} Intelligence Brief - {report_date.strftime('%d %B %Y')}"

    delivery_result = await self._send_with_fallback(
        role=role,
        subject=subject,
        html=html,
        recipients=recipients,
        degraded_auth=degraded_auth,
        enterprise_client=enterprise_client,
        graph_service=graph_service,
        run_id=latest_run.id,
    )
    result["emails_sent"][role] = delivery_result
    self.logger.info(
        "email_delivery_outcome",
        role=role,
        status=delivery_result.get("status"),
        path=delivery_result.get("path"),
    )
```

**Delivery orchestrator method (extracted for testability):**

```python
async def _send_with_fallback(
    self,
    role: str,
    subject: str,
    html: str,
    recipients,
    degraded_auth: bool,
    enterprise_client,
    graph_service,
    run_id: int,
) -> dict:
    """
    Attempt enterprise email delivery, fall back to Graph API on failure.

    degraded_auth=True: Skip enterprise entirely (no JWT available).
    auth_error on enterprise: Immediate fallback to Graph (no retry).
    5xx / timeout on enterprise: After tenacity retries, fall back to Graph.
    Graph failure: Return error, pipeline continues.

    Returns delivery outcome dict with status and path fields.
    """
    # degraded_auth=True means no JWT token — skip enterprise entirely
    if not degraded_auth and enterprise_client.is_configured():
        token = await self.token_manager.get_token()
        if token:
            enterprise_result = await enterprise_client.send_email(
                token=token,
                to_addresses=recipients.to,
                subject=subject,
                html_body=html,
                cc_addresses=recipients.cc or None,
                run_id=run_id,
            )
            if enterprise_result.get("status") == "ok":
                return {**enterprise_result, "path": "enterprise"}

            # Enterprise failed — fall through to Graph API
            self.logger.warning(
                "enterprise_email_failed_falling_back",
                role=role,
                error=enterprise_result.get("message"),
            )
        else:
            self.logger.warning("enterprise_email_skipped_no_token", role=role)

    # Graph API fallback (or primary when degraded_auth=True)
    graph_result = await graph_service.send_email(
        to_addresses=recipients.to,
        subject=subject,
        html_body=html,
        cc_addresses=recipients.cc or None,
        bcc_addresses=recipients.bcc or None,
    )

    path = "graph_fallback" if (not degraded_auth) else "graph_primary"
    return {**graph_result, "path": path}
```

### Pattern 4: Per-Role Independent Fallback

Each role is delivered independently. If enterprise succeeds for Brokers but fails for Leadership, Brokers gets enterprise delivery and Leadership falls back to Graph. The pipeline does not fail-fast to Graph on first enterprise failure.

**Rationale:** Per-role errors are likely transient (rate limit, timeout on one call). Fail-fast would degrade all roles unnecessarily when only one role's send encountered a problem.

**Pipeline status with mixed delivery:**
- All roles "ok": `result["status"] = "completed"`
- Some roles failed (both paths): `result["status"] = "completed_with_delivery_failure"` — new status value
- All roles failed: same `"completed_with_delivery_failure"`
- The Run record `status` stays `COMPLETED` — email delivery is not a blocking failure (reports are archived)

### Pattern 5: Delivery Recording Granularity

Record one `ApiEvent` per send attempt per role (per path):
- Enterprise attempt success: `EMAIL_SENT`, `api_name="email"`, `success=True`
- Enterprise attempt failure + fallback: `EMAIL_FALLBACK`, `api_name="email"`, `success=False`, detail includes role and error
- Graph API fallback success: no additional `ApiEvent` (Graph is not an enterprise API)
- `run_id` always populated (pipeline delivery always has a run context)

The `result["emails_sent"][role]` dict includes a `"path"` key (`"enterprise"`, `"graph_fallback"`, `"graph_primary"`, `"skipped"`) for dashboard visibility.

### Anti-Patterns to Avoid

- **Retrying on 401/403**: Auth errors signal bad credentials, not transient failures. Immediate fallback to Graph. No retry. This matches the Phase 9 decision in `TokenManager._acquire_token()`.
- **Halting the pipeline on email failure**: If both enterprise and Graph fail for a role, log the failure, continue to next role, mark delivery outcome, continue pipeline. All reports are already archived (Step 7).
- **Single-send failure propagating to all roles**: Each role is wrapped in its own try/except. One role's failure does not prevent other roles from being delivered.
- **Using sync httpx in enterprise client**: `run_full_pipeline_with_email()` is async. Use `httpx.AsyncClient`, not `httpx.Client`. This differs from `EquityPriceClient` which uses sync httpx (because `run_full_pipeline()` is sync).
- **Exposing JWT token in logs**: Never pass `token` value to logger. Log only event type, status code, error text (sanitized).
- **Hardcoding email payload field names**: Build `_build_payload()` with named constants or clearly named variables for field names (`impersonatedEmail`, `toRecipients`, `htmlBody`). These must be correctable without refactoring request logic.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry with backoff | Custom retry loop | `tenacity` with `retry_if_exception_type` | Already in every service; handles timeout/connect correctly |
| Structured logging | `print()` / `logging` | `structlog.get_logger()` | Project-wide standard |
| DB session isolation for events | Pass session to `_record_event` | Open own session inside, swallow errors | Same pattern as factiva/equity — event recording never crashes delivery |
| JWT token management | Fresh token acquisition per send | `self.token_manager.get_token()` (TokenManager) | Phase 9 — caches token with TTL, handles refresh, handles failures |
| Graph API fallback implementation | Re-implement Graph send | `GraphEmailService.send_email()` | Already fully implemented in `app/services/emailer.py` |
| Async/sync decision | Choose httpx.Client vs AsyncClient | `httpx.AsyncClient` | Pipeline is async; match `GraphEmailService` pattern not `EquityPriceClient` |

---

## Common Pitfalls

### Pitfall 1: Email API request payload field names unknown
**What goes wrong:** POST to `/coreapi/email/v1` fails with 400 Bad Request because payload field names are wrong.
**Why it happens:** The `emailref.pdf` and `emailaip.pdf` files are image-based (confirmed unreadable). `REQUIREMENTS.md` mentions `impersonatedEmail` or `permittedEmailImpersonation` for sender identity but does not specify which one the API actually uses, nor the correct names for `toRecipients`, `htmlBody`, etc.
**How to avoid:** Build `_build_payload()` with clearly named constants for each field. On first test run, log the raw request payload at DEBUG level (minus HTML body content, which is too large). Validate against real API on the deployment machine. The `EMAIL_PATH` class constant should also be validated — confirm `/coreapi/email/v1` is the actual path.
**Warning signs:** 400 Bad Request on POST — payload shape is wrong. 422 Unprocessable — fields present but wrong structure.

### Pitfall 2: Using sync httpx instead of async
**What goes wrong:** `httpx.Client` (sync) called from an async context causes blocking or event loop conflict.
**Why it happens:** `EquityPriceClient` uses `httpx.Client` (sync) because `run_full_pipeline()` is sync. The email client must be async because `run_full_pipeline_with_email()` is async.
**How to avoid:** Use `httpx.AsyncClient` with `await client.post(...)` throughout the enterprise email client. Check: `async def send_email(...)` and `await client.post(...)` — both must be async.

### Pitfall 3: Acquiring a fresh token on every send
**What goes wrong:** For 4 roles, token is fetched 4 times, each requiring a network call.
**Why it happens:** Calling `self.token_manager.get_token()` inside the per-role loop without caching the result for the batch.
**How to avoid:** Fetch the token once before the per-role loop, pass it into `_send_with_fallback()`. `TokenManager.get_token()` is safe to call multiple times (returns cached token), but one call before the loop is cleaner and avoids async overhead per role.

### Pitfall 4: Enterprise sender mailbox not configured
**What goes wrong:** `is_mmc_email_configured()` returns False because `MMC_SENDER_EMAIL` is empty, causing all 4 roles to skip enterprise and use Graph API — with no log indicating why.
**Why it happens:** `MMC_SENDER_EMAIL` is a new env var that won't be set on existing deployments without explicit configuration.
**How to avoid:** Log a clear info event at pipeline start if enterprise email is unconfigured: `"enterprise_email_not_configured: missing MMC_SENDER_EMAIL, will use Graph API"`. This must be distinguishable from the `degraded_auth=True` path (JWT failed).

### Pitfall 5: Both delivery paths fail silently
**What goes wrong:** Enterprise fails, Graph API also fails (e.g., Graph credentials expired). Pipeline logs individual failures but overall status shows "completed", masking the delivery failure.
**Why it happens:** Pipeline status is set to `"completed"` regardless of email outcome.
**How to avoid:** After the per-role delivery loop, count roles with failed delivery (both paths returned error). If any failures exist, set `result["status"] = "completed_with_delivery_failure"`. Log a summary. The Run record status stays `COMPLETED` (reports are archived, pipeline did its work).

### Pitfall 6: Subject line inconsistency across delivery paths
**What goes wrong:** Enterprise-delivered emails have a different subject format than Graph-delivered emails, confusing recipients.
**Why it happens:** Subject is built per path with different formatting.
**How to avoid:** Build the `subject` string once before calling `_send_with_fallback()`. Pass the same subject string to both enterprise and Graph. Use the existing format: `f"[{settings.company_name}] {role} Intelligence Brief - {report_date.strftime('%d %B %Y')}"`. Keep consistent regardless of delivery path.

### Pitfall 7: Tenacity reraise=True vs reraise=False
**What goes wrong:** If `reraise=True` on `_post_email`, a timeout after 2 retries raises an exception that bypasses the fallback logic.
**Why it happens:** Tenacity `reraise=True` re-raises the last exception after exhausting retries. The outer `send_email()` caller must catch it.
**How to avoid:** Either: (a) set `reraise=False` on `_post_email` (returns None after exhausted retries) and check for None in `send_email()`, OR (b) set `reraise=True` and ensure the outer `send_email()` `except` block catches it. Option (a) is cleaner — consistent with how EquityPriceClient uses `reraise` (implicitly False via tenacity's default) for the public API, raising explicitly inside `get_price()` where appropriate.

---

## Code Examples

### 1. EnterpriseEmailClient is_configured guard

```python
# Source: app/collectors/equity.py is_configured() — reference pattern
def is_configured(self) -> bool:
    """Return True if base URL, API key, and sender email are all present."""
    return bool(self.base_url and self.api_key and self.sender_email)
```

### 2. Delivery decision logic in pipeline

```python
# Source: app/services/pipeline.py Step 0 auth pattern — reference
# degraded_auth=True means JWT acquisition failed at Step 0
# Skip enterprise entirely — don't waste a network call that will 401
if not degraded_auth and enterprise_client.is_configured():
    # Attempt enterprise delivery
    ...
else:
    # Graph API primary (degraded_auth) or not configured
    graph_result = await graph_service.send_email(...)
```

### 3. ApiEvent recording for fallback (reference: FactivaCollector)

```python
# Source: app/collectors/factiva.py _record_event() — definitive pattern
# Record EMAIL_FALLBACK when enterprise fails (before attempting Graph)
self._record_event(
    event_type=ApiEventType.EMAIL_FALLBACK,
    success=False,
    detail=json.dumps({
        "role": role,
        "error": str(exc)[:200],
        "fallback_to": "graph_api",
    }),
    run_id=run_id,
)
```

### 4. Isolated DB session pattern (reference: all collectors)

```python
# Source: app/collectors/factiva.py _record_event() — definitive pattern
def _record_event(self, event_type, success, detail=None, run_id=None):
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
        self.logger.warning("email_event_record_failed", error=str(exc))
        # NEVER propagate — event recording cannot crash delivery
```

### 5. Subject line (keep consistent, build once)

```python
# Source: app/services/pipeline.py Step 8 existing pattern
# Build subject ONCE before fallback decision
subject = (
    f"[{settings.company_name}] {role} Intelligence Brief - "
    f"{report_date.strftime('%d %B %Y')}"
)
# Same subject passed to enterprise and Graph fallback
```

---

## State of the Art

| Old Approach (v1.0) | Current Approach (v1.1) | When Changed | Impact |
|---------------------|-------------------------|--------------|--------|
| Graph API only (Step 8) | Enterprise primary, Graph fallback | Phase 12 | Enterprise sender identity; Graph retained as guaranteed fallback |
| No delivery path recording | `path` field in delivery result + `ApiEvent` per send | Phase 12 | Admin dashboard (Phase 13) can show delivery path per run |
| `run_full_pipeline_with_email` Step 8 inline | Extracted `_send_with_fallback()` method | Phase 12 | Testable, reusable delivery logic |

**Already in place (no changes needed):**
- `ApiEventType.EMAIL_SENT` and `ApiEventType.EMAIL_FALLBACK` — defined in `app/models/api_event.py`
- `degraded_auth` flag in `run_full_pipeline_with_email()` result — set at Step 0 from `TokenManager`
- `TokenManager.get_token()` — Phase 9 implementation, production-ready
- `GraphEmailService.send_email()` — Phase 5 implementation, production-ready fallback
- `settings.get_email_recipients(role)` — returns `EmailRecipients` with TO/CC/BCC

---

## Open Questions

### 1. Email API request payload field names
**What we know:** Endpoint is `POST /coreapi/email/v1`. Authentication is JWT Bearer + X-Api-Key. REQUIREMENTS.md mentions `impersonatedEmail` or `permittedEmailImpersonation` as alternatives for sender identity. The API likely accepts a JSON body with recipient addresses, subject, HTML body, and sender identity.
**What's unclear:** Exact field names for: HTML body content (`htmlBody`? `body`? `content`?), recipients (`toRecipients`? `to`? `recipients`?), sender identity (`impersonatedEmail`? `permittedEmailImpersonation`? `fromEmail`?), and whether success is indicated by 200, 201, or 202.
**Recommendation:** Build `_build_payload()` with named constants (not scattered string literals). Log the actual request payload structure at DEBUG on first call (excluding HTML body). Validate against real API on deployment machine — same validation approach as Factiva and equity endpoints. Accept 200, 201, and 202 as success codes.

### 2. Enterprise email success response code
**What we know:** Graph API returns 202 (Accepted) for email send. Many email APIs return 202 for async delivery, 200 for synchronous.
**What's unclear:** Whether `/coreapi/email/v1` returns 200, 201, or 202 on success.
**Recommendation:** Accept all of 200, 201, 202 as success. Log the actual status code received on first test.

### 3. HTML body size limits
**What we know:** Role-based HTML briefs are large (full formatted news brief with inline equity data). Graph API handles them without issues. Enterprise API may have a request body size limit.
**What's unclear:** Whether `/coreapi/email/v1` imposes a payload size limit on the HTML body.
**Recommendation:** Log `len(html_body)` at INFO when sending. If 413 (Payload Too Large) is encountered, note the body length in the error and add to open questions for the API team.

### 4. Display name for sender
**What we know:** CONTEXT.md says "Display name configurable per path" and that enterprise sender has a separate address from Graph sender. REQUIREMENTS.md says "Sender configured as Kevin Taylor via impersonatedEmail or permittedEmailImpersonation".
**What's unclear:** Whether the display name "Kevin Taylor" is set via the payload (e.g., `"senderName": "Kevin Taylor"`) or is inherent to the mailbox itself.
**Recommendation:** Add `mmc_sender_name` config field defaulting to `"Kevin Taylor"`. Include it in the payload if the API supports it. If not (API ignores it), the mailbox's display name will be used automatically.

---

## Sources

### Primary (HIGH confidence)
- `app/services/emailer.py` — definitive async httpx email client pattern (GraphEmailService)
- `app/auth/token_manager.py` — Phase 9 TokenManager, `get_token()` interface, 401/403 no-retry decision
- `app/collectors/equity.py` — definitive `_record_event()` isolation pattern, tenacity retry pattern
- `app/collectors/factiva.py` — definitive HTTP client pattern for MMC Core API
- `app/models/api_event.py` — confirms `EMAIL_SENT` and `EMAIL_FALLBACK` already defined
- `app/config.py` — confirms `mmc_api_base_url`, `mmc_api_key`, `is_mmc_auth_configured()` present; `sender_email` is Graph-only
- `app/services/pipeline.py` — Step 8 current implementation, `degraded_auth` flag source, `run_full_pipeline_with_email()` async context confirmed
- `app/schemas/delivery.py` — `EmailRecipients` schema, `DeliveryStatus` enum
- `.planning/REQUIREMENTS.md` — MAIL-01/02/03/04, FALL-02 requirements; `impersonatedEmail` / `permittedEmailImpersonation` field name hints
- `app/.env.example` — existing MMC env var naming conventions

### Secondary (MEDIUM confidence)
- `.planning/phases/09-oauth2-token-management/09-RESEARCH.md` — auth API shape, token endpoint path, retry decisions confirmed
- `.planning/phases/11-equity-price-enrichment/11-RESEARCH.md` — establishes `_record_event()` as the canonical pattern for Phase 12

### Tertiary (LOW confidence)
- Email payload field names (`htmlBody`, `toRecipients`, `impersonatedEmail`) — inferred from naming conventions and REQUIREMENTS.md hint; NOT confirmed from API documentation (PDFs image-based)
- HTTP success status code (200/201/202) — inferred from REST conventions; not confirmed
- `EMAIL_PATH = "/coreapi/email/v1"` — from REQUIREMENTS.md MAIL-01, same format as other Core API paths; should be validated on deployment

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed in requirements.txt and used throughout codebase
- Architecture (client structure, event recording, async/sync): HIGH — direct pattern from existing collectors and emailer.py
- Pipeline integration (where to replace Step 8, degraded_auth decision): HIGH — based on pipeline.py and CONTEXT.md decisions
- Fallback logic (per-role independent, immediate on 401/403): HIGH — confirmed by CONTEXT.md decisions
- Email API request shape (field names, response codes): LOW — PDFs unreadable; field names inferred from requirements and naming conventions only
- Config additions (mmc_sender_email, mmc_sender_name): HIGH — CONTEXT.md explicitly requires new env vars

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (stable codebase; LOW-confidence email API shape items need validation on first test run)
