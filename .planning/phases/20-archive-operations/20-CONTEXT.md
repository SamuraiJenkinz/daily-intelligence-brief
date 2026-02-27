# Phase 20: Archive & Operations - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Historical audio briefings are browsable and playable via admin dashboard with automated retention policies and cost monitoring. This phase adds audio archive browsing, an HTML5 audio player, TTS cost tracking, and file retention cleanup. It builds on Phase 19's streaming endpoint and pipeline-generated audio files.

</domain>

<decisions>
## Implementation Decisions

### Archive browsing experience
- New dedicated sidebar nav section ("Audio Archive"), not integrated into existing report archive
- Organization: date-first, then roles — browse by date, expand to see all 4 role briefings
- Date navigation: month picker with day list — select a month, see all days that have audio
- Metadata per briefing: duration + file size (e.g., "3:42 · 2.1 MB")

### Audio player design
- Inline row expansion — clicking a briefing expands the row to reveal a player below it
- Standard controls: play/pause, seek bar, current time / total time
- Marsh-branded custom player — styled to match Marsh blue (#00263e, #0077c8) branding
- One briefing at a time — clicking another stops the current one

### Cost monitoring display
- New dedicated sidebar nav section (separate from audio archive)
- Display format, time period aggregation, and alert threshold approach at Claude's discretion

### Retention & cleanup behavior
- Retention period configured via environment variable (AUDIO_RETENTION_DAYS=90 default)
- Cleanup runs during daily pipeline execution (not a separate scheduled task)
- Silent deletion — files past retention get deleted, logged to api_events
- No pinning mechanism — retention policy applies equally to all briefings

### Claude's Discretion
- Cost monitoring page layout, data display format, and time period views
- Budget alert thresholds and presentation
- Exact month picker component implementation
- Player CSS details beyond Marsh color scheme
- Cleanup logging verbosity to api_events

</decisions>

<specifics>
## Specific Ideas

- Existing admin dashboard uses Bootstrap 5 + HTMX + Jinja2 — new pages should follow same patterns
- Existing streaming endpoint at `/admin/audio/{role}/{date}` already supports HTTP range requests
- Existing report archive page (`/admin/archive`) uses month/role filtering — audio archive should feel familiar but be separate
- api_events table already receives audio generation logs from Phase 18-19 — cost tracking extends this

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-archive-operations*
*Context gathered: 2026-02-27*
