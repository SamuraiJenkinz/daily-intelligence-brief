# Phase 16: Dashboard & Config Updates - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Update admin dashboard and configuration files to reflect Factiva-only architecture. Remove all Apify traces from the UI, simplify source presentation for single-source model, and make FactivaConfig the clear sole collection configuration. No new dashboard features or capabilities.

</domain>

<decisions>
## Implementation Decisions

### Health & Status Display
- Remove "degraded" state for news API — news is either healthy (Factiva working) or offline (Factiva down), no fallback exists
- Keep blue Factiva badge on run source breakdown — consistent branding, distinguishes from any historical runs
- Remove NEWS_FALLBACK enum value from ApiEventType — no fallback concept for news anymore
- News API card label — Claude's discretion based on what other API card labels look like

### Source Management UI
- Remove source type entirely from UI — drop the type dropdown and type badges, the distinction is meaningless with single source
- Remove actor_id field from source form — legacy Apify concept, DB column can stay but hide from UI
- Keep sources page with minimal cleanup — remove type dropdown and actor_id, sources still serve as metadata records (name, URL, description)
- Remove type from form AND tighten schema validation — new sources won't have a type, remove "apify"/"rss" from valid types in admin.py schema

### FactivaConfig Admin Experience
- Replace misleading fallback hint with clear warning — "Disabling Factiva will stop all news collection. No fallback source is available."
- Add header note on FactivaConfig page — something like "Factiva is the sole news collection source. Configure query parameters below."
- Keep current subtle display for inferred industry codes — no additional warning styling needed
- Add help text for date_range_hours — explain what it controls, e.g., "How far back to look for articles each run. 48 hours provides overlap to catch late-indexed articles."

### Historical Data Presentation
- Fresh DB planned — no need to preserve backwards-compatible Apify/RSS rendering
- Remove all Apify/RSS rendering logic from templates — dashboard, search results, email templates, brief templates only have Factiva badge path
- Change news_article model default from 'Apify/RSS' to 'Factiva'
- Update startup migration SQL default from 'Apify/RSS' to 'Factiva'

### Claude's Discretion
- News API card label wording (keep "News (Factiva)" vs simplify to "Factiva")
- Exact wording of FactivaConfig header note and date_range_hours help text
- How to handle source type in DB model vs UI (DB column preservation for schema stability)

</decisions>

<specifics>
## Specific Ideas

- Warning tone for disabled Factiva state — admin must understand disabling means zero collection
- FactivaConfig should feel like THE collection control center, not one of many
- User is creating a fresh DB, so no historical data migration concerns

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-dashboard-config-updates*
*Context gathered: 2026-02-26*
