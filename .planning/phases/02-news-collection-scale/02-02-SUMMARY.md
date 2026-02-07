---
phase: 02
plan: 02
subsystem: news-collection
tags: [rss, feedparser, multi-source, scraping]
requires: [01-02-collector-service]
provides: [generic-rss-scraper, feedparser-dependency]
affects: [02-03-source-registry, 02-04-multi-source-expansion]
tech-stack:
  added: [feedparser==6.0.12]
  patterns: [rss-feed-parsing, html-stripping, date-normalization, error-recovery]
key-files:
  created:
    - app/services/sources/rss_source.py
  modified:
    - requirements.txt
decisions:
  - id: RSS-01
    what: Generic RSSSource for all RSS/Atom feeds
    why: RSS feeds are stable and standardized - one reusable class handles all RSS-based sources
    impact: Eliminates need for source-specific scraper implementations for RSS feeds
  - id: RSS-02
    what: Malformed feed tolerance (bozo flag)
    why: Some feeds have minor issues but still contain valid entries
    impact: System continues processing if entries exist despite malformed feed flag
  - id: RSS-03
    what: Date fallback chain (published → updated → created → current)
    why: Different feeds use different date fields
    impact: Maximizes successful date extraction across diverse RSS implementations
  - id: RSS-04
    what: Simple regex HTML stripping
    why: Feed descriptions often contain HTML tags that should be removed for clean display
    impact: Descriptions are clean text without HTML markup
metrics:
  duration: 1.4 minutes
  completed: 2026-02-06
---

# Phase 02 Plan 02: Generic RSS Feed Source Summary

**One-liner:** Generic RSSSource class using feedparser for any standard RSS/Atom feed with malformed feed tolerance and robust date extraction.

## What Was Built

Created a reusable RSS feed scraper that works with any standard RSS 2.0 or Atom feed. The generic implementation eliminates the need for source-specific scrapers for RSS-based publishers (Bloomberg, Reuters, S&P Global, Moody's, Fitch, AM Best).

### Key Components

1. **RSSSource Class** (`app/services/sources/rss_source.py`)
   - Extends NewsSource ABC for polymorphic multi-source support
   - Accepts `source_url` (feed URL) and optional `source_name` parameter
   - Parses feeds using feedparser.parse()
   - Normalizes entries to standard article schema
   - Handles malformed feeds gracefully (logs warning, continues if entries exist)
   - Strips HTML from descriptions using simple regex
   - Limits to first 20 entries per feed
   - Returns empty list on failure without halting pipeline

2. **Date Extraction**
   - Fallback chain: published_parsed → updated_parsed → created_parsed → current time
   - Converts time.struct_time to datetime object
   - Never returns None (guarantees datetime value)

3. **Error Handling**
   - Bozo flag detection with warning log
   - Continues processing if entries exist despite malformed flag
   - Try/except wrapper returns empty list on critical failure
   - Structured logging with source="rss" and url binding

4. **feedparser Dependency**
   - Added feedparser==6.0.12 to requirements.txt
   - Installed and verified functional

## Deviations from Plan

None - plan executed exactly as written.

## Technical Decisions Made

**Generic vs. Source-Specific:**
- Chose single reusable class over multiple source-specific implementations
- RSS/Atom standards are consistent enough for one implementation
- Source-specific behavior handled via constructor parameters

**HTML Stripping:**
- Simple regex `re.sub(r'<[^>]+>', '', text)` for tag removal
- Adequate for feed descriptions (not user input, so XSS not a concern)
- Could enhance with html.parser or BeautifulSoup if needed

**Date Normalization:**
- feedparser provides parsed time structs, avoiding string parsing complexity
- Fallback chain maximizes successful date extraction
- Current time fallback ensures published_at is never None

## Testing & Validation

All verification checks passed:
- RSSSource class exists and extends NewsSource
- RSSSource.scrape() uses feedparser.parse()
- feedparser==6.0.12 installed and functional
- All imports resolve cleanly

## Integration Points

**Upstream Dependencies:**
- Extends NewsSource ABC from `app/services/sources/base.py`
- Uses structlog for consistent logging

**Downstream Usage:**
- Ready for source registry (02-03)
- Enables multi-source expansion (02-04) for RSS-based publishers

## Next Phase Readiness

**Ready for:**
- 02-03: Source registry system (RSSSource will be registered)
- 02-04: Multi-source expansion (instantiate RSSSource for each RSS feed)

**Blockers:**
None.

**Recommendations:**
- Test with actual RSS feeds in 02-04 to validate parser robustness
- Consider adding user-agent header if feeds block feedparser's default UA
- Monitor for feeds requiring authentication or special headers

## Performance Characteristics

**Efficiency:**
- feedparser is lightweight and efficient
- Limiting to 20 entries prevents excessive processing
- HTML stripping is O(n) with low overhead

**Resource Usage:**
- Minimal memory footprint (processes entries sequentially)
- Network bound (feed fetch time dominates)
- No apify_client usage (parameter required by ABC but unused)

## Commits

| Hash | Message |
|------|---------|
| 0666c3e | feat(02-02): create generic RSSSource class |
| 7f7711e | chore(02-02): add feedparser dependency |

## Artifacts Delivered

- `app/services/sources/rss_source.py` (175 lines) - Generic RSS/Atom feed scraper
- `requirements.txt` - Added feedparser==6.0.12 dependency

Total: 1 new file, 1 modified file, 2 commits
