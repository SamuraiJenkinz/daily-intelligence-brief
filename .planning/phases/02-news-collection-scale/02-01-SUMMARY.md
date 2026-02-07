---
phase: 02-news-collection-scale
plan: 01
subsystem: news-collection
tags: [apify, web-scraping, multi-source, fault-tolerance]

requires:
  - phase: 01
    plan: 02
    capability: "Polymorphic NewsSource pattern"
  - phase: 01
    plan: 02
    capability: "Apify web-scraper integration"

provides:
  - "5-source collection capability (1→5 scale-up)"
  - "Insurance Journal scraper"
  - "Business Insurance scraper"
  - "Artemis scraper"
  - "Lloyd's List scraper"

affects:
  - phase: 02
    plan: 02
    reason: "Need source database records for 4 new sources"
  - phase: 02
    plan: 03
    reason: "Classification must handle articles from all 5 sources"

tech-stack:
  added: []
  patterns:
    - "CSS selector fallback chains for robust scraping"
    - "Per-source logging with structlog binding"

key-files:
  created:
    - "app/services/sources/insurance_journal.py"
    - "app/services/sources/business_insurance.py"
    - "app/services/sources/artemis.py"
    - "app/services/sources/lloyds_list.py"
  modified:
    - "app/services/sources/__init__.py"
    - "app/services/collector.py"

decisions:
  - "Multiple CSS selector fallbacks per field for robust extraction across site structure changes"
  - "web-scraper actor sufficient for all 4 sources (playwright-scraper deferred for complexity)"
  - "20-article limit per source for Phase 2 testing and cost control"

metrics:
  duration: 2 minutes
  completed: 2026-02-07
---

# Phase 2 Plan 1: Multi-Source Scraper Implementation Summary

