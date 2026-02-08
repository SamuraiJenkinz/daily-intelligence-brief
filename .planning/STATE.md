# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-06)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** Phase 6 complete — ready for Phase 7

## Current Position

Phase: 7 of 8 COMPLETE (Production Hardening)
Plan: 5/5 complete
Status: Phase 7 COMPLETE — Production hardening infrastructure operational (logging, backup, health monitoring, drift detection, deploy integration)
Last activity: 2026-02-08 — Completed 07-05-PLAN.md
Verified: Not yet verified

Progress: [█████████░] 97.4% (Phase 1: 5/5, Phase 2: 6/6, Phase 3: 3/3, Phase 4: 7/7, Phase 5: 4/4, Phase 6: 5/5, Phase 7: 5/5)

## Performance Metrics

**Velocity:**
- Total plans completed: 35
- Average duration: 15.2 minutes
- Total execution time: 7.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 5/5 | 26 min | 5.2 min |
| 02 | 6/6 | 17 min | 2.8 min |
| 03 | 3/3 | 5.5 min | 1.8 min |
| 04 | 7/7 | 24 min | 3.4 min |
| 05 | 4/4 | 43.7 min | 10.9 min |
| 06 | 5/5 | 35 min | 7.0 min |
| 07 | 5/5 | 300 min | 60.0 min |

**Recent Trend:**
- Last 5 plans: 07-01 (19min), 07-02 (24min), 07-03 (50min), 07-04 (44min), 07-05 (163min)
- Trend: Phase 7 complete — production hardening infrastructure operational
- **Phase 1 complete**: Vertical slice operational
- **Phase 2 complete**: 20 sources, semantic dedup, health monitoring, pipeline integrated
- **Phase 3 complete**: 9-dimension classification (entities, impact, category, region, business line)
- **Phase 4 complete**: 7/7 plans complete (role filtering, exec summaries, aggregation, template integration)
- **Phase 5 complete**: 4/4 plans complete (email infrastructure, template, pipeline integration, Task Scheduler automation)
- **Phase 6 complete**: 5/5 plans complete (base template, source CRUD, archive browser, FTS5 search, recipient management)
- **Phase 7 complete**: 5/5 plans complete (structured logging, retry logic, database backup, health monitoring, drift detection, deploy integration)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Bootstrap 5.3.3 + HTMX 2.0.4** (06-01): Latest stable versions from CDN for admin dashboard. No build step required.
- **CDN-only approach** (06-01): All CSS/JS from CDN (Bootstrap, HTMX, Bootstrap Icons) for zero build complexity.
- **Responsive sidebar at 768px** (06-01): Standard Bootstrap md breakpoint, sidebar collapses to hamburger menu on mobile.
- **Admin dashboard as root** (06-01): Root / redirects to /admin (not /docs) making admin interface the primary entry point.
- **Jinja2 template inheritance** (06-01): base.html provides master layout, all admin pages extend it for consistent navigation and branding.
- **Pydantic for server-side validation** (06-02): SourceCreate/SourceUpdate schemas provide robust validation with inline error display in HTMX partials.
- **Inline editing with row swap** (06-02): Edit button swaps display row with edit form row using HTMX outerHTML swap.
- **HX-Request header detection** (06-02): Single endpoint serves full page on initial load, partial on HTMX requests.
- **Archive security: multi-layer validation** (06-03): Date regex + role whitelist + Path.resolve() prevents path traversal.
- **30s auto-refresh for runs table** (06-03): hx-trigger="every 30s" shows real-time pipeline status.
- **FTS5 with BM25 ranking** (06-04): SQLite FTS5 for fast full-text search with relevance ranking.
- **300ms debounce delay** (06-04): Balance responsive UX with server load for search-as-you-type.
- **Graceful fallback to LIKE queries** (06-04): FTS5 table might not exist if migration not run.
- **Recipient .env persistence** (06-05): Changes saved to .env with settings cache clearing for immediate effect.
- **structlog + stdlib integration** (07-01): Structured JSON logging with stdlib handlers for compatibility with existing ecosystem.
- **Daily log rotation with 30-day retention** (07-01): Balance disk space with sufficient debugging history.
- **tenacity for retry logic** (07-01): Mature library with exponential backoff, jitter, and async support.
- **Different retry configs per service** (07-01): Collector 4-30s, classifier 2-15s, emailer 2-10s based on operation characteristics.
- **run_id context binding** (07-01): Automatic run_id inclusion in all log entries via structlog contextvars.
- **sqlite3 .backup() API** (07-02): Use sqlite3 .backup() instead of file copy for safe online backups without exclusive locks.
- **Local-then-Azure backup** (07-02): Create local backup first, verify integrity, then upload to Azure for disaster recovery.
- **Dual retention strategy** (07-02): 7 days local (fast restore), 30 days Azure configurable (disaster recovery).
- **Statistical health thresholds** (07-03): Use max(baseline_avg - 2*std, baseline_avg * 0.3) for warning threshold (more lenient approach adapts to source variability).
- **Consecutive low runs tracking** (07-03): Count consecutive below-baseline runs to distinguish single anomaly from persistent degradation.
- **Step 1b health check pattern** (07-03): Insert health check between collection and classification for immediate anomaly detection with run_id context.
- **Graceful health alert failures** (07-03): Health alert email failures are logged but don't block pipeline execution.
- **Priority as confidence proxy** (07-04): Use priority distribution as behavioral proxy since Azure OpenAI structured outputs don't return confidence scores.
- **14-day baseline with 3-day recent** (07-04): Balance statistical power (30+ samples) with drift detection speed (catch issues within days).
- **Three drift tests** (07-04): KS test for priority distribution, chi-square for role/category distributions, comprehensive coverage of failure modes.
- **0.05 p-value threshold** (07-04): Standard statistical significance (95% confidence) balances sensitivity with false positive rate.
- **07:00 backup timing** (07-05): 1 hour after pipeline gives completion buffer before backup runs.
- **Monday 08:00 drift check** (07-05): Weekly frequency balances noise reduction with detection speed (daily would be too noisy).
- **36-hour backup threshold** (07-05): Allows timing variance while catching stale backups within reasonable window.
- **4-task orchestration** (07-05): Pipeline (06:00) → Backup (07:00) → Drift (Mon 08:00) → Monitor (09:00) provides comprehensive automation.

### Pending Todos

None.

### Blockers/Concerns

None — Phase 7 complete, production hardening infrastructure operational

## Session Continuity

Last session: 2026-02-08
Stopped at: Completed 07-05-PLAN.md
Resume file: None
Next: Phase 8 (Admin Interface Enhancements) ready to begin
