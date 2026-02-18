---
phase: 10-factiva-news-collection
verified: 2026-02-18T20:00:00Z
status: passed
score: 5/5 must-haves verified
---

# Phase 10: Factiva News Collection Verification Report

**Phase Goal:** The pipeline fetches insurance/reinsurance news from Factiva as its primary source each morning, with Apify/RSS running automatically as fallback when Factiva is unavailable, and article source stored per-article.

**Verified:** 2026-02-18T20:00:00Z
**Status:** passed
**Re-verification:** No - initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Morning pipeline queries Factiva with configured industry/company codes and returns articles with headline, plaintext, publication date, and source URL | VERIFIED | FactivaCollector.collect() builds query from FactivaConfig DB row; _normalize_article() returns title, description (plaintext preferred over snippet), url, published_at, source_name, collector_source |
| 2  | Factiva articles are deduplicated against the existing article store - no duplicates appear in the brief | VERIFIED | pipeline.py lines 171-178: URL-dedup set from date(created_at)==today; ArticleDeduplicator semantic dedup also applied within-batch |
| 3  | Factiva articles flow through the existing AI classification pipeline unchanged and appear in the brief exactly as Apify-sourced articles do | VERIFIED | store_factiva_articles() calls _store_articles() with same ORM path; _prepare_articles() includes collector_source; both brief templates render source badges |
| 4  | When Factiva is unreachable, pipeline collects from Apify/RSS instead, logs a structured fallback event, and brief generates normally | VERIFIED | pipeline.py except block lines 198-210 and 499-511: catches all exceptions, records ApiEventType.NEWS_FALLBACK event, calls collect_from_sources with INSURANCE_FALLBACK_SOURCES |
| 5  | Each article record in DB carries a source field indicating its origin (Factiva or Apify/RSS) | VERIFIED | NewsArticle.collector_source Column(String(20), default=Apify/RSS) at line 39; _store_articles() reads from article dict at line 262; Factiva articles carry Factiva, Apify carry Apify/RSS |

**Score:** 5/5 truths verified

---

## Required Artifacts

### Plan 10-01: FactivaCollector Foundation

| Artifact | Status | Details |
|----------|--------|---------|
| app/collectors/factiva.py | VERIFIED | 456 lines; collect(), _search(), _search_by_url(), _fetch_article(), _normalize_article(), _record_event(), _build_headers() all substantive; X-Api-Key auth; httpx+tenacity+structlog |
| app/collectors/__init__.py | VERIFIED | Exports FactivaCollector in __all__ |
| app/models/factiva_config.py | VERIFIED | 93 lines; industry_codes, company_codes, keywords, page_size, enabled, updated_at, updated_by columns; __tablename__ = factiva_config |
| app/models/news_article.py | VERIFIED | collector_source = Column(String(20), nullable=True, default=Apify/RSS) at line 39 - backward-compatible |
| app/models/__init__.py | VERIFIED | FactivaConfig imported at line 10 and in __all__ at line 20 |
| app/main.py startup migration | VERIFIED | Lines 48-78: PRAGMA table_info check before ALTER TABLE; INSERT OR IGNORE seeds default factiva_config row id=1; try/except never blocks startup |

### Plan 10-02: Pipeline Integration

| Artifact | Status | Details |
|----------|--------|---------|
| app/services/pipeline.py | VERIFIED | 856 lines; INSURANCE_FALLBACK_SOURCES constant (4 insurance sources); identical Factiva-primary + fallback logic in both pipeline methods; NEWS_FALLBACK event recorded on exception |
| app/services/collector.py | VERIFIED | collect_from_sources(source_name_filter=None) at line 58; filter on DB query at line 89; store_factiva_articles() at line 290 creates its own Run record |
| app/services/reporter.py | VERIFIED | _prepare_articles() includes collector_source at line 135 with getattr fallback; sort key at lines 92-95 puts Factiva first within each priority group |
| app/templates/role_brief.html | VERIFIED | Lines 734-738: blue badge for Factiva, gray badge for Apify/RSS - both branches present and non-empty |
| app/templates/email/role_email.html | VERIFIED | Lines 137-141: inline-styled badges (no CSS classes) for email compatibility; same conditional |
| app/templates/admin/dashboard.html | VERIFIED | Lines 201-208: source_breakdown dict renders Factiva and Apify/RSS badges in Source column of runs table |
| app/routers/admin.py dashboard | VERIFIED | Lines 87-95: group_by(NewsArticle.collector_source) per run_id; source_breakdown dict added to runs_data |

### Plan 10-03: Admin Config UI

