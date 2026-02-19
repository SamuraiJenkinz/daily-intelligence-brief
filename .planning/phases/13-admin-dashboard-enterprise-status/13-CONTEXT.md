# Phase 13: Admin Dashboard Enterprise Status - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Surface enterprise API health, credential management, source attribution, and fallback history within the existing admin dashboard. The dashboard already exists (Bootstrap 5, HTMX, Marsh branding, sidebar nav, summary cards, pipeline runs table). This phase adds enterprise visibility — no new standalone apps, no changes to pipeline logic, no new API integrations.

</domain>

<decisions>
## Implementation Decisions

### Status panel design
- Panel sits at the **top of the dashboard**, above the existing summary cards — first thing admins see
- Shows all 4 enterprise APIs: Auth, News (Factiva), Equity, Email
- Detail level per API: **status + last checked time + reason when degraded/offline** (e.g. "Offline — 401 Unauthorized")
- Status updated on each pipeline run (not real-time polling)

### Credential configuration UX
- Lives on a **new dedicated sidebar page** (e.g. "Enterprise Config" or "API Settings") — not inline on dashboard
- Existing credential values are **fully masked** (bullet characters) — admin must clear and re-enter to change
- New sidebar nav entry added alongside existing pages (Dashboard, Sources, Recipients, etc.)
- Credentials saved to database/config — pipeline uses new values on next run

### Source badges in archive
- Per-article source attribution (Factiva vs Apify/RSS) visible in the archive view
- Success criterion says "without additional clicks" — badge must be inline, not behind a drill-down

### Claude's Discretion
- **Status panel visual treatment**: Card-based, traffic light, or other — pick what integrates best with existing dashboard card style
- **Existing summary cards coexistence**: Keep both rows, merge, or restructure — determine cleanest layout integration
- **Credential save flow**: Standard save button vs confirmation dialog — choose appropriate UX for the risk level
- **Credential scope**: Which credentials are dashboard-configurable vs stay in .env — balance convenience and security
- **Source badge placement**: Inline with headline vs source column — fit the existing archive layout
- **Source badge style**: Colored badge vs icon+text — stay consistent with existing design language
- **Source filtering**: Whether a source filter dropdown adds value in the archive
- **Run table enhancement**: Whether per-article source drill-down makes sense from the pipeline runs table
- **Fallback event log**: Full discretion on layout, placement, detail level, and navigation (user did not select this for discussion)

</decisions>

<specifics>
## Specific Ideas

- The pipeline runs table already has a Source column showing Factiva/Apify aggregate counts per run (blue and grey badges) — new source attribution should be visually consistent with this
- Existing dashboard uses Bootstrap 5 cards with subtle shadows, Marsh blue (#0077c8) for Factiva branding and grey for Apify/RSS
- HTMX already loaded — available for dynamic interactions (inline editing, partial refreshes)
- Factiva Config and Equity Tickers pages already exist in the sidebar — new Enterprise Config page should feel like a natural neighbor

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-admin-dashboard-enterprise-status*
*Context gathered: 2026-02-19*
