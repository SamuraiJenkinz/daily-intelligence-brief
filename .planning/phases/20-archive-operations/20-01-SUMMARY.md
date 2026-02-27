---
phase: 20-archive-operations
plan: 01
subsystem: operations
tags: [tts, audio, cost-monitoring, retention, cleanup, api-events, structlog]

# Dependency graph
requires:
  - phase: 18-audio-generation
    provides: Audio briefing service with TTS event logging
  - phase: 19-pipeline-integration
    provides: Pipeline orchestration with audio generation step
provides:
  - TTS event logging with character_count and role for cost tracking
  - Audio file retention cleanup with configurable AUDIO_RETENTION_DAYS
  - AUDIO_CLEANUP event type for cleanup summary tracking
  - Pipeline Step 10 for automated audio file retention management
affects: [20-03-cost-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Audio retention cleanup as pipeline step"
    - "AUDIO_RETENTION_DAYS env var for configurable retention"
    - "Empty directory cleanup after file deletion"
    - "Graceful cleanup failure handling (never crashes pipeline)"

key-files:
  created: []
  modified:
    - app/models/api_event.py
    - app/services/audio_generator.py
    - app/services/pipeline.py

key-decisions:
  - "AUDIO_RETENTION_DAYS default 90 (matches industry standard for audit logs)"
  - "Cleanup runs as Step 10 in production pipeline only (not run_sync)"
  - "Cleanup failures never crash pipeline (wrapped in try/except with silent return)"
  - "Per-file deletion logging to structlog, summary to api_events"

patterns-established:
  - "Pattern 1: Audio retention cleanup in pipeline (Step 10 after all delivery steps)"
  - "Pattern 2: Character count tracking in TTS events for cost monitoring"
  - "Pattern 3: Empty date directory removal after file cleanup"

# Metrics
duration: 6min
completed: 2026-02-27
---

# Phase 20 Plan 01: Archive Operations - TTS Cost Tracking & Audio Retention Summary

**TTS character count tracking per role per day, automated audio file cleanup with 90-day retention (configurable via AUDIO_RETENTION_DAYS)**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-27T19:43:08Z
- **Completed:** 2026-02-27T19:49:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- TTS events now include character_count and role in detail JSON for cost monitoring
- Audio files older than AUDIO_RETENTION_DAYS (default 90) automatically deleted
- Empty date directories removed after cleanup
- Cleanup summary logged to both structlog and api_events
- Pipeline Step 10 runs cleanup after email delivery and run record update

## Task Commits

Each task was committed atomically:

1. **Task 1: Add character_count and role to TTS event logging** - `0ad80f1` (feat)
2. **Task 2: Add audio file retention cleanup to pipeline** - `9cf80c6` (feat)

## Files Created/Modified
- `app/models/api_event.py` - Added AUDIO_CLEANUP event type
- `app/services/audio_generator.py` - Enhanced TTS event logging with character_count and role
- `app/services/pipeline.py` - Added _cleanup_old_audio_files() method and Step 10 integration

## Decisions Made
- **AUDIO_RETENTION_DAYS default 90**: Aligns with industry standard for audit/compliance logs while balancing storage costs
- **Cleanup in run() only**: Production pipeline runs cleanup once per day; test/legacy run_sync() skips it
- **Never crash pipeline**: Entire cleanup wrapped in try/except with silent return on error
- **Dual logging**: Per-file deletions to structlog (debugging), summary to api_events (dashboard)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required. AUDIO_RETENTION_DAYS environment variable is optional (defaults to 90 days).

## Next Phase Readiness

Ready for Plan 20-03 (Cost Monitoring Dashboard):
- api_events table now contains character_count and role for TTS_SUCCESS and TTS_FALLBACK events
- AUDIO_CLEANUP events logged with deleted_count, deleted_mb, and retention_days
- Dashboard can query api_events to display cost metrics per role per day

No blockers. Audio cleanup runs silently in production pipeline without user intervention.

---
*Phase: 20-archive-operations*
*Completed: 2026-02-27*