| Artifact | Status | Details |
|----------|--------|---------|
| app/routers/admin.py GET /admin/factiva | VERIFIED | Line 1136: reads FactivaConfig id=1; seeds default row if missing (defensive); renders factiva.html |
| app/routers/admin.py POST /admin/factiva | VERIFIED | Line 1175: page_size whitelist (10/25/50/100); comma cleanup; hidden+checkbox enabled pattern; db.commit() persists; flash success/error |
| app/templates/admin/factiva.html | VERIFIED | 254 lines; form fields for all 5 editable params; inline industry code reference table; success/error alert blocks |
| app/templates/admin/base.html sidebar | VERIFIED | Line 231: Factiva Config link with active_nav == factiva active class |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| pipeline.py Step 1 | FactivaCollector.collect() | FactivaConfig DB row query params | WIRED | factiva_collector.collect(query_params) called in both pipeline methods with DB-sourced params |
| FactivaCollector.collect() | /coreapi/recent-news/v1/search | httpx.Client.get() + X-Api-Key | WIRED | _search() builds URL from base_url + BASE_SEARCH_PATH; _build_headers() returns X-Api-Key header |
| FactivaCollector | /coreapi/recent-news/v1/article/{id} | httpx.Client.get() per article | WIRED | _fetch_article() line 318; 4xx returns empty dict for snippet fallback - never drops article |
| _normalize_article() | article dict schema | title/description/url/published_at/source_name/collector_source | WIRED | All 6 required fields returned; plaintext body preferred over snippet |
| Factiva articles | NewsArticle.collector_source | store_factiva_articles() -> _store_articles() -> article_data.get | WIRED | collector_source=Factiva flows through entire collect->normalize->store chain |
| Factiva failure | NEWS_FALLBACK ApiEvent | factiva_collector._record_event(ApiEventType.NEWS_FALLBACK, False) | WIRED | Recorded at lines 201-203 and 502-503 in both pipeline methods before fallback runs |
| Fallback path | INSURANCE_FALLBACK_SOURCES only | collect_from_sources(source_name_filter=INSURANCE_FALLBACK_SOURCES) | WIRED | 4-source list filters DB query; general business sources excluded from fallback |
| _prepare_articles() | collector_source in template context | getattr fallback to Apify/RSS | WIRED | Backward-compatible at line 135 for pre-Phase-10 articles |
| reporter sort | Factiva-first within priority group | sort key (priority_order, 0 if Factiva else 1) | WIRED | Lines 92-95 in filter_articles_by_role() |
| admin dashboard runs | per-run source_breakdown | group_by(NewsArticle.collector_source) | WIRED | Lines 88-95 admin.py; dict passed to template as run.source_breakdown |
| GET /admin/factiva | FactivaConfig row | SQLAlchemy query FactivaConfig.id == 1 | WIRED | Defensive seed if missing; startup migration is primary creation path |
| POST /admin/factiva | FactivaConfig persisted | Form -> validate -> db.commit() | WIRED | page_size whitelist + comma cleanup + enabled string-to-bool all implemented |

---

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| NEWS-01 | SATISFIED | FactivaCollector.collect() queries search endpoint with X-Api-Key using FactivaConfig params (industry codes, company codes, keywords, page size) |
| NEWS-02 | SATISFIED | _fetch_article() fetches body from /coreapi/recent-news/v1/article/{id}; _normalize_article() maps headline, plaintext, URL, and epoch-ms timestamp |
| NEWS-03 | SATISFIED | FactivaConfig ORM model with all required admin-configurable fields; CRUD at /admin/factiva persists to DB |
| NEWS-04 | SATISFIED | NewsArticle.collector_source column; set on every article stored via both Factiva and Apify/RSS paths |
| NEWS-05 | SATISFIED | Startup migration with PRAGMA check before ALTER TABLE; INSERT OR IGNORE seeds default row id=1 |
| NEWS-06 | SATISFIED | URL dedup against today + ArticleDeduplicator semantic dedup both applied before store_factiva_articles() |
| FALL-01 | SATISFIED | Exception handler records NEWS_FALLBACK event and calls collect_from_sources with INSURANCE_FALLBACK_SOURCES filter |

---

## Anti-Patterns Found

None. Zero TODO/FIXME/placeholder patterns found across all phase 10 files. All handlers are substantive implementations with no empty returns or stubs.

---

## Human Verification Required

### 1. Live Factiva API Integration Test

**Test:** On the deployment machine with MMC_API_BASE_URL and MMC_API_KEY in .env, trigger a morning pipeline run via /admin/trigger.
**Expected:** Brief has articles with blue via Factiva badges; admin dashboard shows N Factiva in Source column; api_events has news_fetch event with success=True.
**Why human:** Factiva credentials unavailable on dev machine. Cannot verify actual API response schema maps to _normalize_article() field names without a live call.

### 2. Industry Code Validity

**Test:** Run the staging validation command from 10-03-SUMMARY.md to call /coreapi/recent-news/v1/industries and confirm which of i82, i832, i83, i8311, i8312, i831 are valid Factiva codes.
**Expected:** Status 200; valid codes confirmed; /admin/factiva updated to use only confirmed codes before production.
**Why human:** Codes i83, i8311, i8312, i831 are inferred. Invalid codes cause zero results and trigger silent Apify fallback. Not a code defect but an operational risk before production.

### 3. Fallback Path End-to-End

**Test:** Set MMC_API_BASE_URL to an invalid URL, trigger pipeline run, then restore the correct value.
**Expected:** Admin shows N Apify/RSS in Source column; api_events has a news_fallback event; brief generates normally from Apify/RSS articles.
**Why human:** Requires a running application; structural verification cannot simulate live API failure.

---

## Gaps Summary

No gaps found. All 5 observable truths are structurally verified. All must-haves from plans 10-01, 10-02, and 10-03 exist, are substantive (no stubs), and are wired correctly.

The three human verification items are operational validation concerns requiring live credentials or a running application. They are not code defects.

---

*Verified: 2026-02-18T20:00:00Z*
*Verifier: Claude (gsd-verifier)*