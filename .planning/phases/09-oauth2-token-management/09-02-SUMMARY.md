---
phase: 09-oauth2-token-management
plan: "02"
subsystem: auth
tags: [oauth2, jwt, pipeline, degraded-auth, health-check, token-manager]

# Dependency graph
requires:
  - phase: 09-01
    provides: TokenManager with get_token()/force_refresh(), ApiEvent model, is_mmc_auth_configured()
provides:
  - PipelineOrchestrator wired with TokenManager via optional constructor parameter
  - Step 0 auth in both pipeline variants (with and without email)
  - degraded_auth flag in pipeline result dict (consumed by Phase 12 for email routing)
  - Health endpoint reporting mmc_auth and mmc_api_key configuration status
  - api_events table auto-created on app startup
  - CLI run-pipeline mode creates TokenManager and logs auth status
affects: [12-enterprise-email, 13-admin-dashboard, pipeline-routing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Step 0 auth pattern: acquire JWT before pipeline steps, degrade gracefully on failure"
    - "degraded_auth flag: pipeline result key consumed by Phase 12 to choose email delivery method"
    - "Optional dependency injection: token_manager=None default preserves backward compatibility"

key-files:
  created: []
  modified:
    - app/services/pipeline.py
    - app/main.py

key-decisions:
  - "degraded_auth defaults to True (safe default: Graph API fallback always available)"
  - "run_full_pipeline (sync) uses asyncio.run for token acquisition; run_full_pipeline_with_email (async) uses await directly"
  - "MMC auth/key missing in health check returns status=info not warning — these are optional enterprise features"
  - "Step 0 uses step_0_auth prefix to avoid renumbering existing steps 1-9"

patterns-established:
  - "Auth-aware pipeline: Step 0 runs before collection so degraded_auth is known for all subsequent steps"
  - "Health check info vs warning: use info for optional enterprise features with graceful fallback"

# Metrics
duration: 12min
completed: 2026-02-18
---

# Phase 9 Plan 02: Pipeline Auth Integration Summary

**TokenManager wired into PipelineOrchestrator with degraded-auth propagation; health check reports MMC OAuth2 status; api_events table auto-created on startup**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-18T16:15:00Z
- **Completed:** 2026-02-18T16:27:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- PipelineOrchestrator accepts optional `token_manager` parameter (backward compatible — existing callers unaffected)
- Step 0 auth block added to both `run_full_pipeline` and `run_full_pipeline_with_email` before collection step
- `degraded_auth` flag stored in pipeline result dict and included in `pipeline_summary` log event; defaults to `True` (safe: Graph API fallback)
- Auth failure never blocks pipeline — logs warning and continues
- Health endpoint now reports `mmc_auth` and `mmc_api_key` with `status: info` (optional features, not degraded)
- `api_event` model imported in app lifespan so `api_events` table is created automatically on startup
- CLI `run-pipeline` mode creates `TokenManager`, logs auth configuration, and passes it to `PipelineOrchestrator`

## Task Commits

Each task was committed atomically:

1. **Task 1: Integrate TokenManager into pipeline with degraded-auth flag** - `de65389` (feat)
2. **Task 2: Update CLI startup and health check with MMC auth status** - `f757e7e` (feat)

**Plan metadata:** _(pending — see final commit below)_

## Files Created/Modified

- `app/services/pipeline.py` — Added `from app.auth.token_manager import TokenManager` import; updated `__init__` with `token_manager: Optional[TokenManager] = None`; added Step 0 auth in both pipeline methods; `degraded_auth` stored in result dict and logged in pipeline_summary
- `app/main.py` — Added `api_event` model import in lifespan; added MMC TokenManager creation and auth status logging in CLI mode; added `degraded_auth` to CLI completion log; added `mmc_auth` and `mmc_api_key` blocks to health check endpoint

## Decisions Made

- `degraded_auth` defaults to `True` — safe default ensures Graph API fallback is always used when JWT is unavailable, preventing email delivery failure
- `run_full_pipeline` is synchronous but `get_token()` is async. Used `asyncio.run()` for token acquisition in the sync method (compatible with CLI/scheduler context where no event loop is running)
- MMC auth/API key missing from health check returns `status: "info"` not `"warning"` — these are optional enterprise features with graceful fallback, not required for core operation
- Step 0 naming (`step_0_auth_*` log keys) avoids renumbering existing steps 1-9

## Deviations from Plan

None — plan executed exactly as written. One minor note: the plan pseudocode used `self.token_manager.is_configured` (no parentheses) but `is_configured` is a method (not a property) in TokenManager. Used `is_configured()` with parentheses as defined in Plan 01.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required for this plan. MMC credentials are optional and handled gracefully when absent.

## Next Phase Readiness

- Phase 9 complete — both plans (auth foundation + pipeline integration) are done
- Phase 12 (enterprise email) can now check `result["degraded_auth"]` from pipeline to choose between enterprise email client and Graph API fallback
- Phase 13 (admin dashboard) can read `api_events` table for real-time auth health status
- Staging credentials still needed to exercise the actual JWT acquisition path; `scripts/test_auth.py` from Plan 01 provides the verification tool

---
*Phase: 09-oauth2-token-management*
*Completed: 2026-02-18*
