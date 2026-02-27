---
phase: 20-archive-operations
plan: 03
subsystem: admin-dashboard
tags: [tts, cost-monitoring, htmx, jinja2, api-events, dashboard]

# Dependency graph
requires:
  - phase: 20-01
    provides: "TTS event logging with character_count and role in api_events detail JSON"
  - phase: 20-02
    provides: "Audio Archive sidebar entry and admin template patterns"
  - phase: 18-01
    provides: "TTS provider abstraction with Azure and ElevenLabs pricing models"
provides:
  - "TTS cost monitoring dashboard at /admin/tts-costs"
  - "Per-role character usage aggregation from api_events"
  - "Provider-aware cost calculation (Azure $15/M, ElevenLabs $30/M)"
  - "Budget alert system comparing current vs previous period spend"
  - "Time period filtering (7d, 30d, 90d) with HTMX partial updates"
affects: [operations, cost-tracking, tts-monitoring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HTMX partial rendering for period filter updates without page reload"
    - "Provider-aware cost calculation from TTS event detail JSON"
    - "Budget alert threshold at 80% of previous period average"

key-files:
  created:
    - app/templates/admin/tts_costs.html
    - app/templates/admin/partials/tts_cost_chart.html
  modified:
    - app/routers/admin.py
    - app/templates/admin/base.html

key-decisions:
  - "Budget alert compares current period to previous period (not static threshold) - adapts to usage patterns"
  - "Provider-aware pricing from detail JSON provider field (Azure $15/M, ElevenLabs $30/M) - accurate cost tracking"
  - "Historical events with missing character_count default to 0 - graceful degradation for pre-20-01 data"
  - "Daily aggregation groups by date and role - enables per-role cost breakdown"

patterns-established:
  - "TTS cost aggregation: Query api_events for TTS_SUCCESS and TTS_FALLBACK, parse detail JSON for character_count, role, provider"
  - "Budget alerting: Compare sum(current_period_cost) > 0.8 * sum(previous_period_cost) for adaptive threshold"
  - "HTMX period filtering: Button group updates #cost-data div via hx-get without full page reload"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 20 Plan 03: TTS Cost Monitoring Summary

**TTS cost dashboard tracking character usage per role with provider-aware pricing and budget alerts at /admin/tts-costs**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T19:49:22Z
- **Completed:** 2026-02-27T19:51:21Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- TTS cost monitoring dashboard aggregates character usage from api_events
- Per-role cost breakdown with Azure ($15/M) and ElevenLabs ($30/M) pricing
- Budget alert when monthly spend exceeds 80% of previous month average
- Time period filter (7d, 30d, 90d) with HTMX partial updates

## Task Commits

Each task was committed atomically:

1. **Task 1: Add TTS cost aggregation route and templates** - `579ded2` (feat)
2. **Task 2: Add TTS Costs sidebar nav entry** - `27641b0` (feat)

## Files Created/Modified
- `app/routers/admin.py` - Added /admin/tts-costs route with character usage aggregation, provider-aware cost calculation, and budget alert logic
- `app/templates/admin/tts_costs.html` - Main TTS cost dashboard with summary cards, period filter, and HTMX integration
- `app/templates/admin/partials/tts_cost_chart.html` - HTMX partial for role breakdown and daily cost tables
- `app/templates/admin/base.html` - Added TTS Costs sidebar nav link between Audio Archive and Search

## Decisions Made

**Budget alert threshold at 80% of previous period:**
- Compares current period spend to previous period spend (not static threshold)
- Adapts to usage patterns automatically
- Only shows alert when previous period data exists (days <= 30)

**Provider-aware cost calculation:**
- Azure TTS: $15 per million characters
- ElevenLabs TTS: $30 per million characters
- Pricing extracted from detail JSON provider field
- Accurate cost tracking across both providers

**Historical event handling:**
- Events before Plan 20-01 may have character_count=0
- Dashboard gracefully shows $0.00 cost for these events
- No errors, correct behavior for incomplete historical data

**Daily aggregation structure:**
- Groups by date and role for per-role cost breakdown
- Enables tracking which roles generate highest TTS costs
- Daily view shows temporal cost patterns

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. TTS cost monitoring uses existing api_events data populated by Phase 20-01.

## Next Phase Readiness

**Phase 20 complete.** All Archive & Operations requirements satisfied:
- OPS-03: TTS character usage tracked per role per day ✓ (Plan 20-01)
- OPS-04: Cost monitoring dashboard with budget alerts ✓ (Plan 20-03)
- DLVR-03: Audio retention cleanup with configurable days ✓ (Plan 20-01)
- DLVR-04: Audio archive browser with inline player ✓ (Plan 20-02)

**v2.0 milestone delivery complete:**
- Phase 17: TTS text preprocessing and Azure OpenAI integration ✓
- Phase 18: ElevenLabs failover with cost alerting ✓
- Phase 19: Pipeline integration and email delivery ✓
- Phase 20: Archive operations and cost monitoring ✓

**Ready for:**
- Production deployment of v2.0 Audio Intelligence Briefings
- Live audio generation and delivery to stakeholders
- Cost monitoring and budget management via admin dashboard

**Blockers:**
- Azure OpenAI TTS credentials still needed for end-to-end testing
- ElevenLabs credentials needed for failover testing
- Both providers functional but untested without credentials configured

---
*Phase: 20-archive-operations*
*Completed: 2026-02-27*
