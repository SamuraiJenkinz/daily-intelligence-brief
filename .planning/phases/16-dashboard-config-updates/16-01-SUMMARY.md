---
phase: 16-dashboard-config-updates
plan: 01
subsystem: ui
tags: [dashboard, monitoring, health-status, config, factiva]

# Dependency graph
requires:
  - phase: 15-pipeline-simplification-cleanup
    provides: FactivaCollector as sole news collection source
provides:
  - News API health status (binary: healthy/offline, no degraded state)
  - Fallback event log excludes NEWS_FALLBACK events
  - Dashboard run breakdown shows Factiva-only badge
  - NewsArticle model and migration default to 'Factiva'
  - .env.example documents Factiva-only architecture
affects: [future-dashboard-development, health-monitoring, deployment-documentation]

# Tech tracking
tech-stack:
  added: []
  patterns: [binary-health-status-for-news-api, factiva-sole-source-architecture]

key-files:
  created: []
  modified:
    - app/routers/admin.py
    - app/models/news_article.py
    - app/main.py
    - .env.example
    - app/templates/admin/dashboard.html

key-decisions:
  - "binary-news-status: News API shows healthy/offline only (no degraded state since no fallback exists)"
  - "exclude-news-fallback-events: Fallback event log excludes NEWS_FALLBACK to avoid querying non-existent events"
  - "factiva-default: New articles default to 'Factiva' collector_source in both model and migration SQL"

patterns-established:
  - "health-status-pattern: API status calculation uses FALLBACK_TYPES set to determine degraded vs offline state"
  - "factiva-badge-rendering: Dashboard uses newspaper icon for Factiva badges (consistency with app-wide Factiva representation)"

# Metrics
duration: 12min
completed: 2026-02-27
---

# Phase 16 Plan 01: Dashboard Config Updates Summary

**News API health status simplified to binary healthy/offline, fallback events exclude NEWS_FALLBACK, dashboard shows Factiva-only badge, and model/migration defaults updated to 'Factiva'**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-27T09:30:00Z
- **Completed:** 2026-02-27T09:42:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Removed NEWS_FALLBACK from status calculation (news API now binary: healthy/offline)
- Removed NEWS_FALLBACK from fallback event log query
- Simplified dashboard run source breakdown to Factiva-only rendering with newspaper icon
- Updated NewsArticle model default from 'Apify/RSS' to 'Factiva'
- Updated migration SQL default from 'Apify/RSS' to 'Factiva'
- Documented Factiva-only architecture in .env.example

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove NEWS_FALLBACK from status logic and update model defaults** - `f3c7823` (feat)
2. **Task 2: Simplify dashboard run source breakdown to Factiva-only** - `b5337dc` (feat)

## Files Created/Modified
- `app/routers/admin.py` - Removed NEWS_FALLBACK from FALLBACK_TYPES and FALLBACK_EVENT_TYPES
- `app/models/news_article.py` - Changed collector_source default to 'Factiva'
- `app/main.py` - Updated migration SQL default to 'Factiva'
- `.env.example` - Documented Factiva as sole collection source
- `app/templates/admin/dashboard.html` - Simplified run source breakdown to Factiva-only badge with newspaper icon

## Decisions Made

**binary-news-status**: News API health status now shows only healthy or offline (no degraded state). This is correct because no news fallback mechanism exists - if Factiva fails, the system is offline for news collection.

**exclude-news-fallback-events**: Removed NEWS_FALLBACK from FALLBACK_EVENT_TYPES to prevent querying for events that should not exist in the new architecture.

**factiva-default**: Changed NewsArticle.collector_source default from 'Apify/RSS' to 'Factiva' in both the model definition and the startup migration SQL. This ensures new articles default to the correct source.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Dashboard and configuration files fully reflect Factiva-only architecture
- News API health monitoring simplified to binary healthy/offline
- Fallback event log correctly excludes NEWS_FALLBACK events
- Model and migration defaults ensure new articles are attributed to Factiva
- Phase 16 complete - v1.2 milestone ready for final verification

---
*Phase: 16-dashboard-config-updates*
*Completed: 2026-02-27*
