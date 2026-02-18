---
phase: 10-factiva-news-collection
plan: "03"
subsystem: ui
tags: [fastapi, jinja2, admin, factiva, crud, html-forms]

# Dependency graph
requires:
  - phase: 10-01
    provides: FactivaCollector, FactivaConfig DB model, startup migration seeding row id=1
  - phase: 10-02
    provides: Factiva-primary pipeline with fallback; enabled flag read at runtime
provides:
  - GET /admin/factiva — Factiva config view page with current DB values
  - POST /admin/factiva — Save updated query parameters to factiva_config table
  - Sidebar navigation link to Factiva Config in admin/base.html
  - Industry code reference table for admin guidance
affects:
  - Phase 11 (email delivery) — no direct dependency, but admin config pattern established
  - Future staging validation run — industry codes deferred for on-machine credential access

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hidden input + checkbox pattern for boolean form fields (prevents missing key on uncheck)"
    - "Admin CRUD page pattern: GET renders form from DB row, POST validates + updates + re-renders"
    - "Page_size whitelist validation in route (10/25/50/100 only)"
    - "Comma-separated code cleanup: split + strip + rejoin in route before DB write"

key-files:
  created:
    - app/templates/admin/factiva.html
  modified:
    - app/routers/admin.py
    - app/templates/admin/base.html

key-decisions:
  - "Staging Factiva API validation deferred — no credentials on dev machine; will validate on deployment machine with MMC_API_BASE_URL and MMC_API_KEY set"
  - "Hidden input trick for checkbox boolean: <input type='hidden' name='enabled' value='false'> before checkbox so form always sends a value"
  - "page_size validated against whitelist (10/25/50/100) — any other value coerced to 25"
  - "Industry code reference table included inline in admin page — docs-as-UI pattern for operator guidance without leaving the dashboard"

patterns-established:
  - "Admin form pages extend admin/base.html with success/error flash message blocks"
  - "Routes seed missing DB row on GET (defensive — startup migration should have created it)"
  - "structlog logger.info() on successful config update for audit trail"

# Metrics
duration: 45min
completed: 2026-02-18
---

# Phase 10 Plan 03: Factiva Admin Config UI Summary

**Factiva admin config page at /admin/factiva: CRUD form for industry codes, company codes, keywords, page size, and enable toggle persisted to factiva_config DB table — staging validation deferred to deployment machine.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-02-18
- **Completed:** 2026-02-18
- **Tasks:** 1 completed, 1 checkpoint resolved (deferred)
- **Files modified:** 3

## Accomplishments

- Admin can view and edit all Factiva query parameters (industry codes, company codes, keywords, page size, enabled) at /admin/factiva
- Form saves to factiva_config DB table; changes take effect on next pipeline run
- Enable/disable toggle persists correctly via hidden-input-before-checkbox pattern
- Industry code reference table embedded in admin page for operator guidance (i82, i832, i83, i8311, i8312 with status notes)
- Factiva Config navigation link added to admin sidebar
- Staging API validation deferred — industry codes will be confirmed on the deployment machine once credentials are available

## Task Commits

Each task committed atomically:

1. **Task 1: Factiva config CRUD routes and admin template** — `7874e62` (feat)

**Plan metadata:** (to be recorded after this commit)

## Files Created/Modified

- `app/routers/admin.py` — Added GET /admin/factiva (read FactivaConfig row, render form) and POST /admin/factiva (validate, clean, save to DB, flash success/error)
- `app/templates/admin/factiva.html` — Config form with industry codes, company codes, keywords, page size select, enable checkbox, inline industry code reference table
- `app/templates/admin/base.html` — Added "Factiva Config" link in sidebar navigation

## Decisions Made

- **Staging validation deferred.** No MMC_API credentials on dev machine. The checkpoint (Task 2) was resolved with user response "deferred" — admin UI was confirmed working, staging call to /coreapi/recent-news/v1/industries skipped. Will be run on deployment machine.
- **Hidden input + checkbox pattern.** HTML checkboxes only submit when checked, causing FastAPI `bool = Form(False)` to behave unexpectedly. Added `<input type="hidden" name="enabled" value="false">` before the checkbox so the form always sends an "enabled" key; when checkbox is checked, both false and true are submitted and FastAPI's last-value-wins behavior correctly reads true.
- **page_size whitelist validation in POST route.** Values outside 10/25/50/100 are coerced to 25. Prevents arbitrary large page sizes from being injected via form manipulation.
- **Comma-separated code cleanup.** Industry codes and company codes are split on comma, stripped of whitespace, and rejoined before DB write. Prevents leading/trailing spaces accumulating in stored values.

## Deviations from Plan

None — plan executed exactly as written. The checkbox boolean handling note in the task action was addressed as documented (hidden field approach).

## Issues Encountered

None.

## User Setup Required

None — no new external service configuration added in this plan. Factiva credentials (MMC_API_BASE_URL, MMC_API_KEY) were already covered in Phase 10 plan 01 setup.

**Staging validation (deferred):** When credentials are available on the deployment machine:
1. Set `MMC_API_BASE_URL` and `MMC_API_KEY` in `.env`
2. Run: `python -c "from app.collectors.factiva import FactivaCollector; import httpx; fc = FactivaCollector(); r = httpx.get(f'{fc.base_url}/coreapi/recent-news/v1/industries', headers=fc._build_headers(), timeout=30); print(r.status_code, r.json())"`
3. Confirm which industry codes (i82, i832, i83, i8311, i8312, i831) are valid
4. Update /admin/factiva config to use only confirmed codes

## Next Phase Readiness

- Phase 10 (Factiva News Collection) is **complete** — all 3 plans delivered:
  - 10-01: FactivaCollector + FactivaConfig DB model
  - 10-02: Factiva-primary pipeline with Apify/RSS fallback + source attribution
  - 10-03: Admin config UI for runtime query parameter management
- Staging industry code validation is deferred (non-blocking for Phase 11)
- Concern: Industry codes i83, i8311, i8312, i831 are inferred — validate before production to avoid empty result sets

---
*Phase: 10-factiva-news-collection*
*Completed: 2026-02-18*
