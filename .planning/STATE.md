# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** Phase 12 — Enterprise Email Delivery (next up)

## Current Position

Phase: 11 of 13 (Equity Price Enrichment) — VERIFIED ✓
Plan: 3 of 3 in current phase
Status: Phase complete — verified (4/4 must-haves passed), requirements EQTY-01/02/03/04 + FALL-03 marked Complete
Last activity: 2026-02-19 — Phase 11 executed, verified, and closed

Progress: v1.0 [██████████] 100% | v1.1 [████████░░] 67% (8/12 plans)

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 39
- Total phases: 8
- Shipped: 9 days (Feb 6-15, 2026)

**v1.1 Baseline:**
- Plans planned: 12 across 5 phases
- Completed: 8 (09-01, 09-02, 10-01, 10-02, 10-03, 11-01, 11-02, 11-03)

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
- Staging Factiva API validation deferred — no credentials on dev machine; validate on deployment machine
- Hidden input + checkbox pattern for boolean (enabled field)
- page_size validated against whitelist (10/25/50/100) in POST route
- Industry code reference table embedded inline in admin page

Phase 11 plan 01 decisions:
- EquityPriceClient returns None on all failures — never raises, callers always safe to ignore
- Multiple field name fallbacks (price/lastPrice/last, change/priceChange/netChange, changePct/percentChange/pctChange) — equity API field names not yet confirmed
- BASE_PRICE_PATH = /coreapi/equity-price/v1/price — inferred, validate on deployment machine
- Flash messages via query params on redirect — no session middleware; stateless and simple
- equity_edit.html as separate template — cleaner than embedding in equity.html

Phase 11 plan 02 decisions:
- Step 3b runs on original articles list (from Step 2), not re-queried classified_articles — SQLAlchemy re-query returns fresh objects that don't carry transient _equity_data attributes
- Equity data bridged via id-keyed dict after Step 4 re-query: equity_data_map = {a.id: getattr(a, '_equity_data', []) for a in articles}
- Unconfigured equity client and no ticker mappings both result in _equity_data=[] — never None, never blocking
- run_full_pipeline_with_email() tracks step_3b duration; run_full_pipeline() does not (consistent with each method's existing pattern)

Phase 11 plan 03 decisions:
- Equity chips placed first in impact-strip (before sentiment/impact/region) — most visually prominent
- is not none (Jinja2 lowercase) used for null checks — Jinja2 does not support capital None
- Email template: display:inline-block not inline-flex — Outlook does not support flexbox
- Email template: explicit padding properties not shorthand — maximum email client compatibility
- .equity-chip CSS class with hover transition in browser brief only — email must use inline styles only

### Pending Todos

None.

### Blockers/Concerns

- Staging credentials still needed to run scripts/test_auth.py against the real endpoint
- Industry codes i83, i8311, i8312, i831 are inferred — validate against /coreapi/recent-news/v1/industries on deployment machine before production
- BASE_PRICE_PATH `/coreapi/equity-price/v1/price` is inferred — validate against actual equity API on deployment machine
- Equity API response field names (price/lastPrice etc.) need validation against real API response

## Session Continuity

Last session: 2026-02-19
Stopped at: Phase 11 complete — verified ✓, requirements complete, roadmap updated
Resume file: None
Next: `/gsd:discuss-phase 12` or `/gsd:plan-phase 12` to start Enterprise Email Delivery
