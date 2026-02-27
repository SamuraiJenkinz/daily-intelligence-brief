---
phase: 17-audio-generation-foundation
plan: 02
subsystem: audio
tags: [azure-openai-tts, audio-generation, mp3-files, idempotent-generation, atomic-writes]

# Dependency graph
requires:
  - phase: 17-01
    provides: ScriptGenerator and TextPreprocessor services
  - phase: 01-mvp-core-pipeline
    provides: Azure OpenAI client initialization patterns (reporter.py, classifier.py)
provides:
  - AudioBriefingService orchestrating full script-to-MP3 pipeline
  - Idempotent audio generation with atomic file writes
  - Standalone CLI tool for manual audio testing
affects: [17-03, 19-pipeline-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [Idempotent generation, Atomic file writes, Retry logic with exponential backoff, TTS client separation]

key-files:
  created: [app/services/audio_generator.py, scripts/generate_audio.py]
  modified: []

key-decisions:
  - "TTS client separate from GPT-4o client (may use different deployment)"
  - "Idempotent generation checks file size >100KB before skipping"
  - "Atomic file writes using temp file + rename pattern"
  - "File storage at data/audio/YYYY-MM-DD/{role}.mp3 (lowercase role names)"
  - "Word count validation logs warning if outside 250-600 range (not blocking)"
  - "CLI script uses ASCII-safe output for Windows console compatibility"

patterns-established:
  - "Separate TTS client initialization following reporter.py pattern"
  - "Batch generation with per-role error handling (one failure doesn't block others)"
  - "CLI script loads from most recent completed Run in database"
  - "Duration estimation formula: word_count / 150 wpm"

# Metrics
duration: 11min
completed: 2026-02-27
---

# Phase 17 Plan 02: Audio Generation Service Summary

**AudioBriefingService orchestrates script-to-MP3 pipeline with idempotent generation, atomic file writes, and standalone CLI testing tool**

## Performance

- **Duration:** 11 min
- **Started:** 2026-02-27T16:15:00Z
- **Completed:** 2026-02-27T16:26:16Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments
- AudioBriefingService chains ScriptGenerator -> TextPreprocessor -> Azure OpenAI TTS to produce MP3 files
- Idempotent generation skips if valid MP3 exists (>100KB file size check)
- Atomic file writes use temp file + rename pattern to prevent corruption
- Retry logic with exponential backoff for TTS API calls (3 attempts, 2-15s backoff)
- Batch generation method processes all 4 roles with per-role error handling
- Standalone CLI script (scripts/generate_audio.py) enables manual testing from completed pipeline runs
- File naming convention: data/audio/YYYY-MM-DD/{role}.mp3 (lowercase role names)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create audio generator service with TTS conversion** - `ee52484` (feat)
2. **Task 2: Create standalone CLI runner for audio testing** - `2e2f84c` (feat)

## Files Created/Modified
- `app/services/audio_generator.py` - AudioBriefingService with full pipeline orchestration
- `scripts/generate_audio.py` - CLI tool for standalone audio generation testing

## Decisions Made

All decisions followed plan as specified:
- TTS client initialized separately from GPT-4o client (may use different Azure OpenAI deployment)
- Idempotent generation checks file existence and validates size >100KB before skipping
- Atomic file writes prevent corruption from interrupted generation (temp file + rename)
- File storage at data/audio/YYYY-MM-DD/{role}.mp3 following existing project conventions
- Word count validation logs warnings if outside 250-600 range but doesn't block generation
- Batch generation handles per-role failures gracefully (one failure doesn't stop others)

## Deviations from Plan

Minor improvements beyond plan scope:
- Added voice property as configurable setting (supports future customization via config)
- CLI script includes duration estimation (word_count / 150 wpm) for user feedback
- CLI script uses ASCII-safe output ([OK], [X], [*]) for Windows console compatibility
- generate_all_briefings returns comprehensive summary dict with success/skip/fail counts

No functional deviations - all core requirements met.

## Issues Encountered

**Windows console encoding issue:**
- **Problem:** Original script used emoji characters (✅, ❌, 📋) causing UnicodeEncodeError on Windows
- **Solution:** Replaced emoji with ASCII-safe status indicators ([OK], [X], [*])
- **Impact:** None - CLI remains fully functional with clear visual indicators

No blocking issues encountered. Service instantiates successfully and follows all established patterns.

## User Setup Required

None - service gracefully handles missing Azure OpenAI configuration by returning runtime errors with clear messages. CLI script validates configuration before attempting generation.

## Next Phase Readiness

**Ready for Phase 17-03 (ElevenLabs Fallback):**
- AudioBriefingService provides clear TTS client separation pattern
- Service architecture supports fallback provider integration
- Error handling distinguishes between script/preprocessing failures vs TTS failures

**Ready for Phase 19 (Pipeline Integration):**
- AudioBriefingService.generate_all_briefings() ready for pipeline.py Step 5
- Accepts same article dict structure as reporter.py uses
- Idempotent generation prevents duplicate API costs on pipeline retries
- Batch error handling ensures one role's failure doesn't block others

**No blockers or concerns** - audio generation foundation complete and tested.

## Technical Notes

**TTS Client Initialization Pattern:**
- Follows reporter.py pattern for corporate proxy support (/deployments/ endpoint detection)
- TTS client may use different deployment name than GPT-4o deployment
- Separation allows independent scaling and configuration of TTS vs chat completions

**File Size Validation:**
- 100KB threshold based on: 2min audio × 128kbps = ~1.88MB typical, 100KB = corruption indicator
- Corrupted files are automatically deleted and regenerated
- Skipped files are logged with size for audit trail

**Atomic Write Pattern:**
- Temp file written first (.tmp extension)
- Atomic rename to final path (.mp3)
- Prevents partial/corrupted files if process interrupted
- Follows industry best practice for reliable file operations

---
*Phase: 17-audio-generation-foundation*
*Completed: 2026-02-27*
