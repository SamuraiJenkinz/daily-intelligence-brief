---
phase: 02-news-collection-scale
plan: 03
subsystem: data-collection
tags: [source-registry, rss-integration, multi-source, data-seeding]

requires:
  - 02-01-multi-source-scrapers
  - 02-02-rss-source-implementation

provides:
  - RSS source routing in collector
  - RSSSource module export
  - Complete 20-source seed script
  - Database-driven source management

affects:
  - 02-04-error-handling-validation
  - 02-05-source-health-monitoring
  - 02-06-production-deployment

tech-stack:
  added: []
  patterns:
    - Source type-based routing
    - Generic RSS handler for all RSS sources
    - Idempotent database seeding
    - Source registry pattern

key-files:
  created:
    - scripts/seed_sources.py (complete 20-source version)
  modified:
    - app/services/sources/__init__.py
    - app/services/collector.py

decisions:
  - decision: Type-based RSS routing
    rationale: Check source_type=RSS to route all RSS sources generically rather than name-based map
    impact: Eliminates need for RSS source-specific scrapers
    alternatives: Name-based map (rejected - would require map entry for every RSS source)
  - decision: 20 source seed data
    rationale: Seed all 18 target sources plus 2 disabled sources for future activation
    impact: Complete source registry ready for Phase 2 production
    alternatives: Incremental seeding (rejected - better to have complete registry upfront)
  - decision: Source name passed to RSSSource
    rationale: Pass source.name to RSSSource constructor for proper article attribution
    impact: Articles from RSS sources get correct source_name value
    alternatives: Use feed title (rejected - inconsistent with database source names)

metrics:
  duration: 2 minutes
  completed: 2026-02-06
---

# Phase 02 Plan 03: Source Registry and RSS Integration Summary

**One-liner:** Unified source routing supporting both Apify and RSS sources via SourceType enum, plus complete 20-source seed script.

## What Was Built

### RSS Source Integration
- **RSSSource Export**: Added RSSSource to `app/services/sources/__init__.py` exports
- **Collector Routing**: Modified `_get_source_scraper()` to route via `source.source_type`:
  - RSS sources: `if source.source_type == SourceType.RSS` → RSSSource
  - Apify sources: Name-based map lookup
  - Pass `source_name=source.name` to RSSSource for attribution

### Complete Source Seed Script
Created `scripts/seed_sources.py` with 20 sources:

**Core Apify Sources (5 with custom scrapers):**
- Reinsurance News, Insurance Journal, Business Insurance, Artemis, Lloyd's List

**RSS Sources (4):**
- Bloomberg, Reuters, S&P Global, AM Best

**Additional Apify Sources (11):**
- Insurance Business UK, The Insurer, GlobeNewsWire, Verisk, APCIA, Gallagher Re, Mapfre, Research and Markets, KCC

**Disabled Sources (2):**
- Moody's, Fitch Ratings (enabled=False for future activation)

### Key Features
- **Idempotent**: Script checks existing records before insert (0 duplicates on re-run)
- **Type-based routing**: Any source with `source_type=RSS` uses RSSSource automatically
- **Source attribution**: RSS articles get correct `source_name` from database
- **Clean imports**: All source classes import cleanly without circular dependencies

## Files Changed

### Modified Files
1. **app/services/sources/__init__.py**
   - Added RSSSource import and export
   - All 6 source classes now exported (base + 5 Apify + RSS)

2. **app/services/collector.py**
   - Imported RSSSource
   - Rewrote `_get_source_scraper()` to check `source.source_type` first
   - RSS sources routed generically via RSSSource class
   - Apify sources routed via name-based map
   - Added source_name parameter to RSSSource constructor

### Created Files
1. **scripts/seed_sources.py** (complete rewrite)
   - 20 source definitions (5 Apify + 4 RSS + 11 additional + 2 disabled)
   - Idempotent seeding logic
   - Summary output (created/skipped counts)

## Technical Details

### Source Routing Logic
```python
def _get_source_scraper(self, source: Source) -> NewsSource:
    # RSS sources use generic handler
    if source.source_type == SourceType.RSS:
        return RSSSource(self.apify_client, source.url, source_name=source.name)

    # Apify sources use site-specific scrapers
    apify_source_map = {
        "Reinsurance News": ReinsuranceNewsSource,
        "Insurance Journal": InsuranceJournalSource,
        "Business Insurance": BusinessInsuranceSource,
        "Artemis": ArtemisSource,
        "Lloyd's List": LloydsListSource,
    }

    scraper_class = apify_source_map.get(source.name)
    if not scraper_class:
        self.logger.warning("no_scraper_for_source", ...)
        return None

    return scraper_class(self.apify_client, source.url)
```

### Seed Script Pattern
- Uses `Base.metadata.create_all(bind=engine)` to ensure tables exist
- Checks `db.query(Source).filter(Source.name == source_data["name"]).first()`
- Only inserts if source doesn't exist
- Tracks created/skipped counts for summary output

## Testing Results

### Verification Tests Passed
- [x] All source imports resolve cleanly
- [x] Collector imports RSSSource without errors
- [x] Seed script creates 20 source records
- [x] 4 RSS sources, 16 Apify sources in database
- [x] 18 enabled, 2 disabled sources
- [x] Idempotent: Re-run creates 0 duplicates (20 skipped)

### Database Verification
```
Total sources: 20
  Reinsurance News               (apify) enabled=True
  Insurance Journal              (apify) enabled=True
  Business Insurance             (apify) enabled=True
  Artemis                        (apify) enabled=True
  Lloyd's List                   (apify) enabled=True
  Bloomberg                      (rss  ) enabled=True
  Reuters                        (rss  ) enabled=True
  S&P Global                     (rss  ) enabled=True
  AM Best                        (rss  ) enabled=True
  ... (11 more sources)
  Moody's                        (apify) enabled=False
  Fitch Ratings                  (apify) enabled=False
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Unicode encoding in seed script print statements**
- **Found during:** Task 2 verification
- **Issue:** Emoji characters (🌱, ✅, ❌) caused UnicodeEncodeError on Windows console
- **Fix:** Removed emoji characters from print statements
- **Files modified:** scripts/seed_sources.py
- **Commit:** bb1f911

## Integration Points

### Upstream Dependencies
- **02-01**: Provides Apify source classes and base NewsSource interface
- **02-02**: Provides RSSSource implementation

### Downstream Integrations
- **02-04**: Error handling will leverage source_type routing
- **02-05**: Health monitoring will track RSS vs Apify sources separately
- **02-06**: Production deployment uses complete 20-source registry

## Next Phase Readiness

### What's Ready
- Complete source registry (20 sources)
- Type-based routing for both Apify and RSS
- Idempotent seeding script for database initialization
- Clean module exports and imports

### What's Next (02-04)
- Per-source error handling and retry logic
- Scraping validation rules
- Data quality checks
- Failure recovery patterns

### Remaining Concerns
- RSS source URLs not yet validated (may need adjustment during testing)
- Additional Apify sources don't have custom scrapers yet (will use generic web-scraper)
- Disabled sources (Moody's, Fitch) need scraper development before enablement

## Performance Metrics

- **Execution Time:** 2 minutes
- **Files Modified:** 2
- **Files Created:** 1 (complete rewrite)
- **Lines Changed:** +158 -10
- **Sources Seeded:** 20 (18 enabled, 2 disabled)

## Commits

- 38a9c69: feat(02-03): add RSS source routing to collector
- bb1f911: feat(02-03): expand seed script to 20 sources (5 Apify + 4 RSS + 11 additional)
