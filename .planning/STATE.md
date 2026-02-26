# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** v1.2 Factiva Knowledge Integration — Port BrasilIntel's FactivaCollector

## Current Position

Milestone: v1.2 Factiva Knowledge Integration
Phase: 14 of 16 (FactivaCollector Port)
Plan: —
Status: Roadmap created, ready for planning
Last activity: 2026-02-26 — v1.2 roadmap created with 3 phases

Progress: v1.0 [##########] 100% | v1.1 [##########] 100% | v1.2 [░░░░░░░░░░] 0%

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
- FactivaConfig seed data must target MMC audience (brokers, leadership, compliance, underwriting)

## Session Continuity

Last session: 2026-02-26
Stopped at: v1.2 roadmap creation complete
Resume file: None
Next: `/gsd:plan-phase 14` to create execution plan for FactivaCollector port
