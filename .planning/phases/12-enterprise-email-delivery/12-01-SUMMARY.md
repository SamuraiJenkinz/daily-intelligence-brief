---
phase: 12-enterprise-email-delivery
plan: 01
subsystem: api
tags: [httpx, tenacity, structlog, enterprise-email, mmc-api, jwt, pydantic-settings]

# Dependency graph
requires:
  - phase: 09-enterprise-auth
    provides: MMCAuthManager for JWT token acquisition, ApiEvent/ApiEventType models
  - phase: 11-equity-price-enrichment
    provides: EquityPriceClient pattern (httpx + tenacity + structlog + _record_event)
provides:
  - EnterpriseEmailClient with send_email(), is_configured(), _build_headers(), _build_payload(), _record_event()
  - Settings.mmc_sender_email, mmc_sender_name, mmc_email_path fields
  - Settings.is_mmc_email_configured() method
  - .env.example MMC_SENDER_EMAIL, MMC_SENDER_NAME, MMC_EMAIL_PATH documentation
affects:
  - 12-02 (pipeline wiring — imports EnterpriseEmailClient, calls send_email())
  - 13-admin-dashboard (EMAIL_SENT/EMAIL_FALLBACK ApiEvents in dashboard display)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Async httpx.AsyncClient for enterprise email (vs sync for equity/factiva)"
    - "Class-level FIELD_* constants for payload field names (correctable without refactoring)"
    - "JWT token passed per-call (not stored on self) for rotation safety"
    - "Immediate auth_error return on 401/403 — no retry to prevent account lockout"

key-files:
  created:
    - app/services/enterprise_emailer.py
  modified:
    - app/config.py
    - .env.example

key-decisions:
  - "async httpx.AsyncClient (not sync) — pipeline run_full_pipeline_with_email() is async"
  - "Payload field names as class constants (FIELD_SUBJECT, FIELD_HTML_BODY, etc.) — INFERRED, validate on deployment machine"
  - "FIELD_SENDER = 'impersonatedEmail' — standard corporate API impersonation field convention"
  - "401/403 return auth_error immediately with no retry — same policy as MMCAuthManager (Phase 9)"
  - "mmc_sender_email = '' default (not a real address) — is_mmc_email_configured() returns False without config"
  - "mmc_sender_name = 'Kevin Taylor' default — display name pre-filled for likely config"
  - "mmc_email_path = '/coreapi/email/v1' default — inferred, validate on deployment machine"

patterns-established:
  - "EnterpriseEmailClient mirrors EquityPriceClient exactly: __init__, is_configured, _record_event"
  - "send_email() is async (unlike get_price() which is sync) — matches pipeline async context"
  - "Never raises from send_email() — always returns dict with 'status' key"
  - "Email content never logged — only html_body_length logged at INFO level"
  - "JWT token never stored on self, never logged — passed per-call only"

# Metrics
duration: 5min
completed: 2026-02-19
---

# Phase 12 Plan 01: Enterprise Email Client Summary

**Async EnterpriseEmailClient for MMC Core API email with JWT+API-Key auth, tenacity retry, and EMAIL_SENT/EMAIL_FALLBACK event recording**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T02:12:27Z
- **Completed:** 2026-02-19T02:17:06Z
- **Tasks:** 2/2
- **Files modified:** 3 (config.py, .env.example, enterprise_emailer.py created)

## Accomplishments

- Created EnterpriseEmailClient with full send/retry/record pattern following EquityPriceClient structure
- Added mmc_sender_email, mmc_sender_name, mmc_email_path Settings fields with correct defaults
- Added is_mmc_email_configured() requiring JWT auth + API key + sender email (all three)
- Documented MMC_SENDER_EMAIL, MMC_SENDER_NAME, MMC_EMAIL_PATH in .env.example
- Payload field names as correctable class constants (FIELD_SUBJECT, FIELD_HTML_BODY, FIELD_TO_RECIPIENTS, FIELD_CC_RECIPIENTS, FIELD_SENDER, FIELD_SENDER_NAME)

## Task Commits

1. **Task 1: Enterprise email config fields and is_mmc_email_configured()** - `ea6970d` (feat)
2. **Task 2: EnterpriseEmailClient module** - `60da758` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/services/enterprise_emailer.py` - EnterpriseEmailClient: async send_email(), is_configured(), _build_headers(), _build_payload(), _post_email(), _record_event()
- `app/config.py` - Added mmc_sender_email, mmc_sender_name, mmc_email_path fields + is_mmc_email_configured()
- `.env.example` - Added MMC_SENDER_EMAIL, MMC_SENDER_NAME, MMC_EMAIL_PATH section

## Decisions Made

- **async httpx.AsyncClient (not sync):** Pipeline run_full_pipeline_with_email() is async; sync httpx.Client would block the event loop. This is the key divergence from EquityPriceClient which is sync.
- **Payload field names as class constants:** FIELD_SUBJECT, FIELD_HTML_BODY, FIELD_TO_RECIPIENTS, FIELD_CC_RECIPIENTS, FIELD_SENDER, FIELD_SENDER_NAME are all INFERRED from corporate API conventions. Defined as FIELD_* class constants so they can be corrected in one place without refactoring send_email() callers.
- **FIELD_SENDER = "impersonatedEmail":** Standard field name for sender impersonation in corporate email API proxies. Validate against real /coreapi/email/v1 on deployment machine.
- **401/403 return auth_error immediately with no retry:** Consistent with Phase 9 decision — invalid credentials won't resolve via retry and may trigger account lockout. Callers (pipeline) see "auth_error" and fall back to Graph API immediately.
- **mmc_sender_name = "Kevin Taylor" default:** Pre-filled for likely real-world configuration while keeping mmc_sender_email = "" (is_mmc_email_configured() returns False without explicit email config).
- **mmc_email_path = "/coreapi/email/v1" default:** Inferred path, validate on deployment machine — same pattern as mmc_api_token_path.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required at this stage. Credentials are configured via .env.

Deployment validation needed:
- Validate FIELD_SENDER ("impersonatedEmail") against real /coreapi/email/v1 API documentation
- Validate FIELD_HTML_BODY ("htmlBody"), FIELD_TO_RECIPIENTS ("toRecipients") field names
- Validate mmc_email_path "/coreapi/email/v1" against actual email endpoint
- Set MMC_SENDER_EMAIL to the enterprise mailbox to send from

## Next Phase Readiness

- EnterpriseEmailClient ready for Plan 02 pipeline wiring
- Plan 02 imports EnterpriseEmailClient and calls send_email() in the pipeline delivery step
- Client is self-contained and testable independently of pipeline
- Blocker: Payload field names (FIELD_*) are inferred — validate on deployment machine before sending real emails

---
*Phase: 12-enterprise-email-delivery*
*Completed: 2026-02-19*
