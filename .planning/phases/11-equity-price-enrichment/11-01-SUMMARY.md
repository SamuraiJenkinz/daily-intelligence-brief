---
phase: 11-equity-price-enrichment
plan: 01
subsystem: api
tags: [sqlalchemy, httpx, tenacity, structlog, fastapi, jinja2, equity, orm]

# Dependency graph
requires:
  - phase: 09-enterprise-auth
    provides: ApiEventType enum (EQUITY_FETCH/EQUITY_FALLBACK) already defined, SessionLocal pattern
  - phase: 10-factiva-news-collection
    provides: FactivaCollector pattern (httpx+tenacity+structlog+_record_event) to model EquityPriceClient on

provides:
  - EquityTicker ORM model (equity_tickers table) with entity_name, ticker, exchange, enabled fields
  - EquityPriceClient API client with get_price(), is_configured(), _build_headers(), _record_event()
  - Admin CRUD UI at /admin/equity for entity-to-ticker mapping management
  - Equity nav link in admin sidebar

affects:
  - 11-02-plan (pipeline enrichment step reads EquityTicker and calls EquityPriceClient.get_price())
  - 11-03-plan (template rendering displays equity price data from enriched articles)

# Tech tracking
tech-stack:
  added: []  # No new dependencies — httpx, tenacity, structlog, sqlalchemy all pre-existing
  patterns:
    - "EquityPriceClient mirrors FactivaCollector exactly: httpx.Client, tenacity @retry, structlog.bind, _record_event isolation"
    - "Hidden input + checkbox pattern for boolean enabled field (same as Factiva admin)"
    - "Flash messages via query params (?success=...&error=...) on redirect after POST"
    - "sqla_func.lower() for case-insensitive uniqueness check"

key-files:
  created:
    - app/models/equity_ticker.py
    - app/collectors/equity.py
    - app/templates/admin/equity.html
    - app/templates/admin/equity_edit.html
  modified:
    - app/models/__init__.py
    - app/main.py
    - app/routers/admin.py
    - app/templates/admin/base.html

key-decisions:
  - "EquityPriceClient returns None on all failures — never raises, callers always safe to ignore"
  - "Multiple field name fallbacks (price/lastPrice/last, change/priceChange/netChange, etc.) — equity API contract not yet confirmed"
  - "BASE_PRICE_PATH = /coreapi/equity-price/v1/price — inferred, validate on deployment machine"
  - "Flash messages via query params on redirect — simplest pattern without session middleware"
  - "equity_edit.html as separate template — cleaner than embedding in equity.html"

patterns-established:
  - "EquityPriceClient._record_event: isolated SessionLocal, api_name='equity', swallow errors"
  - "Admin CRUD: try/finally db.close(), logger.info for all mutations, 303 redirect after POST"

# Metrics
duration: 6min
completed: 2026-02-19
---

# Phase 11 Plan 01: Equity Price Enrichment Foundation Summary

**EquityTicker ORM model (entity_name→ticker mapping table), EquityPriceClient httpx API client with tenacity retry and ApiEvent recording, and full admin CRUD UI at /admin/equity with add/edit/delete/enable-disable**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-19T01:03:42Z
- **Completed:** 2026-02-19T01:09:20Z
- **Tasks:** 2
- **Files modified:** 6 (4 created, 4 modified)

## Accomplishments
- EquityTicker ORM model with unique entity_name, ticker, exchange, enabled fields and audit trail
- EquityPriceClient modeled exactly on FactivaCollector: httpx, tenacity 2-attempt retry, structlog, isolated _record_event()
- Admin equity ticker CRUD at /admin/equity with add/edit/delete and enabled toggle
- equity_tickers table auto-created by Base.metadata.create_all() on app startup
- Multiple response field name fallbacks for equity API (price/lastPrice/last, etc.) since API contract not yet confirmed

## Task Commits

Each task was committed atomically:

1. **Task 1: EquityTicker ORM model and EquityPriceClient API client** - `c44740d` (feat)
2. **Task 2: Admin equity mapping UI with CRUD routes** - `1efd299` (feat)

**Plan metadata:** _(pending — created after this commit)_

## Files Created/Modified

**Created:**
- `app/models/equity_ticker.py` - EquityTicker(Base) ORM model with entity_name, ticker, exchange, enabled, updated_at, updated_by
- `app/collectors/equity.py` - EquityPriceClient with is_configured(), get_price(), _build_headers(), _fetch_price(), _record_event()
- `app/templates/admin/equity.html` - Equity ticker list page with add-mapping form
- `app/templates/admin/equity_edit.html` - Pre-populated edit form for single mapping

**Modified:**
- `app/models/__init__.py` - Added EquityTicker export in __all__
- `app/main.py` - Added `from app.models import equity_ticker` for Base.metadata registration
- `app/routers/admin.py` - Added EquityTicker import + 5 CRUD routes (GET/POST /equity, POST /equity/delete/{id}, GET+POST /equity/edit/{id})
- `app/templates/admin/base.html` - Added Equity Tickers nav link after Factiva Config

## Decisions Made

- **Returns None on all failures:** EquityPriceClient.get_price() catches all exceptions and returns None. Callers (pipeline enrichment) can always safely proceed without equity data.
- **Multiple field name fallbacks:** The equity API field names (price/lastPrice/last etc.) are not yet confirmed. Client tries all known variants with `or` chaining.
- **BASE_PRICE_PATH = /coreapi/equity-price/v1/price:** Inferred path — validate against real API endpoint on deployment machine before production.
- **Flash messages via query params:** No session middleware in this app, so success/error messages pass as ?success=...&error=... query params on redirect. Simple and stateless.
- **Separate equity_edit.html template:** Cleaner separation than embedding the edit form in equity.html. Follows the same pattern as other admin pages.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required for this plan. EquityPriceClient.is_configured() returns False until MMC_API_BASE_URL and MMC_API_KEY are set in .env (same credentials used for Factiva).

## Next Phase Readiness

Ready for Plan 02 (pipeline enrichment integration):
- `EquityTicker` model importable from `app.models`
- `EquityPriceClient` importable from `app.collectors.equity`
- `equity_tickers` table exists in DB
- Admin can add ticker mappings at /admin/equity before running enrichment

Blockers:
- BASE_PRICE_PATH `/coreapi/equity-price/v1/price` is inferred — validate against actual API on deployment machine
- Equity price field names (price/lastPrice/last etc.) need validation against real API response

---
*Phase: 11-equity-price-enrichment*
*Completed: 2026-02-19*
