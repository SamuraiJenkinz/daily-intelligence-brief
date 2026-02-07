# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-06)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** Phase 5 - Automated Delivery System

## Current Position

Phase: 5 of 8 IN PROGRESS (Automated Delivery System)
Plan: 1/2 complete
Status: Wave 1 (05-01) complete — Email service infrastructure ready
Last activity: 2026-02-07 — Completed 05-01-PLAN.md
Verified: 2026-02-07 — Phase 4 VERIFIED (10/10 must-haves passed)

Progress: [█████▓░░░░] 56.4% (Phase 1: 5/5, Phase 2: 6/6, Phase 3: 3/3, Phase 4: 7/7, Phase 5: 1/2)

## Performance Metrics

**Velocity:**
- Total plans completed: 22
- Average duration: 2.9 minutes
- Total execution time: 1.07 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 5/5 | 26 min | 5.2 min |
| 02 | 6/6 | 17 min | 2.8 min |
| 03 | 3/3 | 5.5 min | 1.8 min |
| 04 | 7/7 | 24 min | 3.4 min |
| 05 | 1/2 | 2.4 min | 2.4 min |

**Recent Trend:**
- Last 5 plans: 04-04 (3min), 04-05 (1.5min), 04-06 (3min), 04-07 (7.5min), 05-01 (2.4min)
- Trend: Consistent fast execution, Phase 5 started strong
- **Phase 1 complete**: Vertical slice operational
- **Phase 2 complete**: 20 sources, semantic dedup, health monitoring, pipeline integrated
- **Phase 3 complete**: 9-dimension classification (entities, impact, category, region, business line)
- **Phase 4 complete**: 7/7 plans complete (role filtering, exec summaries, aggregation, template integration)
- **Phase 5 in progress**: 1/2 plans complete (email service infrastructure)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Tabs implementation**: Phase 1 uses JavaScript tabs for browser viewing (served via FastAPI endpoint). Phase 5 will handle email delivery separately (email clients don't support JS). This is the correct approach — no premature email optimization.
- **Test source**: Reinsurance News selected for Phase 1 vertical slice (clean structured data, reliable daily updates).
- **Multi-role article schema** (01-01): Using JSON text column for roles array instead of M2M table. Simpler for Phase 1, may need migration later.
- **Port 8001** (01-01): MDInsights runs on 8001 to avoid conflict with BrasilIntel on 8000 during parallel development.
- **Source interface pattern** (01-02): Abstract NewsSource base class enables polymorphic multi-source expansion in Phase 2.
- **Error handling strategy** (01-02): Individual source failures return empty list rather than halting collection - enables fault tolerance.
- **Structured outputs** (01-03): Using Azure OpenAI beta.chat.completions.parse() with Pydantic schema for guaranteed schema compliance.
- **Multi-role strategy** (01-03): Generous role assignment with 40-60% multi-role target. Skip-on-error pattern for batch resilience.
- **JSON roles parsing** (01-04): Reporter service converts JSON string from database to Python list before passing to template.
- **Pipeline orchestrator pattern** (01-05): Collector creates Run internally, orchestrator queries latest Run for coordination.
- **Generic RSS source** (02-02): Single RSSSource class handles all RSS/Atom feeds.
- **Sentence transformers over MinHash** (02-04): Direct cosine similarity with all-MiniLM-L6-v2 for semantic dedup.
- **Three-phase collection** (02-06): Collect all → deduplicate → store enables cross-source dedup.
- **Phase 3 nullable fields** (03-01): All Phase 3 fields nullable for backward compatibility.
- **Impact vs priority distinction** (03-01): Separate impact_level (market magnitude) from priority (Marsh urgency).
- **Entity extraction structure** (03-01): JSON array in entities column with {name, type, context} objects.
- **Categorical Literal types** (03-01): Strict Literal types for structured outputs enforcement.
- **Comprehensive prompt design** (03-02): Single 5379-char prompt delivers all 9 dimensions in one GPT-4o call.
- **Pydantic v2 model_dump** (03-02): Use model_dump() for entities serialization.
- **Entity round-trip validation** (03-03): Explicit json.loads + structure checks prove serialization integrity.
- **Static method for filtering** (04-01): filter_articles_by_role as static method for stateless filtering logic.
- **Edition stats in reporter** (04-01): Reporter service computes edition_stats (source_count, article_count) from articles.
- **Unified brief signature** (04-01): Removed target_role parameter — unified brief contains all roles via tabs.
- **Temperature 0.4 for summaries** (04-02): Balance consistency with variety for executive summaries (vs 0.3 for classification).
- **Top 20 articles for context** (04-02): Provides rich AI context without exceeding token budgets, priority-sorted.
- **Three-tier fallback** (04-02): Graceful degradation for empty articles, unconfigured Azure, or generation errors.
- **defaultdict for aggregation** (04-03): Use defaultdict for O(1) grouping by business_line in sector heatmap.
- **Simple majority signal** (04-03): Determine directional signal by comparing positive vs negative counts (neutral ignored).
- **Entity count tracking** (04-04): defaultdict with count/type composite for single-pass entity mention tracking.
- **Defensive entity parsing** (04-04): Handle None, JSON strings, and malformed data for robust entity aggregation.
- **Dual filtering criteria** (04-05): What to Watch filters by priority (Critical/High) OR category (Market Trends) for comprehensive coverage.
- **Temperature 0.5 for what-to-watch** (04-05): Higher than summaries (0.4) to encourage forward-looking creativity while maintaining consistency.
- **Six predefined market segments** (04-06): P&C Market, Reinsurance, Specialty Lines, Life & Health, M&A Activity, Regulatory for market pulse bar.
- **Sentiment score thresholds** (04-06): Strong (>0.3), Stable (>0), Mixed (>-0.3), Softening (else) for four-level classification.
- **P&C Market combination** (04-06): Combines Property and Casualty business lines into single segment matching industry terminology.
- **Reporter calls all aggregators** (04-07): Reporter service calls all three aggregation methods (sector_heatmap, entity_tracker, market_pulse) and passes to template.
- **Edition stats expansion** (04-07): Edition stats now includes entity_count and signal_count for footer display.
- **Template dict access pattern** (04-07): Use bracket notation for what_to_watch dict access in Jinja2 to avoid built-in method conflicts.
- **Kevin Taylor dual attribution** (04-07): Kevin Taylor badge appears in header AND footer for maximum attribution visibility.
- **CONFIDENTIAL banner placement** (04-07): Banner positioned above header for maximum visibility and compliance.
- **Market pulse bar positioning** (04-07): Between header and container (not inside tabs) for universal context.
- **Cross-tab sections architecture** (04-07): Heatmap, entity tracker, what to watch positioned after all tab content for cross-role visibility.
- **Impact chip ordering** (04-07): Sentiment, impact_level, region, business_line, entities (top 3) provides logical visual hierarchy.
- **Prototype CSS integration** (04-07): Wholesale CSS integration from prototype faster and more consistent than piecemeal implementation.
- **Structlog for email service** (05-01): Use structlog (not stdlib logging) to maintain consistency with MDInsights logging patterns.
- **Microsoft field prefix** (05-01): Config fields use microsoft_* prefix (not azure_*) matching existing MDInsights convention.
- **Graceful Graph fallback** (05-01): GraphEmailService returns credential=None when not configured, allowing dev/test without credentials.

### Pending Todos

None yet.

### Blockers/Concerns

None - Phase 5 Wave 1 complete, ready for Wave 2 (pipeline delivery integration)

## Session Continuity

Last session: 2026-02-07
Stopped at: Completed 05-01-PLAN.md — Email service infrastructure ready
Resume file: None
Next: Execute 05-02-PLAN.md — Pipeline delivery integration (send role-specific briefs)
