# Phase 15: Pipeline Simplification & Cleanup - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Simplify the pipeline to use FactivaCollector as the sole collection path (no Apify/RSS fallback) and remove all Apify infrastructure from the codebase. Deduplication and classification continue to work. No new collection sources are added.

</domain>

<decisions>
## Implementation Decisions

### Failure mode (no fallback)
- Retry with existing exponential backoff (Phase 14), then skip daily brief and alert admin if still failing
- When Factiva returns zero articles (not a failure), send an empty brief so recipients know the system ran
- Remove all fallback code paths completely — no stub comments, no breadcrumbs about where Apify fallback used to be

### Dedup simplification
- Keep semantic dedup (sentence-transformers) as-is — still catches near-duplicate Factiva articles from different wire services
- Keep source-aware URL dedup logic intact — no simplification
- Keep generic multi-source interface in dedup layer for future extensibility
- Keep dedup similarity threshold hardcoded — no new config knob

### Cleanup thoroughness
- Remove all Apify-specific test files, fixtures, and mock data (not just production code)
- Full codebase sweep: hunt down and remove all Apify references in comments across entire codebase
- Clean slate — no Apify traces should remain anywhere

### Pipeline orchestrator shape
- Collapse to direct FactivaCollector call — remove source-abstraction layer (no loop over sources)
- Keep structured result from orchestrator run (article counts: collected, deduped, classified)

### Claude's Discretion
- Admin notification mechanism when pipeline skips after retry failure (dashboard event, email, or both — match existing patterns)
- Whether wire-service dedup needs a separate step or semantic dedup handles it sufficiently
- Pipeline stage ordering for single-source flow (collect -> dedup -> classify or reorder if beneficial)
- Dedup logging level — simplify or keep verbose based on current patterns
- Pipeline stage merging — keep distinct or merge where stages become trivial
- `is_configured()` check scope — what to verify for Factiva readiness
- Database schema changes — whether Apify-specific columns exist and risk/benefit of removal
- base.py in app/services/sources/ — keep full abstract interface or trim to Factiva needs based on actual usage

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-pipeline-simplification-cleanup*
*Context gathered: 2026-02-26*
