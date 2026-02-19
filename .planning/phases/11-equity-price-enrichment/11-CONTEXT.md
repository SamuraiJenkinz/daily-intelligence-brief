# Phase 11: Equity Price Enrichment - Context

**Gathered:** 2026-02-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Articles about tracked public companies appear in the brief with current equity price and daily change displayed inline alongside the story. Admin configures entity-to-ticker mappings. Pipeline fetches prices after classification, before report generation. Brief generates normally when price data is unavailable.

</domain>

<decisions>
## Implementation Decisions

### Unmapped entity handling
- Silent skip in the brief — articles with unmapped companies appear normally, no equity data shown, no visible indicator of a gap
- Admin manages ticker mappings proactively — no automatic surfacing of unmapped entities in the dashboard
- Lookup failures for mapped entities treated identically to unmapped — brief shows the story without equity fields, failure logged
- Consistent principle: the brief never degrades because of equity data gaps

### Claude's Discretion
- Inline equity display layout and styling (how price data looks alongside stories)
- Entity-to-ticker mapping admin UI approach and fields
- Price data scope (which data points to display, freshness handling)
- Logging dedup strategy for unmapped entities across articles in a single run
- Failure logging granularity and format (consistent with existing ApiEvent patterns)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for inline display, mapping admin UI, and price data presentation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-equity-price-enrichment*
*Context gathered: 2026-02-18*
