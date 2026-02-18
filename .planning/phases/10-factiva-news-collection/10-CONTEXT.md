# Phase 10: Factiva News Collection - Context

**Gathered:** 2026-02-18
**Status:** Ready for planning

<domain>
## Phase Boundary

The pipeline fetches insurance/reinsurance news from Factiva as its primary source each morning, with Apify/RSS running automatically as fallback when Factiva is unavailable, and article source stored per-article. Query parameters are admin-configurable. Articles flow through the existing AI classification pipeline unchanged.

</domain>

<decisions>
## Implementation Decisions

### Query design
- Query scope approach is Claude's discretion — pick the combination of industry codes, company codes, and keywords that best feeds the existing AI classification pipeline
- Query parameters (industry codes, company codes, keywords) must be admin-configurable from the dashboard UI
- Time window: last 24 hours per morning run — straightforward daily collection
- Article fetch limit is Claude's discretion — pick a sensible default with rationale

### Fallback behavior
- Fallback trigger strategy is Claude's discretion — balance reliability with speed (retry vs immediate fallback)
- Partial results: accept whatever Factiva returns, even if low volume — do NOT supplement with Apify/RSS in the same run
- Fallback scope: reduced set — only insurance-focused Apify/RSS sources run during fallback, skip general business news sources
- Fallback events must be logged as structured events (feeds into Phase 13 admin dashboard)

### Article deduplication
- Deduplication strategy is Claude's discretion — pick the most reliable approach for cross-source dedup (title similarity, content hash, or hybrid)
- Dedup winner: when a Factiva article duplicates an existing Apify/RSS article, keep the Factiva version (Factiva is preferred source)
- Dedup window: current day only — only deduplicate against articles collected today
- Dedup logging is Claude's discretion — decide based on operational needs

### Source attribution
- Each article record in the database carries a source field (Factiva or Apify/RSS)
- Brief display: visible source badge on each article in the generated brief (e.g., "via Factiva", "via RSS")
- Badge labels: use explicit source names — "Factiva" and "Apify/RSS", not generic labels
- Factiva articles listed first within each section of the brief — prioritized over Apify/RSS articles
- Admin dashboard: per-run source breakdown showing how many articles came from each source (e.g., "12 Factiva, 3 RSS")

### Claude's Discretion
- Factiva query scope (industry codes vs company+industry vs keyword combination)
- Article fetch limit per query
- Fallback trigger strategy (retry count, timeout thresholds)
- Deduplication algorithm (title similarity, content hash, or hybrid)
- Dedup logging approach

</decisions>

<specifics>
## Specific Ideas

- Fallback should only run insurance-focused sources, not the full v1.0 Apify/RSS source list — keeps fallback briefs relevant and fast
- Factiva articles should feel like first-class citizens in the brief — listed first, with explicit "Factiva" badge
- Admin dashboard needs per-run source stats, not just per-article badges — gives Kevin visibility into whether Factiva is earning its keep

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-factiva-news-collection*
*Context gathered: 2026-02-18*
