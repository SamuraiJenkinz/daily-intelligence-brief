# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** Phase 9 — OAuth2 Token Management (v1.1, phase complete)

## Current Position

Phase: 9 of 13 (OAuth2 Token Management)
Plan: 2 of 2 in current phase
Status: Phase complete — both plans done, ready for Phase 10
Last activity: 2026-02-18 — Completed 09-02-PLAN.md (pipeline integration)

Progress: v1.0 [██████████] 100% | v1.1 [██░░░░░░░░] 17% (2/12 plans)

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 39
- Total phases: 8
- Shipped: 9 days (Feb 6-15, 2026)

**v1.1 Baseline:**
- Plans planned: 12 across 5 phases
- Completed: 2 (09-01, 09-02)

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

Phase 9 plan 02 decisions:
- degraded_auth defaults to True — safe: Graph API fallback always available
- MMC auth/key missing in health check returns status=info not warning (optional features)
- Step 0 auth prefix avoids renumbering existing steps 1-9
- asyncio.run() used in sync run_full_pipeline for token acquisition

### Pending Todos

None.

### Blockers/Concerns

- Staging credentials still needed to run scripts/test_auth.py against the real endpoint

## Session Continuity

Last session: 2026-02-18
Stopped at: Completed 09-02-PLAN.md — pipeline auth integration (TokenManager wired into pipeline)
Resume file: None
Next: Plan Phase 10 (Factiva News Integration)
