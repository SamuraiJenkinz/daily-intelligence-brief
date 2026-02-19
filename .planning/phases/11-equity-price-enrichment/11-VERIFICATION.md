---
phase: 11-equity-price-enrichment
verified: 2026-02-19T01:19:00Z
status: passed
score: 4/4 must-haves verified
gaps: []
human_verification:
  - test: Generate a brief for an article mentioning a tracked company with live equity API credentials
    expected: The brief shows an equity chip inline before sentiment/impact chips
    why_human: Requires live API credentials and a real pipeline run.
  - test: Trigger a brief run with equity API credentials missing, with a ticker mapping configured
    expected: Brief generates normally with no equity chip. No error thrown. Pipeline completes.
    why_human: Requires controlling env credentials and running the pipeline.
  - test: Navigate to /admin/equity in a running app instance and add/edit/delete a ticker mapping
    expected: All CRUD operations succeed. Equity Tickers visible in sidebar nav.
    why_human: Requires a running app instance with a browser.
---
# Phase 11: Equity Price Enrichment Verification Report

**Phase Goal:** Articles about tracked public companies appear in the brief with the company's current equity price and daily change displayed inline alongside the story, with no disruption to brief generation when price data is unavailable.

**Verified:** 2026-02-19T01:19:00Z
**Status:** PASSED
**Re-verification:** No - initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | An admin-configurable entity-to-ticker mapping associates company names with exchange and ticker symbols | VERIFIED | EquityTicker ORM model with entity_name, ticker, exchange, enabled fields; full CRUD at /admin/equity with 5 routes in admin.py |
| 2 | After AI classification, articles mentioning tracked entities are automatically enriched with current price, daily change amount, and daily change percent before brief generation | VERIFIED | Step 3b in both pipeline methods; runs after step_3 classification, before step_4 re-query; attaches _equity_data list to articles; reporter passes it as equity_data to templates |
| 3 | Enriched equity data appears inline alongside the relevant story in the HTML brief - not in a separate section | VERIFIED | Equity chip block inside impact-strip div in role_brief.html and inside chips row in role_email.html; placed before sentiment/impact/region chips |
| 4 | When equity price lookup fails for any entity (API error, timeout, unmapped ticker), the brief generates normally with that story equity fields absent and the failure logged | VERIFIED | Three explicit fallback paths in pipeline: not configured sets _equity_data=[]; no mappings sets _equity_data=[]; per-entity failure means get_price() returns None, article gets empty equity_hits. All exceptions caught and logged in EquityPriceClient.get_price(). getattr fallback in reporter provides backward-compat default. |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| app/models/equity_ticker.py | EquityTicker ORM model | VERIFIED | 97 lines. class EquityTicker(Base) with __tablename__ = equity_tickers. Fields: entity_name (String 200, unique, non-null), ticker (String 20), exchange (String 20, default NYSE), enabled (Boolean, default True), updated_at (DateTime, auto-update), updated_by (String 100). |
| app/models/__init__.py | EquityTicker exported | VERIFIED | from app.models.equity_ticker import EquityTicker present. EquityTicker in __all__. |
| app/main.py | equity_ticker import for metadata registration | VERIFIED | from app.models import equity_ticker (noqa: F401) present at line 20. |
| app/collectors/equity.py | EquityPriceClient with get_price(), is_configured(), _record_event() | VERIFIED | 284 lines. class EquityPriceClient. Has is_configured(), get_price(), _build_headers(), _fetch_price() with tenacity retry (stop=2, wait exponential, retry on TimeoutException+ConnectError), _record_event() with isolated SessionLocal. Returns None on all failures. Never raises to caller. |
| app/routers/admin.py | /admin/equity CRUD routes | VERIFIED | 5 routes: GET /equity, POST /equity (add with duplicate check), POST /equity/delete/{id}, GET /equity/edit/{id}, POST /equity/edit/{id}. Imports EquityTicker. Uses SessionLocal() with try/finally. Logs mutations with structlog. |
| app/templates/admin/equity.html | Admin equity ticker mapping page | VERIFIED | 213 lines. Extends base.html. Table with enabled badge. Add-mapping form with entity_name, ticker, exchange, enabled fields. Hidden+checkbox pattern. Flash messages via query params. |
| app/templates/admin/equity_edit.html | Pre-populated edit form | VERIFIED | 132 lines. Extends base.html. Pre-populated form with current values. Hidden+checkbox enabled pattern. Cancel link. |
| app/templates/admin/base.html | Equity Tickers nav link | VERIFIED | Nav link at /admin/equity with bi-graph-up icon and label Equity Tickers. Active state wired via active_nav == equity check. |
| app/services/pipeline.py | Step 3b equity enrichment in both pipeline methods | VERIFIED | Step 3b present in both run_full_pipeline() (lines ~281-356) and run_full_pipeline_with_email() (lines ~687-766). Both positioned after step_3 (classification) and before step_4 (re-query). Per-run dedup cache fetched_prices dict keyed by exchange:ticker. Equity data transfer loop after Step 4 re-query via equity_data_map. |
| app/services/reporter.py | equity_data in _prepare_articles | VERIFIED | Line 136: equity_data: getattr(article, _equity_data, []) inside _prepare_articles() article dict. |
| app/templates/role_brief.html | Inline equity chip in browser brief | VERIFIED | Equity chip block inside impact-strip div before sentiment chips. Jinja2 outer guard (if article.equity_data) and inner loop (for eq in article.equity_data). Shows ticker (Marsh blue #00263e), price ($formatted), change (green #198754/red #dc3545/grey #6c757d). .equity-chip CSS class with hover transition. |
| app/templates/email/role_email.html | Inline equity chip in email brief | VERIFIED | Equity chip block inside chips row before sentiment chip. Inline styles only (no CSS classes). display: inline-block (Outlook-safe, not inline-flex). Explicit padding-top/bottom/left/right properties. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| app/collectors/equity.py | app/config.py | get_settings() for mmc_api_base_url and mmc_api_key | WIRED | settings = get_settings() in __init__; reads settings.mmc_api_base_url and settings.mmc_api_key. is_configured() checks both. |
| app/collectors/equity.py | app/models/api_event.py | _record_event with ApiEventType.EQUITY_FETCH | WIRED | from app.models.api_event import ApiEvent, ApiEventType. ApiEventType.EQUITY_FETCH = equity_fetch confirmed. _record_event() creates ApiEvent with api_name=equity. |
| app/routers/admin.py | app/models/equity_ticker.py | CRUD operations in /admin/equity routes | WIRED | from app.models.equity_ticker import EquityTicker. All 5 routes use db.query(EquityTicker) for reads and EquityTicker(...) for inserts. |
| app/main.py | app/models/equity_ticker.py | Import for Base.metadata registration | WIRED | from app.models import equity_ticker ensures EquityTicker is registered with Base.metadata before create_all() runs. |
| app/services/pipeline.py | app/collectors/equity.py | EquityPriceClient.get_price() calls per matched entity | WIRED | from app.collectors.equity import EquityPriceClient. equity_client = EquityPriceClient() in Step 3b. equity_client.get_price(ticker=..., exchange=..., run_id=...) called per entity match. |
| app/services/pipeline.py | app/models/equity_ticker.py | db.query(EquityTicker) to build entity-to-ticker lookup | WIRED | from app.models.equity_ticker import EquityTicker. db.query(EquityTicker).filter(EquityTicker.enabled == True).all() in Step 3b of both methods. |
| app/services/reporter.py | templates | equity_data key in prepared article dict consumed by Jinja2 | WIRED | equity_data: getattr(article, _equity_data, []) in _prepare_articles(). Both role_brief.html and role_email.html reference article.equity_data. |

---

### Requirements Coverage

| Requirement | Status | Supporting Truths |
|-------------|--------|-------------------|
| EQTY-01 - Admin-configurable entity-to-ticker mapping | SATISFIED | Truth 1: EquityTicker model + /admin/equity CRUD |
| EQTY-02 - Automatic enrichment after classification | SATISFIED | Truth 2: Step 3b in both pipeline methods |
| EQTY-03 - Equity data displayed inline in brief | SATISFIED | Truth 3: Equity chip in impact-strip (browser) and chips row (email) |
| EQTY-04 - Data includes price, daily change amount, daily change percent | SATISFIED | Truth 3: Chip renders eq.price, eq.change, eq.change_pct with formatting |
| FALL-03 - No disruption when price data unavailable | SATISFIED | Truth 4: Three fallback paths; get_price() always returns None on failure; brief generates normally |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| app/collectors/equity.py | 122 | Comment: exact field names from the MMC equity API are not yet confirmed | Info | Multiple field name fallbacks are implemented. Real defensive logic, not a stub. Needs validation against actual API response on first deployment. |
| app/collectors/equity.py | 70 | BASE_PRICE_PATH = /coreapi/equity-price/v1/price is inferred | Info | Documented as inferred in all three SUMMARYs. Real code fully implemented around this path. Needs validation on deployment. |

No blocker-severity anti-patterns found. No TODO/FIXME comments. No placeholder content in code. No empty return stubs.

---

### Human Verification Required

#### 1. Live Equity Price Display

**Test:** Configure MMC API credentials in .env (MMC_API_BASE_URL, MMC_API_KEY), add a ticker mapping at /admin/equity (e.g. entity_name=Marsh McLennan, ticker=MMC, exchange=NYSE), run the pipeline against articles that mention Marsh McLennan, then open the generated brief.

**Expected:** The article card shows an equity chip inline - e.g. MMC $220.50 +1.25 (+0.57%) in green - before sentiment/impact chips.

**Why human:** Requires live API credentials, a real pipeline run, and visual inspection of the generated HTML.

#### 2. Graceful Fallback on API Failure

**Test:** With a ticker mapping configured, run the pipeline with invalid or missing equity API credentials.

**Expected:** The brief generates completely. The article renders normally without an equity chip. No exception is thrown. The pipeline logs a warning and continues.

**Why human:** Requires controlling env credentials and running the pipeline to confirm runtime graceful degradation.

#### 3. Admin CRUD Interface

**Test:** Navigate to /admin/equity on a running instance. Add a new mapping, edit it, disable it via the enabled checkbox, then delete it.

**Expected:** All operations succeed. The table updates correctly. Equity Tickers link appears in the admin sidebar and highlights as active on the equity page.

**Why human:** Requires a running app instance with a browser.

---

## Summary

Phase 11 goal achievement is confirmed. All four observable truths are supported by substantive, wired code:

- The EquityTicker ORM model and /admin/equity CRUD interface provide the admin-configurable mapping layer (EQTY-01).
- Step 3b in both pipeline methods runs after classification and before reporting, enriching articles with live price data via a per-run dedup cache (EQTY-02).
- Both brief templates render equity chips inline in the article impact strip, before existing sentiment/impact/region chips (EQTY-03, EQTY-04).
- Three explicit fallback paths ensure brief generation is never blocked by equity lookup issues (FALL-03). get_price() is unconditionally safe - it returns None on every failure mode and records it as an ApiEvent for observability.

One known deployment concern: the equity API response field names (price/lastPrice/last etc.) and the base path /coreapi/equity-price/v1/price need validation against the real MMC Core API on first deployment. Defensive fallback logic is fully implemented for multiple field name conventions; this is a deployment concern, not a code gap.

Three human verification items remain that require a running app with live credentials. All automated structural checks passed.

---

*Verified: 2026-02-19T01:19:00Z*
*Verifier: Claude (gsd-verifier)*
