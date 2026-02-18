# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** Phase 9 — OAuth2 Token Management (v1.1, plan 1 of 2 complete)

## Current Position

Phase: 9 of 13 (OAuth2 Token Management)
Plan: 1 of 2 in current phase
Status: In progress — Plan 01 complete, Plan 02 pending
Last activity: 2026-02-18 — Completed 09-01-PLAN.md (auth foundation)

Progress: v1.0 [██████████] 100% | v1.1 [█░░░░░░░░░] 8% (1/12 plans)

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 39
- Total phases: 8
- Shipped: 9 days (Feb 6-15, 2026)

**v1.1 Baseline:**
- Plans planned: 12 across 5 phases
- Completed: 1 (09-01)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Key decisions for v1.1:
- Factiva as primary news source (enterprise Dow Jones feed)
- Equity data inline with stories (not a separate section)
- Enterprise email with Graph API fallback (reliability)
- Client credentials grant only (server-side pipeline, no user interaction)
- Graceful fallback for all three enterprise APIs

Phase 9 plan 01 decisions:
- 5-minute proactive token refresh margin (REFRESH_MARGIN_SECONDS=300)
- No retry on 401/403 — invalid credentials won't resolve via retry; avoids account lockout
- ApiEventType includes all 9 event types upfront (NEWS, EQUITY, EMAIL) for schema stability
- _record_event() isolates its own DB session; failures are swallowed to protect token flow
- test_auth.py shows first 8 + last 4 chars of token only (security without opacity)

### Pending Todos

None.

### Blockers/Concerns

- Staging credentials still needed to run scripts/test_auth.py against the real endpoint
- Phase 9 Plan 02 covers token refresh scheduling and integration tests — depends on Plan 01 (complete)

## Session Continuity

Last session: 2026-02-18
Stopped at: Completed 09-01-PLAN.md — auth foundation (TokenManager, ApiEvent, test script)
Resume file: None
Next: Execute 09-02-PLAN.md (token refresh scheduling and integration validation)
