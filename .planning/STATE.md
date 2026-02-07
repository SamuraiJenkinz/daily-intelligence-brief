# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-06)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** Phase 4 - Intelligence Report Generation

## Current Position

Phase: 4 of 8 IN PROGRESS (Intelligence Report Generation)
Plan: 5/10 complete
Status: Phase 4 in progress — Plans 01-05 complete (role filtering, exec summaries, sector heatmap, entity tracker, what to watch)
Last activity: 2026-02-07 — Completed 04-05-PLAN.md (what to watch forward-looking analysis)

Progress: [██████░░░░] 47.5% (Phase 1: 5/5, Phase 2: 6/6, Phase 3: 3/3, Phase 4: 5/10)

## Performance Metrics

**Velocity:**
- Total plans completed: 19
- Average duration: 2.8 minutes
- Total execution time: 0.91 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 5/5 | 26 min | 5.2 min |
| 02 | 6/6 | 17 min | 2.8 min |
| 03 | 3/3 | 5.5 min | 1.8 min |
| 04 | 5/10 | 13.5 min | 2.7 min |

**Recent Trend:**
- Last 5 plans: 04-01 (4min), 04-02 (parallel), 04-03 (5s), 04-04 (3min), 04-05 (1.5min)
- Trend: Phase 4 Wave 2 continuing with autonomous execution
- **Phase 1 complete**: Vertical slice operational
- **Phase 2 complete**: 20 sources, semantic dedup, health monitoring, pipeline integrated
- **Phase 3 complete**: 9-dimension classification (entities, impact, category, region, business line)
- **Phase 4 in progress**: 5/10 plans complete (role filtering, exec summaries, sector heatmap, entity tracker, what to watch)

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

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 4:**
- Report format clarification: REPT-01 specifies single HTML with tabs, but PROJECT.md mentions "separate emails per role" — roadmap follows REPT-01 (tabbed brief, single email)
- Phase 4 has 10 plans — largest phase in the roadmap

## Session Continuity

Last session: 2026-02-07
Stopped at: Phase 4 Plans 01-05 COMPLETE — role filtering, exec summaries (Wave 2 parallel), sector heatmap, entity tracker, what to watch
Resume file: None
Next: Continue Phase 4 - proceed to 04-06 (Market Pulse) or 04-07 (Template Integration)
