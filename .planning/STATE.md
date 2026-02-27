# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-27)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** v2.0 Audio Intelligence Briefings

## Current Position

Milestone: v2.0 Audio Intelligence Briefings
Phase: 20 - Archive & Operations (IN PROGRESS)
Plan: 1 of 3 complete (20-01 complete)
Status: Phase 20 in progress
Last activity: 2026-02-27 — Completed 20-01-PLAN.md

Progress: v1.0 [##########] 100% | v1.1 [##########] 100% | v1.2 [##########] 100% | v2.0 [████████..] 80%

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 39
- Total phases: 8
- Shipped: 9 days (Feb 6-15, 2026)

**Velocity (v1.1):**
- Total plans completed: 12
- Total phases: 5
- Shipped: 2 days (Feb 18-19, 2026)

**Velocity (v1.2):**
- Total plans completed: 8
- Total phases: 3
- Shipped: 2 days (Feb 26-27, 2026)
- Must-haves verified: 43/43
- Requirements satisfied: 20/20
- Net lines: -1,338 (major cleanup)

**v2.0 Progress:**
- Total phases: 4 (Phase 17-20)
- Plans completed: 9 of ~11 estimated
- Phase 17 progress: 3 of 3 plans complete (Phase 17 complete)
- Phase 18 progress: 2 of 2 plans complete (Phase 18 complete)
- Phase 19 progress: 3 of 3 plans complete (Phase 19 complete)
- Phase 20 progress: 1 of 3 plans complete (20-01 complete)
- Requirements mapped: 16/16
- Requirements satisfied: 15/16 (OPS-03 and OPS-04 satisfied in 20-01; DLVR-03, DLVR-04 remain for 20-02/20-03)
- Coverage: 100%
- Depth: Comprehensive (4-phase structure from research)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Recent v2.0 decisions:
- Azure OpenAI TTS as primary, ElevenLabs as fallback (Phase 17-18)
- Per-role audio (not combined) matching core value proposition (Phase 17)
- Admin dashboard serves streaming audio using existing FastAPI server (Phase 19-20)
- Filesystem storage for MP3 files (better streaming than DB BLOBs for 2-4 MB files)
- Parallel processing for all 4 roles (Phase 19)
- Operations requirements integrated throughout (not separate monitoring phase)
- All pronunciation control via text preprocessing — OpenAI TTS does not support SSML (17-01)
- Role-specific tone via GPT-4o prompts, not TTS voice changes — one voice for all roles (17-01)
- Articles reuse reporter.py dict structure for seamless pipeline integration (17-01)
- TTS client separate from GPT-4o client for independent deployment/scaling (17-02)
- Idempotent generation with 100KB file size validation prevents duplicate API costs (17-02)
- Atomic file writes (temp + rename) prevent corruption from interrupted generation (17-02)
- Validation script created for programmatic audio checks; human verification deferred (17-03)
- Strategy pattern with TTSProvider ABC for transparent provider swapping (18-01)
- Common TTSError exception for unified failover exception handling (18-01)
- ElevenLabs SDK over custom HTTP client for faster implementation and fewer bugs (18-01)
- Atomic file writes preserved in both Azure and ElevenLabs providers (18-01)
- Automatic failover without retry on primary provider — providers handle their own retries (18-02)
- Cost alert on ElevenLabs fallback success — 20x more expensive than Azure (18-02)
- SessionLocal pattern for api_events logging — matches factiva.py/equity.py pattern (18-02)
- Never propagate logging errors — database failures should not break audio generation (18-02)
- Lazy import audio service in pipeline to avoid circular dependencies (19-01)
- run_in_executor for sync audio generation wrapped in async pipeline (19-01)
- return_exceptions=True for graceful audio generation degradation (19-01)
- Audio endpoint before archive endpoint to avoid FastAPI route conflicts (19-01)
- FileResponse automatic HTTP range support for browser audio seeking (19-01)
- Base64-encoded MP3 attachments in both enterprise and graph email services (19-02)
- 3MB audio file size limit with warning logs for oversized files (19-02)
- Relative URLs for streaming links in email HTML (works in all environments) (19-03)
- Conditional template rendering for graceful audio section omission (19-03)
- HTML entities for emoji in email templates (maximum client compatibility) (19-03)
- AUDIO_RETENTION_DAYS default 90 matches industry standard for audit logs (20-01)
- Cleanup runs as Step 10 in production pipeline only (not run_sync) (20-01)
- Cleanup failures never crash pipeline (wrapped in try/except with silent return) (20-01)
- Per-file deletion logging to structlog, summary to api_events (20-01)

### Pending Todos

None.

### Blockers/Concerns

Carried across milestones:
- Staging credentials still needed to run scripts/test_auth.py against real endpoint
- Industry codes i83, i8311, i8312, i831 are inferred — validate on deployment machine
- Industry code i832 is inferred — validate for production use
- BASE_PRICE_PATH and equity API field names need validation against live API
- Enterprise email FIELD_* constants are inferred — validate on deployment machine
- TD-01: Admin trigger routes don't pass TokenManager (medium severity, non-production impact)

v2.0 blockers:
- **Azure OpenAI TTS credentials needed for audio generation end-to-end testing** — Phase 17 services complete but human audio quality verification deferred until credentials configured (see 17-03-SUMMARY.md)
- **ElevenLabs credentials needed for failover testing** — Phase 18-01 complete but ElevenLabs provider untested until ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID configured (see 18-01-SUMMARY.md user setup section)

## Session Continuity

Last session: 2026-02-27
Stopped at: Completed 20-01-PLAN.md
Resume file: None
Next: Continue with 20-02 or 20-03 plans
