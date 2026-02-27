---
phase: 16-dashboard-config-updates
plan: 03
subsystem: admin-ui
tags: [pydantic, fastapi, jinja2, forms, configuration]

# Dependency graph
requires:
  - phase: 16-01
    provides: "Simplified dashboard status logic (binary healthy/offline)"
  - phase: 16-02
    provides: "Simplified source management UI (removed type/actor_id fields)"
provides:
  - "Simplified source schemas (SourceCreate/SourceUpdate without source_type or actor_id)"
  - "Enhanced FactivaConfig page with sole-source messaging and date_range_hours field"
affects: [none - final plan in phase]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Pydantic schema simplification aligned with UI changes"]

key-files:
  created: []
  modified:
    - app/schemas/admin.py
    - app/routers/admin.py
    - app/templates/admin/factiva.html

key-decisions:
  - "rss-default-type: Use SourceType.RSS as default for new sources (DB NOT NULL constraint, RSS is safe non-Apify option)"
  - "preserve-existing-values: Preserve existing source_type and actor_id values on update (don't overwrite DB data)"
  - "honest-disable-warning: Replace misleading 'fallback to Apify/RSS' hint with honest 'stops all collection' warning"

patterns-established:
  - "Backend schema alignment: When UI simplifies, backend schemas and routes follow to maintain consistency"
  - "Honest admin messaging: Configuration pages clearly communicate system behavior without marketing language"

# Metrics
duration: 15min
completed: 2026-02-27
---

# Phase 16 Plan 03: Backend Schema & Config Page Alignment Summary

**Source schemas simplified to name/url/enabled only, FactivaConfig page enhanced with sole-source header, clear disable warning, and date_range_hours field**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-27T[execution_start]
- **Completed:** 2026-02-27T[execution_end]
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Source CRUD operations work without source_type or actor_id (aligned with 16-02 UI simplification)
- FactivaConfig page clearly identifies itself as the sole collection source with helpful header note
- Misleading "fallback to Apify/RSS" hint replaced with honest "stops all collection" warning
- date_range_hours field added with helpful documentation and 1-168 hour validation

## Task Commits

Each task was committed atomically:

1. **Task 1: Update source schemas and route handlers for simplified source model** - `49ac77a` (refactor)
2. **Task 2: Enhance FactivaConfig page with sole-source messaging and date_range_hours field** - `64fc79a` (feat)

## Files Created/Modified
- `app/schemas/admin.py` - Removed source_type, actor_id fields and validators from SourceCreate and SourceUpdate
- `app/routers/admin.py` - Updated create_source/update_source routes to work without type/actor_id, added date_range_hours to Factiva config
- `app/templates/admin/factiva.html` - Added sole-source header, date_range_hours field, replaced misleading fallback hint with clear warning

## Decisions Made

**rss-default-type**: Use SourceType.RSS as default for new sources
- **Context:** DB source_type column is NOT NULL, requires a value even though UI doesn't collect it
- **Rationale:** RSS is the safe non-Apify option, preserves DB compatibility without breaking existing rows
- **Alternative considered:** Create migration to make column nullable (rejected - too invasive for phase 16 cosmetic cleanup)

**preserve-existing-values**: Preserve existing source_type and actor_id on update
- **Context:** Update route no longer receives these fields from UI
- **Rationale:** Prevents overwriting existing DB data, maintains historical accuracy for existing sources
- **Implementation:** Remove field assignments from update_source route handler

**honest-disable-warning**: Replace misleading "fallback to Apify/RSS" hint with clear warning
- **Context:** FactivaConfig page suggested fallback exists when it doesn't (Phase 15 removed Apify/RSS collectors)
- **Rationale:** Admins deserve honest information about system behavior to make informed decisions
- **Impact:** Clear text-danger warning with icon: "Disabling Factiva will stop all news collection. No fallback source is available."

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Phase 16 complete** - All dashboard and config updates finished:
- 16-01: Status logic simplified to binary healthy/offline (no NEWS_FALLBACK events)
- 16-02: Template badges and source UI simplified (no Apify/RSS concepts)
- 16-03: Backend schemas and config page aligned with UI changes

**System state after phase:**
- Dashboard shows accurate Factiva-only status
- Source management works with minimal fields (name, url, enabled)
- FactivaConfig page clearly communicates sole-source role
- Zero Apify/RSS references in admin UI (code artifacts preserved per 15-03 decision)

**Ready for production:** Dashboard and configuration UI accurately reflect v1.2 Factiva-only collection architecture.

---
*Phase: 16-dashboard-config-updates*
*Completed: 2026-02-27*
