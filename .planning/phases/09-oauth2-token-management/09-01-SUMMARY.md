---
phase: 09
plan: 01
subsystem: auth
tags: [oauth2, jwt, token-manager, sqlite, sqlalchemy, httpx, tenacity, structlog]

dependency-graph:
  requires:
    - app/database.py (SQLAlchemy Base, engine, SessionLocal)
    - app/config.py (Settings/get_settings pattern)
    - app/services/emailer.py (httpx + tenacity + structlog patterns)
    - app/models/run.py (ORM model pattern)
  provides:
    - JWT token acquisition via client_credentials grant
    - In-memory token cache with proactive 5-minute refresh margin
    - ApiEvent ORM model for all enterprise API event tracking
    - MMC API configuration fields + validation helpers in Settings
    - scripts/test_auth.py standalone auth validation tool
  affects:
    - Phase 10 (Factiva news) - will write NEWS_FETCH/NEWS_FALLBACK events to api_events
    - Phase 11 (Equity data) - will write EQUITY_FETCH/EQUITY_FALLBACK events to api_events
    - Phase 12 (Enterprise email) - imports TokenManager.get_token() for Bearer auth
    - Phase 13 (Admin dashboard) - reads api_events table for API health display

tech-stack:
  added:
    - httpx (already in project, now used for OAuth2 token endpoint)
    - tenacity (already in project, retry decorator pattern extended)
  patterns:
    - client_credentials OAuth2 grant (no user interaction, server-side daemon)
    - In-memory token caching with TTL-based expiry
    - Event sourcing for API health observability (api_events table)
    - Graceful degradation: is_configured() guard before any network call

key-files:
  created:
    - app/auth/__init__.py
    - app/auth/token_manager.py
    - app/models/api_event.py
    - scripts/test_auth.py
  modified:
    - app/config.py (5 new MMC fields + 2 validation methods)
    - app/models/__init__.py (ApiEvent, ApiEventType exported)
    - app/main.py (test-auth CLI branch added)
    - .env.example (MMC Core API section documented)

decisions:
  - key: token-refresh-margin
    choice: "5-minute proactive refresh margin (REFRESH_MARGIN_SECONDS=300)"
    rationale: "Access Management tokens expire in 1h; 5min margin ensures zero mid-request expiry"
  - key: no-retry-on-auth-errors
    choice: "401/403 responses return None immediately without retry"
    rationale: "Invalid credentials won't resolve via retry; avoids account lockout"
  - key: api-events-future-types
    choice: "ApiEventType includes all 9 event types upfront (NEWS, EQUITY, EMAIL events)"
    rationale: "Schema stability — adding enum values later would require Alembic migration"
  - key: event-recording-isolation
    choice: "_record_event() opens its own DB session, failures are swallowed"
    rationale: "Event recording must never crash the token acquisition flow"
  - key: token-redaction-in-test
    choice: "test_auth.py shows first 8 + last 4 chars of token only"
    rationale: "Confirms token was received while keeping secret out of terminal history"

metrics:
  duration: "~20 minutes"
  completed: "2026-02-18"
  tasks: 3/3
  commits: 3
---

# Phase 9 Plan 01: OAuth2 Token Management — Foundation Summary

**One-liner:** JWT client_credentials token manager with 5-min refresh margin, api_events table for full enterprise API observability, and standalone test CLI.

## What Was Built

### app/auth/token_manager.py (331 lines)
The central auth module for all enterprise API access:
- `TokenManager.get_token()` — returns cached JWT or acquires fresh one transparently
- `TokenManager.force_refresh()` — invalidates cache and re-acquires (used by test script)
- Retry policy: 3 attempts with exponential backoff for 429/5xx/network errors; no retry for 401/403
- `_record_event()` writes to api_events table with its own DB session lifecycle
- Security contract enforced: client_id, client_secret, and token values never appear in logs

### app/models/api_event.py
`ApiEvent` ORM model with `ApiEventType` enum covering all 9 event types across all 4 enterprise APIs:
- Auth: TOKEN_ACQUIRED, TOKEN_REFRESHED, TOKEN_FAILED
- News (Phase 10): NEWS_FETCH, NEWS_FALLBACK
- Equity (Phase 11): EQUITY_FETCH, EQUITY_FALLBACK
- Email (Phase 12): EMAIL_SENT, EMAIL_FALLBACK

### app/config.py additions
5 new MMC API fields: `mmc_api_base_url`, `mmc_api_client_id`, `mmc_api_client_secret`, `mmc_api_key`, `mmc_api_token_path`.
2 new validation methods: `is_mmc_auth_configured()` (for JWT/email), `is_mmc_api_key_configured()` (for news/equity).

### scripts/test_auth.py
4-step standalone test suite:
1. Config validation (exits 2 with clear missing-var list if not configured)
2. Token acquisition (shows token_type, expiry, redacted token preview)
3. Cache validation (confirms second call is sub-100ms)
4. Force refresh (confirms re-acquisition works)

### .env.example
Documented MMC Core API section between Azure Blob Storage and Email Recipients sections. Includes staging/production host names and per-var instructions.

## Commits

| Hash | Description |
|------|-------------|
| `a74ba86` | feat(09-01): add MMC Core API config, ApiEvent model, and auth package scaffold |
| `a08c61b` | feat(09-01): implement TokenManager with acquire, cache, refresh, and event recording |
| `ec7f92e` | feat(09-01): create standalone auth test command and main.py test-auth CLI |

## Verification Results

| Check | Result |
|-------|--------|
| `is_mmc_auth_configured()` returns False (no creds) | PASSED |
| `is_mmc_api_key_configured()` returns False (no creds) | PASSED |
| `len(ApiEventType)` == 9 | PASSED |
| `TokenManager().is_configured()` == False | PASSED |
| `TokenManager().is_token_valid` == False | PASSED |
| `python scripts/test_auth.py` exits 2 (config missing) | PASSED |
| `Base.metadata.create_all()` creates api_events table | PASSED |
| No secret values in logger calls | PASSED |

## Deviations from Plan

None — plan executed exactly as written. The `app/auth/__init__.py` forward-references `token_manager.py` which is created in Task 2; this was expected per the plan and both tasks were committed in order.

## Next Phase Readiness

Phase 10 (Factiva News Integration) can begin immediately:
- `get_settings().mmc_api_base_url` and `mmc_api_key` are available for X-Api-Key auth
- `ApiEventType.NEWS_FETCH` and `NEWS_FALLBACK` are ready to use
- `ApiEvent._record_event()` pattern is established — Phase 10 will replicate it

Phase 12 (Enterprise Email):
- `TokenManager.get_token()` is the single import needed for Bearer token auth
- Import: `from app.auth import TokenManager`
