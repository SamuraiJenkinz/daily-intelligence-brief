---
phase: 10-factiva-news-collection
plan: 01
subsystem: api
tags: [factiva, httpx, tenacity, structlog, sqlite, sqlalchemy, news-collection]

# Dependency graph
requires:
  - phase: 09-oauth2-token-management
    provides: ApiEvent, ApiEventType, SessionLocal, token_manager pattern (httpx+tenacity+structlog)
  - phase: 01-foundation
    provides: Base, SessionLocal, engine, Settings, NewsArticle ORM model
provides:
  - FactivaCollector class with collect(), _search(), _fetch_article(), _normalize_article()
  - FactivaConfig ORM model (single-row admin config table for Factiva query params)
  - collector_source column on NewsArticle (source attribution: Factiva vs Apify/RSS)
  - Startup migration: ALTERs news_articles, seeds factiva_config default row
affects:
  - 10-02 (pipeline integration wires FactivaCollector into PipelineOrchestrator)
  - 10-03 (admin UI edits FactivaConfig rows via new router)
  - 13-admin-dashboard (reads api_events.api_name="news" for health display)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sync httpx.Client for REST API calls (matches ApifyCollector pattern)"
    - "tenacity retry on TimeoutException+ConnectError only (2 attempts for news calls)"
    - "Isolated SessionLocal() per _record_event() call — swallow DB errors to protect caller"
    - "Startup migration in lifespan() with try/except — failure logs but never blocks startup"
    - "Per-article fetch failure falls back to search snippet (not a hard error)"

key-files:
  created:
    - app/collectors/__init__.py
    - app/collectors/factiva.py
    - app/models/factiva_config.py
  modified:
    - app/models/news_article.py
    - app/models/__init__.py
    - app/main.py

key-decisions:
  - "Sync httpx.Client (not async) — matches existing ApifyCollector.collect_from_sources() pattern"
  - "X-Api-Key only header — Factiva news endpoint does not require JWT Bearer"
  - "collector_source default 'Apify/RSS' — backward-compatible for all pre-Phase-10 articles"
  - "Per-article fetch failures fall back to snippet, not hard errors — pipeline gets max coverage"
  - "MAX_ARTICLES=100 hard cap — one pageSize100 link follow avoids N-article loop overhead"
  - "Migration in lifespan() with try/except — startup never blocked by schema migration failure"

patterns-established:
  - "FactivaCollector._record_event() pattern: isolated SessionLocal, swallow errors, detail[:500]"
  - "Startup migration pattern: PRAGMA table_info() check before ALTER TABLE"
  - "Collector normalization returns collector_source='Factiva' for all new articles"

# Metrics
duration: 37min
completed: 2026-02-18
---

# Phase 10 Plan 01: FactivaCollector Foundation Summary

**FactivaCollector with X-Api-Key auth, search + per-article body fetch, snippet fallback, and FactivaConfig single-row admin config table with startup migration**

## Performance

- **Duration:** 37 min
- **Started:** 2026-02-18T18:13:37Z
- **Completed:** 2026-02-18T18:51:21Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- FactivaCollector class (app/collectors/factiva.py, 300+ lines) following httpx+tenacity+structlog patterns from token_manager.py
- FactivaConfig ORM model with industry_codes, company_codes, keywords, page_size, enabled, audit fields
- collector_source column added to NewsArticle with backward-compatible "Apify/RSS" default
- Startup migration in lifespan() that safely ALTERs existing news_articles table and seeds default factiva_config row (id=1)

## Task Commits

Each task was committed atomically:

1. **Task 1: Database schema — FactivaConfig model, collector_source column, startup migration** - `0dcfb76` (feat)
2. **Task 2: FactivaCollector class — API client with search, article fetch, and normalization** - `c289c15` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/collectors/__init__.py` - Package init, exports FactivaCollector
- `app/collectors/factiva.py` - FactivaCollector: collect(), _search(), _search_by_url(), _fetch_article(), _normalize_article(), _record_event(), _build_headers()
- `app/models/factiva_config.py` - FactivaConfig ORM model (single-row factiva_config table)
- `app/models/news_article.py` - Added collector_source Column(String(20), default="Apify/RSS")
- `app/models/__init__.py` - Added FactivaConfig import and to __all__
- `app/main.py` - Added factiva_config model import + Phase 10 startup migration block in lifespan()

## Decisions Made

- **Sync httpx.Client** — plan specified sync (matches existing ApifyCollector pattern); no async added
- **X-Api-Key only** — Factiva news/equity endpoints use API key header, not JWT Bearer (confirmed from config.py is_mmc_api_key_configured())
- **collector_source default "Apify/RSS"** — backward-compatible: all pre-Phase-10 articles stay attributed correctly without backfill
- **Per-article fetch failures fall back to snippet** — individual article body unavailability (4xx, timeout) does not drop the article; snippet from search result is used instead
- **MAX_ARTICLES=100 hard cap with pageSize100 link follow** — avoids N-API-call pagination loop; one extra call gets maximum coverage
- **Migration failure does not block startup** — try/except around entire migration block; logs error but app starts normally

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required for this plan.
FactivaCollector.is_configured() returns False until mmc_api_base_url and mmc_api_key are set in .env.

## Next Phase Readiness

- Plan 10-02 (pipeline integration): FactivaCollector is ready to be wired into PipelineOrchestrator as primary news source with Apify fallback
- Plan 10-03 (admin UI): FactivaConfig model and default row exist; router can add GET/POST endpoints to read/update config
- All existing pipeline code unaffected: collector_source column is nullable with default "Apify/RSS"

---
*Phase: 10-factiva-news-collection*
*Completed: 2026-02-18*
