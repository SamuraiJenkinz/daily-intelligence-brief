# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** Phase 10 — Factiva News Collection (next up)

## Current Position

Phase: 10 of 13 (Factiva News Collection) — COMPLETE
Plan: 3 of 3 in current phase (all plans done)
Status: Phase 10 complete — next phase is 11 (Email Delivery)
Last activity: 2026-02-18 — Completed 10-03-PLAN.md (Factiva admin config UI)

Progress: v1.0 [██████████] 100% | v1.1 [█████░░░░░] 42% (5/12 plans)

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 39
- Total phases: 8
- Shipped: 9 days (Feb 6-15, 2026)

**v1.1 Baseline:**
- Plans planned: 12 across 5 phases
- Completed: 3 (09-01, 09-02, 10-01)

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

Phase 10 plan 01 decisions:
- Sync httpx.Client (not async) — matches existing ApifyCollector pattern
- X-Api-Key only header — Factiva news endpoint does not require JWT Bearer
- collector_source default "Apify/RSS" — backward-compatible for all pre-Phase-10 articles
- Per-article fetch failures fall back to snippet, not hard errors — pipeline gets max coverage
- MAX_ARTICLES=100 hard cap with pageSize100 link follow — avoids N-API-call loop
- Migration in lifespan() with try/except — startup never blocked by schema failure

Phase 10 plan 02 decisions:
- INSURANCE_FALLBACK_SOURCES hardcoded list (Reinsurance News, Insurance Journal, Artemis, Lloyd's List) — keeps fallback brief insurance-focused
- Zero Factiva articles triggers fallback — zero results signals API/query breakage, not low volume
- store_factiva_articles() creates its own Run record — Factiva collection independently traceable
- URL dedup uses date(created_at) == today — handles pipeline reruns within same day
- collector_source=None treated as "Apify/RSS" via getattr fallback — backward-compatible without migration

Phase 10 plan 03 decisions:
- Staging Factiva API validation deferred — no credentials on dev machine; validate on deployment machine with MMC_API_BASE_URL + MMC_API_KEY set; run GET /coreapi/recent-news/v1/industries to confirm i83/i8311/i8312/i831
- Hidden input + checkbox pattern for boolean: hidden field with value="false" before checkbox ensures form always submits "enabled" key; FastAPI last-value-wins reads true when checkbox checked
- page_size validated against whitelist (10/25/50/100) in POST route — values outside coerced to 25
- Industry code reference table embedded inline in admin page — docs-as-UI for operator guidance

### Pending Todos

None.

### Blockers/Concerns

- Staging credentials still needed to run scripts/test_auth.py against the real endpoint
- Industry codes i83, i8311, i8312, i831 are inferred — validate against /coreapi/recent-news/v1/industries on deployment machine before production to avoid empty result sets

## Session Continuity

Last session: 2026-02-18
Stopped at: Completed 10-03-PLAN.md — Factiva admin config UI complete; Phase 10 fully done
Resume file: None
Next: Execute Phase 11 (Email Delivery) — begin with 11-01-PLAN.md
