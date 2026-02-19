---
phase: 13-admin-dashboard-enterprise-status
plan: 01
subsystem: admin-ui
tags: [fastapi, jinja2, bootstrap5, api-health, credentials, .env, dashboard]

# Dependency graph
requires:
  - phase: 09-enterprise-auth
    provides: ApiEvent model and ApiEventType enum with all 9 event types
  - phase: 10-factiva-news
    provides: api_name="news" events in api_events table
  - phase: 11-equity-prices
    provides: api_name="equity" events in api_events table
  - phase: 12-enterprise-email
    provides: api_name="email" events in api_events table
provides:
  - Enterprise API Status panel on dashboard (healthy/degraded/offline/unknown per API)
  - Fallback Event Log on dashboard (last 20 fallback/failure events)
  - Enterprise Config page at /admin/enterprise-config for credential management
  - active_nav='dashboard' bug fix for sidebar highlight
affects:
  - future pipeline monitoring, credential rotation workflows

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Helper functions before routes: _get_enterprise_api_status(), _get_fallback_events(), _update_env_var()"
    - "Secret masking: password inputs always render value='', placeholder shows bullets only when secret is set"
    - "Boolean flags pattern: *_set flags passed to template instead of actual secret values"
    - ".env update helper: _update_env_var() replaces existing line or appends new one"

key-files:
  created:
    - app/templates/admin/enterprise_config.html
  modified:
    - app/routers/admin.py
    - app/templates/admin/dashboard.html
    - app/templates/admin/base.html

key-decisions:
  - "api_names queried: ['auth', 'news', 'equity', 'email'] — exact strings from token_manager.py/factiva.py/equity.py/enterprise_emailer.py"
  - "Status logic: success=True -> healthy; success=False + fallback event_type -> degraded; success=False other -> offline; no events -> unknown"
  - "Degraded defined as: fallback succeeded (NEWS_FALLBACK/EQUITY_FALLBACK/EMAIL_FALLBACK) — service working via fallback"
  - "Secret fields: value attribute always empty, placeholder shows bullets only when *_set boolean flag is True"
  - "Non-secret fields always written to .env; secret fields only written when non-blank value submitted"
  - "_update_env_var() extracted as reusable helper (recipients code keeps its inline version — not refactored)"

patterns-established:
  - "Enterprise status pattern: query api_events per api_name, derive status from success + event_type"
  - "Fallback log pattern: filter by fallback event types, order DESC, limit 20"
  - "Credential form pattern: two grouped cards (MMC Core, Graph), secrets masked, cache cleared on save"

# Metrics
duration: 22min
completed: 2026-02-19
---

# Phase 13 Plan 01: Admin Dashboard Enterprise Status Summary

**Enterprise API health panel and credential config UI: dashboard shows healthy/degraded/offline/unknown for 4 APIs via api_events table, /admin/enterprise-config manages MMC+Graph credentials with masked secrets**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-02-19T07:09:27Z
- **Completed:** 2026-02-19T07:31:00Z
- **Tasks:** 2
- **Files modified:** 4 (3 modified, 1 created)

## Accomplishments

- Enterprise API Status panel added above summary cards on dashboard — shows Auth/News/Equity/Email health at a glance
- Fallback Event Log card added below Recent Pipeline Runs table — shows last 20 fallback/failure events with timestamp, API, event type, reason
- Enterprise Config page at `/admin/enterprise-config` enables credential management without touching .env directly
- Fixed sidebar active nav bug (`active_nav='dashboard'` was missing from dashboard route render call)

## Task Commits

Each task was committed atomically:

1. **Task 1: Enterprise status panel and fallback event log** - `bf9cba3` (feat)
2. **Task 2: Enterprise Config credential management page** - `fb42b96` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/routers/admin.py` - Added _get_enterprise_api_status(), _get_fallback_events(), _update_env_var() helpers; GET/POST /admin/enterprise-config routes; updated get_admin_dashboard() with active_nav fix and enterprise data
- `app/templates/admin/dashboard.html` - Enterprise API Status panel (above summary cards), Fallback Event Log card (below runs table)
- `app/templates/admin/base.html` - Enterprise Config sidebar nav entry between Equity Tickers and Manual Trigger
- `app/templates/admin/enterprise_config.html` - 199-line credential form with MMC Core API and Microsoft Graph sections, masked secret fields

## Decisions Made

- api_names queried: `["auth", "news", "equity", "email"]` — exact strings from token_manager.py/factiva.py/equity.py/enterprise_emailer.py
- Status logic: `success=True` -> healthy; `success=False` + fallback event_type -> degraded; `success=False` other -> offline; no events -> unknown
- "Degraded" means the service worked via fallback (NEWS_FALLBACK/EQUITY_FALLBACK/EMAIL_FALLBACK) — not a hard failure
- Secret fields: `value` attribute always empty string; `placeholder` shows bullet characters only when `*_set` boolean flag is True
- Non-secret fields always written to `.env`; secret fields only written when non-blank value submitted in POST
- `_update_env_var()` extracted as reusable helper for enterprise-config routes; recipients code keeps its inline version (not refactored per plan spec)
- `get_settings.cache_clear()` called after `.env` write so pipeline picks up new values on same process

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all functionality worked as specified. Sidebar active nav test initially appeared to fail (HTTP test) but confirmed working via FastAPI test client — active class was being rendered correctly by Jinja2.

## User Setup Required

None - no external service configuration required for this plan. The Enterprise Config page enables credential management via the dashboard UI rather than requiring manual .env editing.

## Next Phase Readiness

- Phase 13 Plan 01 complete: ADMN-01, ADMN-02, FALL-04 satisfied
- Phase 13 Plan 02 (search results source badges) already complete per git log
- Phase 13 is now complete — both plans executed
- No blockers for deployment

---
*Phase: 13-admin-dashboard-enterprise-status*
*Completed: 2026-02-19*
