# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-06)

**Core value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.
**Current focus:** Phase 3 - Advanced Classification Pipeline

## Current Position

Phase: 3 of 8 (Advanced Classification Pipeline)
Plan: 2 of 5 complete
Status: In progress
Last activity: 2026-02-07 — Completed 03-02-PLAN.md (classifier prompt expansion)

Progress: [█████░░░░░] 30% (Phase 1: 5/5, Phase 2: 6/6, Phase 3: 2/5)

## Performance Metrics

**Velocity:**
- Total plans completed: 13
- Average duration: 3.3 minutes
- Total execution time: 0.75 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 5/5 | 26 min | 5.2 min |
| 02 | 6/6 | 17 min | 2.8 min |
| 03 | 2/5 | 4.2 min | 2.1 min |

**Recent Trend:**
- Last 5 plans: 02-05 (1min), 02-06 (3min), 03-01 (2.5min), 03-02 (1.7min)
- Trend: Very fast execution for data/schema/prompt implementations
- **Phase 1 complete**: Vertical slice operational
- **Phase 2 complete**: 20 sources, semantic dedup, health monitoring, pipeline integrated
- **Phase 3 started**: Data layer expanded for advanced classification

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
- **Classification deferral** (01-02): Classification fields left NULL until 01-03 - separates collection from classification concerns.
- **Structured outputs** (01-03): Using Azure OpenAI beta.chat.completions.parse() with Pydantic schema for guaranteed schema compliance.
- **Multi-role strategy** (01-03): Generous role assignment with 40-60% multi-role target. Skip-on-error pattern for batch resilience.
- **JSON roles parsing** (01-04): Reporter service converts JSON string from database to Python list before passing to template - keeps filtering logic clean.
- **CSS custom properties** (01-04): Using CSS variables for Marsh branding enables easy theming and consistent color palette across template.
- **Premailer CSS inlining** (01-04): Transforms CSS for email compatibility (Phase 5) while maintaining modern browser support for Phase 1.
- **Pipeline orchestrator pattern** (01-05): Collector creates Run internally (Option A) - simpler for Phase 1, orchestrator queries latest Run for coordination.
- **Admin UI delivery** (01-05): Opens report in new window for browser-based viewing before email integration in Phase 5.
- **Custom response headers** (01-05): X-MDInsights-* headers enable client-side run tracking without additional API calls.
- **CSS selector fallbacks** (02-01): Multiple fallback selectors per field (containers, titles, descriptions) for robust extraction across site structure changes.
- **web-scraper for all sources** (02-01): Using web-scraper actor for all 4 new sources (Insurance Journal, Business Insurance, Artemis, Lloyd's List) - sufficient for static content, can migrate to playwright-scraper if dynamic content needed.
- **20-article limit** (02-01): Hard limit of 20 articles per source for Phase 2 cost control and consistent dataset size.
- **Generic RSS source** (02-02): Single RSSSource class handles all RSS/Atom feeds - eliminates need for source-specific scrapers for RSS-based publishers.
- **Malformed feed tolerance** (02-02): System processes feeds with bozo flag if entries exist - maximizes data collection from imperfect feeds.
- **Date fallback chain** (02-02): Falls back through published_parsed → updated_parsed → created_parsed → current time for robust date extraction.
- **Type-based RSS routing** (02-03): Check source_type=RSS to route all RSS sources generically rather than name-based map - eliminates need for RSS source-specific scrapers.
- **20 source seed data** (02-03): Seed all 18 target sources plus 2 disabled sources (Moody's, Fitch) for future activation - complete source registry ready for Phase 2 production.
- **Source name passed to RSSSource** (02-03): Pass source.name to RSSSource constructor for proper article attribution - articles from RSS sources get correct source_name value.
- **Sentence transformers over MinHash** (02-04): Direct cosine similarity with all-MiniLM-L6-v2 model provides superior semantic understanding compared to MinHash/LSH - worth 80MB model size for daily batches.
- **Conservative 0.85 similarity threshold** (02-04): Reduces false positives in duplicate detection, can be tuned based on customer feedback and production metrics.
- **Lazy model loading** (02-04): SentenceTransformer model loaded on first deduplicate() call avoids 1-2s startup penalty when deduplicator imported but not used.
- **Union-Find for transitive duplicates** (02-04): Handles A→B, B→C transitive relationships correctly - all three grouped as one duplicate even if A not directly similar to C.
- **Earliest article as keeper** (02-04): Original publication date preserved, proper attribution to first source that reported the story.
- **Comma-separated source merging** (02-04): Simple implementation matching existing source_name VARCHAR column - may evolve to JSON array if source metadata needed later.
- **Three-phase collection** (02-06): Collect all → deduplicate → store (instead of per-source storage) enables cross-source duplicate detection with minimal memory footprint.
- **Additive health monitoring** (02-06): Health check failures log warnings but never block pipeline - core workflow reliability preserved while adding observability.
- **Phase 3 nullable fields** (03-01): All Phase 3 classification fields (entities, impact_level, category, region, business_line) are nullable for backward compatibility with existing Phase 1/2 articles.
- **Impact vs priority distinction** (03-01): Separate impact_level (market magnitude) from priority (Marsh urgency) - different dimensions enable nuanced classification.
- **SQLAlchemy 2.0 connection pattern** (03-01): Use "with engine.connect() as conn" instead of engine.execute() - SQLAlchemy 2.0 compatibility.
- **Entity extraction structure** (03-01): JSON array in entities column with {name, type, context} objects - flexible storage for variable-length entity lists.
- **Categorical Literal types** (03-01): Strict Literal types for impact_level, category, region, business_line - Azure OpenAI structured outputs require enum constraints.
- **Comprehensive prompt design** (03-02): Appended 5 new guidance sections to existing CLASSIFICATION_PROMPT - single coherent prompt delivers all 9 dimensions in one GPT-4o call instead of multi-pass classification.
- **Pydantic v2 model_dump** (03-02): Use model_dump() for entities serialization instead of deprecated dict() method - future-proof Pydantic v2 compatibility.

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1:**
- Requires Azure AD app registration for Azure OpenAI and Microsoft Graph API access
- Requires Apify account setup and actor configuration
- Requires prototype HTML from RefChyt/prototype_daily_intelligence_brief.html as reference

**Phase 2:**
- Need to identify and validate all 18+ target sources from prototype
- Apify rate limiting and cost implications need validation during scale-up

**Phase 4:**
- Report format clarification: REPT-01 specifies single HTML with tabs, but PROJECT.md mentions "separate emails per role" — roadmap follows REPT-01 (tabbed brief, single email)

## Session Continuity

Last session: 2026-02-07
Stopped at: Completed 03-02-PLAN.md (classifier prompt expansion, 1.7 min)
Resume file: None
Next: Execute 03-03 (classification testing and validation)
