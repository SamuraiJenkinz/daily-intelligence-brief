---
phase: 11-equity-price-enrichment
plan: 02
subsystem: pipeline
tags: [equity, pipeline, enrichment, sqlalchemy, json, structlog]

# Dependency graph
requires:
  - phase: 11-01
    provides: EquityPriceClient and EquityTicker model built in plan 01
provides:
  - Step 3b equity price enrichment between classification and reporting in both pipeline methods
  - equity_data key in reporter _prepare_articles output for Jinja2 template context
affects:
  - 11-03 (template rendering of equity_data)
  - future reporting phases

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Transient ORM attribute pattern: _equity_data set on SQLAlchemy objects in-memory, never persisted"
    - "Equity data transfer map: id-keyed dict bridges pre-requery and post-requery article lists"
    - "Per-run dedup cache (fetched_prices dict) prevents duplicate API calls for same ticker within a run"
    - "getattr with [] default for backward-compatible optional attribute access in reporter"

key-files:
  created: []
  modified:
    - app/services/pipeline.py
    - app/services/reporter.py

key-decisions:
  - "Step 3b runs on original `articles` list (from Step 2), not re-queried classified_articles — SQLAlchemy re-query would discard transient attributes"
  - "Equity data bridged via id-keyed dict after Step 4 re-query: equity_data_map = {a.id: getattr(a, '_equity_data', []) for a in articles}"
  - "Unconfigured equity client and no ticker mappings both result in _equity_data=[] — never None, never blocking"
  - "run_full_pipeline_with_email() tracks step_3b duration separately; run_full_pipeline() does not (consistent with other steps in each method)"

patterns-established:
  - "Transient enrichment pattern: attach non-DB data to ORM objects as _ prefixed attributes before reporting"
  - "Ticker dedup cache: fetched_prices dict keyed by exchange:ticker avoids redundant API calls per run"

# Metrics
duration: 3min
completed: 2026-02-19
---

# Phase 11 Plan 02: Equity Price Enrichment Integration Summary

**Step 3b equity enrichment wired into both pipeline methods: classified articles enriched with live equity prices via dedup cache before reporting, equity_data passed through reporter to Jinja2 template context**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-19T01:12:33Z
- **Completed:** 2026-02-19T01:15:01Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Step 3b equity enrichment inserted between classification (Step 3) and re-query (Step 4) in both `run_full_pipeline()` and `run_full_pipeline_with_email()`
- Per-run ticker dedup cache (`fetched_prices` dict keyed by `exchange:ticker`) prevents duplicate API calls for articles sharing the same company
- Equity data bridged to re-queried `classified_articles` via `id`-keyed dict after Step 4 re-query (transient attributes don't survive SQLAlchemy re-query)
- Reporter `_prepare_articles` passes `equity_data` through to template context with `getattr` fallback for backward compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Step 3b equity enrichment to pipeline** - `daf9d0f` (feat)
2. **Task 2: Update reporter _prepare_articles to include equity_data** - `71232ce` (feat)

## Files Created/Modified

- `app/services/pipeline.py` - Added `import json`, `EquityPriceClient`, `EquityTicker` imports; Step 3b equity enrichment block in both pipeline methods; equity data transfer loop after Step 4 re-query in both methods
- `app/services/reporter.py` - Added `'equity_data': getattr(article, '_equity_data', [])` to article dict in `_prepare_articles()`

## Decisions Made

- Step 3b runs on the original `articles` list (from Step 2) rather than re-queried `classified_articles` — SQLAlchemy's `db.query()` returns fresh ORM objects that don't carry transient `_equity_data` attributes
- After Step 4 re-queries `classified_articles`, a transfer loop maps `_equity_data` by article `id` from the original list to the re-queried list
- Both unconfigured equity client and empty ticker map result in `_equity_data = []` on all articles — never `None`, so templates can safely iterate
- Duration tracking around Step 3b only added to `run_full_pipeline_with_email()` to match the existing pattern in that method (simpler `run_full_pipeline()` does not track per-step durations)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both edits applied cleanly; import verification passed; pre-existing test failure (`test_collection.py` failing due to `APIFY_TOKEN` not configured in env) is unrelated to these changes and was present before this plan.

## User Setup Required

None - no external service configuration required. Equity API credentials were already covered in 11-01-USER-SETUP if applicable.

## Next Phase Readiness

- Pipeline now enriches articles with equity price data before report generation
- Reporter passes `equity_data` through to Jinja2 templates in all render paths (`generate_role_brief` and `generate_role_emails`)
- Plan 03 can now add template rendering for `equity_data` lists in `role_brief.html` and `email/role_email.html`
- No blockers — equity enrichment is fully isolated; templates will ignore `equity_data` until Plan 03 adds rendering

---
*Phase: 11-equity-price-enrichment*
*Completed: 2026-02-19*
