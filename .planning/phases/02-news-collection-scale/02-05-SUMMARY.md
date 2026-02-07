---
phase: 02-news-collection-scale
plan: 05
subsystem: monitoring
tags: [health-monitoring, source-health, sqlalchemy, structlog]

# Dependency graph
requires:
  - phase: 01-vertical-slice-validation
    provides: ORM models (Source, Run, NewsArticle) for health queries
provides:
  - SourceHealthMonitor service with baseline calculation and alert detection
affects: [02-06-health-alerting, 07-scheduling-automation]

# Tech tracking
tech-stack:
  added: []
  patterns: [health-monitoring, baseline-calculation, alert-threshold-detection]

key-files:
  created: [app/services/health_monitor.py]
  modified: []

key-decisions:
  - "7-day moving average baseline for article count analysis"
  - "50% baseline threshold for warning alerts"
  - "Zero articles with non-zero baseline triggers critical alerts"
  - "New sources with <7 days history return 'unknown' status to avoid false alarms"
  - "Health checks query completed runs only (ignore running/failed runs)"

patterns-established:
  - "Health monitoring pattern: baseline calculation → latest comparison → status determination"
  - "Alert flag pattern: boolean alert field for filtering actionable statuses"
  - "Structlog logging with service binding for health monitoring events"

# Metrics
duration: 3min
completed: 2026-02-07
---

# Phase 2 Plan 5: Source Health Monitor Summary

**Source health monitoring with 7-day baseline calculation, alert thresholds (zero articles critical, <50% baseline warning), and unknown status for new sources**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-07T07:10:57Z
- **Completed:** 2026-02-07T07:13:57Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- SourceHealthMonitor service detects source anomalies using 7-day moving average baseline
- Critical alerts for zero articles when baseline exists
- Warning alerts for article counts below 50% of baseline
- Graceful handling of new sources (no false alarms for insufficient history)
- Queries completed runs only for accurate health metrics

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SourceHealthMonitor service** - `ab9ab4f` (feat)

## Files Created/Modified
- `app/services/health_monitor.py` - Source health monitoring service with baseline calculation and alert detection

## Decisions Made

**7-day lookback period:** Uses 7-day moving average for baseline calculation, balancing recency with statistical stability. Configurable via constructor parameter.

**50% baseline threshold:** Warning alerts trigger when latest count falls below 50% of baseline average, catching significant drops without excessive false positives.

**Zero articles critical status:** Only triggers critical alert if baseline_avg > 0, preventing false alarms for sources that legitimately have intermittent publishing.

**Unknown status for new sources:** Sources with no completed runs in lookback period get 'unknown' status with alert=False, avoiding false alarms during initial setup.

**Completed runs only:** Queries filter to `RunStatus.COMPLETED` to exclude running or failed runs from health calculations, ensuring accurate baseline metrics.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded without issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:**
- Plan 02-06: Health alerting endpoint can now consume SourceHealthMonitor.get_alerts()
- Phase 7: Scheduler can use health monitor for automated monitoring

**Architecture notes:**
- Health monitor is stateless and query-based (no persistent state)
- All thresholds and logic encapsulated in service layer
- Can be extended with additional health checks (staleness, error rates, etc.)

---
*Phase: 02-news-collection-scale*
*Completed: 2026-02-07*
