# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** v1.2 Factiva Knowledge Integration — Port BrasilIntel's FactivaCollector

## Current Position

Milestone: v1.2 Factiva Knowledge Integration
Phase: 15 of 16 (Pipeline Simplification & Cleanup) — IN PROGRESS
Plan: 01 of 03 — COMPLETE
Status: Plan 15-01 complete, ready for Plan 15-02
Last activity: 2026-02-26 — Completed 15-01-PLAN.md

Progress: v1.0 [##########] 100% | v1.1 [##########] 100% | v1.2 [████░░░░░░] 40%

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 39
- Total phases: 8
- Shipped: 9 days (Feb 6-15, 2026)

**Velocity (v1.1):**
- Total plans completed: 12
- Total phases: 5
- Shipped: 2 days (Feb 18-19, 2026)

**v1.2 Target:**
- 3 phases (14-16)
- Plan count: TBD during phase planning

*Updated after milestone completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Key v1.2 design decisions:
- Phase 14: Port BrasilIntel's proven FactivaCollector (456 lines) as foundation before cleanup
- Phase 15: Combine pipeline simplification and Apify cleanup (tightly coupled operations)
- Phase 16: Dashboard/config updates last (cosmetic relative to collector changes)

Phase 14-01 decisions:
- default-date-range-48h: Use 48h lookback (BrasilIntel proven approach) vs. 24h (current MDInsights)
- preserve-existing-config: Migration adds column but preserves admin-customized values in existing rows
- corrected-seed-data-i82: Seed data uses validated 'i82' industry code only (not unvalidated 'i82,i832')

Phase 14-02 decisions:
- api-param-mapping: Use correct MMC Core API param names (industry, company, query) validated by BrasilIntel
- keyword-joining-or: OR-join keywords for broader coverage (BrasilIntel proven approach)
- url-encoding-article-ids: quote(article_id, safe='') hardens against special characters
- configurable-date-range: 48h default matches BrasilIntel, allows tuning per deployment
- is-configured-delegation: Consistent with EquityPriceClient and Settings pattern

Phase 15-01 decisions:
- inline-article-storage: Extract article storage from ApifyCollector into PipelineOrchestrator._store_articles()
- run-record-timing: Create Run record at start of Step 1 (before collection) for cleaner logging
- zero-article-handling: Continue pipeline to generate empty brief when Factiva returns zero articles

### Pending Todos

None.

### Blockers/Concerns

Carried from v1.1:
- Staging credentials still needed to run scripts/test_auth.py against real endpoint
- Industry codes i83, i8311, i8312, i831 are inferred — validate on deployment machine
- BASE_PRICE_PATH and equity API field names need validation against live API
- Enterprise email FIELD_* constants are inferred — validate on deployment machine
- TD-01: Admin trigger routes don't pass TokenManager (medium severity, non-production impact)

v1.2 considerations:
- BrasilIntel FactivaCollector reference at C:\BrasilIntel\app\collectors\factiva.py (456 lines)
- Need to adapt Portuguese insurer domain logic to English insurance/reinsurance
- Industry code i832 is inferred (not validated) — may need validation for production use

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed 15-01-PLAN.md
Resume file: None
Next: `/gsd:execute-phase 15-02` for Delete ApifyCollector
