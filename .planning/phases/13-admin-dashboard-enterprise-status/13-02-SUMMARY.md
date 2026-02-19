---
phase: 13-admin-dashboard-enterprise-status
plan: 02
subsystem: ui
tags: [jinja2, bootstrap, htmx, badges, search-results, collector_source]

# Dependency graph
requires:
  - phase: 10-factiva-integration
    provides: collector_source field on NewsArticle model (String, nullable, default Apify/RSS)
  - phase: 13-admin-dashboard-enterprise-status-01
    provides: dashboard runs table with Factiva/Apify source_breakdown badges (style reference)
provides:
  - Per-article collector_source badge inline in search results article cards
  - Factiva blue (#0077c8) badge and Apify/RSS grey (bg-secondary) badge visible without additional clicks
  - ADMN-03 requirement fulfilled
affects:
  - Future admin UI work touching search_results.html

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Jinja2 elif chain for nullable collector_source field (None = no badge, falsy check)
    - Badge color parity between dashboard runs table and search results (same Factiva blue #0077c8)

key-files:
  created: []
  modified:
    - app/templates/admin/partials/search_results.html

key-decisions:
  - "No badge shown for articles with collector_source=None — elif check makes None falsy, handles pre-Phase-10 articles"
  - "Badge placed after source_name, before priority — follows visual hierarchy: source context then importance"
  - "Font-size: 0.7rem keeps badge subordinate to article title"

patterns-established:
  - "collector_source badge pattern: Factiva=blue #0077c8 with bi-newspaper icon, Apify/RSS=grey bg-secondary with bi-rss icon"

# Metrics
duration: 3min
completed: 2026-02-19
---

# Phase 13 Plan 02: Admin Dashboard Enterprise Status - Search Results Source Badges Summary

**Per-article Factiva/Apify source attribution badges added inline to search results, completing ADMN-03 with zero-click visibility matching the dashboard runs table badge style**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-19T09:49:32Z
- **Completed:** 2026-02-19T09:52:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added Factiva (blue #0077c8, bi-newspaper icon) badge per article in search results
- Added Apify/RSS (grey bg-secondary, bi-rss icon) badge for non-Factiva articles
- No badge rendered for pre-Phase-10 articles where collector_source is None
- Badge placement and color exactly match the existing dashboard runs table source badges

## Task Commits

Each task was committed atomically:

1. **Task 1: Add collector_source badge to search results article cards** - `99b383d` (feat)

**Plan metadata:** (to follow in docs commit)

## Files Created/Modified
- `app/templates/admin/partials/search_results.html` - Added 9-line Jinja2 block rendering Factiva/Apify badge inline after source_name span

## Decisions Made
- No badge shown for `collector_source=None` — the `{% elif article.collector_source %}` check treats None as falsy, backward-compatible for all pre-Phase-10 articles without migration
- Badge inserted after source_name and before priority badge — preserves existing metadata row visual order (date, source, collector, priority)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- ADMN-03 complete: per-article source attribution visible in search results without additional clicks
- Remaining Phase 13 plans can proceed: status indicators, export, and any remaining dashboard requirements
- The collector_source badge pattern (Factiva blue / grey secondary) is now established across both dashboard and search views

---
*Phase: 13-admin-dashboard-enterprise-status*
*Completed: 2026-02-19*