**One-liner:** Added 4 Apify web-scraper implementations (Insurance Journal, Business Insurance, Artemis, Lloyd's List) following ReinsuranceNewsSource pattern, expanding collection from 1→5 sources.

## What Was Built

Created 4 new source scraper files implementing the NewsSource abstract interface, each using Apify's web-scraper actor with site-specific CSS selectors and fallback chains.

**Insurance Journal** (`insurance_journal.py`):
- CSS selectors: `article, .article-item, .news-item` containers; `h2 a, h3 a, .article-title a` titles
- Multiple fallback selectors for robust extraction
- Returns standardized article dicts with source_name="Insurance Journal"

**Business Insurance** (`business_insurance.py`):
- CSS selectors: `article, .article-card, .story` containers; `h2 a, h3 a, .headline a` titles
- Fallbacks: `.teaser, .deck, .excerpt, p` for descriptions
- Returns standardized article dicts with source_name="Business Insurance"

**Artemis** (`artemis.py`):
- CSS selectors: `article, .post, .entry` containers (same as ReinsuranceNewsSource)
- Fallbacks: `.entry-content, .excerpt, p` for descriptions
- Returns standardized article dicts with source_name="Artemis"

**Lloyd's List** (`lloyds_list.py`):
- CSS selectors: `article, .article-card, .story-card` containers
- Fallbacks: `.article-summary, .teaser, p` for descriptions
- Returns standardized article dicts with source_name="Lloyd's List"

**Integration:**
- Expanded `app/services/sources/__init__.py` to export all 4 new classes
- Updated `collector.py` source_map from 1→5 sources
- Maintained polymorphic NewsSource pattern for clean extension

## Technical Implementation

### Pattern Consistency

All 4 scrapers follow exact ReinsuranceNewsSource structure:
- Extend `NewsSource` ABC from `base.py`
- Implement `scrape()` → `List[Dict[str, Any]]`
- Use Apify web-scraper actor with pageFunction
- Include `_normalize_article()` for schema compliance
- Return empty list on failure (fault tolerance)
- Use structlog with source-specific binding

### CSS Selector Strategy

**Fallback chains** for each field:
- **Containers:** 3 fallback selectors per source (e.g., `article, .article-item, .news-item`)
- **Titles:** 3-4 fallback selectors (e.g., `h2 a, h3 a, .article-title a, h2`)
- **Descriptions:** 3-4 fallback selectors (e.g., `.article-excerpt, .summary, p`)

Fallbacks enable resilience against:
- Site redesigns
- A/B testing variations
- Different article types on same site

### Article Schema

All sources return standardized dicts:
```python
{
    "title": str,              # Required
    "description": str,        # Optional, empty string if missing
    "url": str,                # Absolute URL via new URL(relativeUrl, request.url).href
    "published_at": datetime,  # ISO string from Apify, parsed to datetime
    "source_name": str         # Source identifier for database
}
```

### Fault Tolerance

Each scraper:
- Catches all exceptions in `scrape()`
- Logs error with `exc_info=True` for debugging
- Returns empty list (not exception) to avoid halting pipeline
- Enables collector to continue with remaining sources

## Verification Evidence

**Import verification:**
```bash
python -c "from app.services.sources.insurance_journal import InsuranceJournalSource; print('OK')"
python -c "from app.services.sources.business_insurance import BusinessInsuranceSource; print('OK')"
python -c "from app.services.sources.artemis import ArtemisSource; print('OK')"
python -c "from app.services.sources.lloyds_list import LloydsListSource; print('OK')"
# All: OK
```

**Module exports:**
```bash
python -c "from app.services.sources import InsuranceJournalSource, BusinessInsuranceSource, ArtemisSource, LloydsListSource; print('All imports OK')"
# All imports OK
```

**Collector integration:**
```bash
python -c "from app.services.collector import ApifyCollector; print('Collector imports OK')"
# Collector imports OK
```

All 4 sources successfully extend NewsSource ABC, export cleanly, and integrate into collector source_map.

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

**1. Multiple CSS selector fallbacks per field**
- **Context:** News sites frequently change structure, use A/B testing, and vary article layouts
- **Decision:** Use 3-4 fallback selectors per field (containers, titles, descriptions) rather than single selector
- **Rationale:** Increases scraping resilience without code changes when sites update their HTML
- **Impact:** Higher extraction success rate, fewer empty results from selector mismatches

**2. web-scraper actor for all sources (not playwright-scraper)**
- **Context:** Lloyd's List plan suggested "can switch to playwright-scraper later if needed"
- **Decision:** Use web-scraper for all 4 sources in Phase 2
- **Rationale:** Web-scraper sufficient for static content extraction, simpler configuration, lower cost
- **Future:** Can migrate individual sources to playwright-scraper if dynamic content/JS rendering needed

**3. 20-article limit per source**
- **Context:** Sources vary in article volume (some publish 5/day, others 50+)
- **Decision:** Hard limit of 20 articles per source in pageFunction
- **Rationale:** Cost control during Phase 2 testing, consistent dataset size across sources
- **Future:** Make configurable per-source in database (Phase 3)

## Known Issues & Next Steps

**Phase 2 blockers removed:**
- ✅ Source scraper implementations complete
- ⏭ Next: Plan 02-02 - Create database records for 4 new sources

**Testing notes:**
- CSS selectors are best-effort based on common news site patterns
- Real-world validation requires:
  1. Database source records (Plan 02-02)
  2. Actual Apify execution (Plan 02-03 validation)
  3. Selector adjustment if extraction fails

**Potential issues:**
- Selectors may need tuning after first real scrape
- Some sources may require authentication/paywall handling (defer to Phase 3)
- Rate limiting not yet tested at 5-source scale

## Integration Points

**Upstream dependencies:**
- `app/services/sources/base.py` - NewsSource ABC (Phase 1)
- `app/services/collector.py` - ApifyCollector orchestration (Phase 1)
- Apify web-scraper actor (external service)

**Downstream impacts:**
- **Plan 02-02:** Requires source database records matching these source_names exactly
- **Plan 02-03:** Classification must handle articles from all 5 sources
- **Plan 02-04+:** Any source-specific logic (e.g., URL normalization) may need per-source handling

## Files Changed

**Created (4 files, 596 lines):**
- `app/services/sources/insurance_journal.py` - InsuranceJournalSource class
- `app/services/sources/business_insurance.py` - BusinessInsuranceSource class
- `app/services/sources/artemis.py` - ArtemisSource class
- `app/services/sources/lloyds_list.py` - LloydsListSource class

**Modified (2 files):**
- `app/services/sources/__init__.py` - Added 4 imports and __all__ exports
- `app/services/collector.py` - Expanded source_map from 1→5 entries

## Commits

1. **c5024fc** - `feat(02-01): add 4 Apify source scrapers`
   - Created 4 source scraper files
   - Each extends NewsSource ABC with site-specific CSS selectors
   - Standardized article dict output with fault tolerance

2. **7949e38** - `feat(02-01): integrate 4 sources into collector and exports`
   - Updated __init__.py exports
   - Expanded collector source_map to 5 sources
   - All imports resolve cleanly

## Metrics

- **Duration:** 2 minutes
- **Files created:** 4
- **Files modified:** 2
- **Lines added:** ~620
- **Source scale-up:** 1→5 sources (400% increase)
- **Pattern reuse:** 100% (all follow ReinsuranceNewsSource template)
