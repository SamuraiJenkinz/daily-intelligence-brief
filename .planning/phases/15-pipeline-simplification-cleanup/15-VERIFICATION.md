---
phase: 15-pipeline-simplification-cleanup
verified: 2026-02-26T21:43:07Z
status: passed
score: 15/15 must-haves verified
---

# Phase 15: Pipeline Simplification & Cleanup Verification Report

**Phase Goal:** Simplify the pipeline to use FactivaCollector as the sole collection path (no Apify/RSS fallback) and remove all Apify infrastructure from the codebase. Deduplication and classification continue to work. No new collection sources are added.

**Verified:** 2026-02-26T21:43:07Z  
**Status:** PASSED  
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pipeline orchestrator calls FactivaCollector.collect() directly with no Apify fallback path | VERIFIED | pipeline.py:199 direct factiva_collector.collect() with no fallback logic |
| 2 | When Factiva collection fails after retry, pipeline skips daily brief and sends admin alert (no fallback) | VERIFIED | pipeline.py:200-207 exception handler updates Run.status=FAILED, commits, returns immediately |
| 3 | When Factiva returns zero articles, pipeline sends empty brief | VERIFIED | pipeline.py:209-211 explicit check continues pipeline flow |
| 4 | Pipeline still creates Run record, deduplicates, classifies, delivers emails | VERIFIED | pipeline.py:190-246 Run created, URL dedup, semantic dedup, article storage, continues to step 2 |
| 5 | PipelineOrchestrator no longer requires ApifyCollector in its constructor | VERIFIED | pipeline.py:44-48 __init__ has classifier, reporter, token_manager only |
| 6 | ApifyCollector class file deleted from codebase | VERIFIED | app/services/collector.py does not exist |
| 7 | All Apify source implementation files are deleted | VERIFIED | Only base.py and __init__.py remain in app/services/sources/ |
| 8 | app/services/sources/__init__.py only exports NewsSource from base.py | VERIFIED | File exports only NewsSource with Phase 15 explanatory comment |
| 9 | base.py abstract interface is retained for future extensibility | VERIFIED | 53-line NewsSource(ABC) class with scrape() abstract method |
| 10 | No Python file fails to import due to missing ApifyCollector or source files | VERIFIED | All imports successful - pipeline, main, admin, sources |
| 11 | Test and script files updated to remove Apify references | VERIFIED | test_collection.py uses FactivaCollector, test_pipeline.py has correct signature |
| 12 | apify-client and feedparser removed from requirements.txt | VERIFIED | Zero matches for both, httpx retained |
| 13 | APIFY_TOKEN and Apify configuration section removed from .env.example | VERIFIED | Zero APIFY matches |
| 14 | is_apify_configured() method and apify_token setting removed from config.py | VERIFIED | Zero apify references, config loads successfully |
| 15 | No stale Apify references remain in comments across app/ directory | VERIFIED | Only intentional DB/schema compatibility references preserved |

**Score:** 15/15 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| app/services/pipeline.py | Factiva-only orchestration | VERIFIED | _store_articles method, direct collect() calls, no ApifyCollector |
| app/main.py | CLI entry without ApifyCollector | VERIFIED | PipelineOrchestrator has 3 params only |
| app/routers/admin.py | Admin routes without ApifyCollector | VERIFIED | Zero ApifyCollector or is_apify_configured references |
| app/services/__init__.py | Clean module without exports | VERIFIED | Only module docstring, no ApifyCollector |
| app/services/sources/base.py | Abstract NewsSource retained | VERIFIED | 53-line ABC with scrape() method |
| app/services/sources/__init__.py | Minimal module exports NewsSource | VERIFIED | Exports only NewsSource with Phase 15 comment |
| requirements.txt | Clean dependency list | VERIFIED | No apify-client or feedparser |
| .env.example | No Apify variables | VERIFIED | Zero APIFY_TOKEN |
| app/config.py | No apify settings | VERIFIED | Zero apify references |
| app/services/reporter.py | Factiva default | VERIFIED | Line 135 fallback changed to 'Factiva' |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| pipeline.py | factiva.py | FactivaCollector.collect() | WIRED | Import line 24, calls lines 199/580 |
| pipeline.py | pipeline.py | _store_articles | WIRED | Method 65-88, called 238/620 |
| sources/__init__.py | sources/base.py | import NewsSource | WIRED | Line 8 direct import |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| sources/base.py | 28-37 | apify_client parameter | Info | Historical artifact, not used by pipeline |
| main.py | 57 | Migration SQL DEFAULT | Info | Intentionally preserved for DB compatibility |
| news_article.py | 39 | Column default | Info | SQL default retained, pipeline overrides |

**No blockers or warnings.** All info-level items intentionally preserved.

### Human Verification Required

None — all phase goals verifiable programmatically.

### Gaps Summary

None — all 15 must-haves verified. Phase goal fully achieved.

## Verification Details

### Plan 15-01 Verification (Pipeline Refactoring)

**Must-haves:** 5/5 verified

Evidence:
- PipelineOrchestrator.__init__ has no collector parameter
- FactivaCollector.collect() direct calls at lines 199, 580
- _store_articles() method lines 65-88 with Factiva default
- Factiva failure handling lines 200-207 with FAILED status
- Zero articles handling lines 209-211 continues flow
- URL dedup lines 213-225, semantic dedup lines 227-235
- All imports successful

Pattern checks: Zero matches for ApifyCollector, INSURANCE_FALLBACK_SOURCES, collect_from_sources, self.collector

### Plan 15-02 Verification (File Deletion)

**Must-haves:** 6/6 verified

Evidence:
- app/services/collector.py DELETED
- Only base.py and __init__.py remain in sources/
- All 6 source files deleted (artemis, business_insurance, insurance_journal, lloyds_list, reinsurance_news, rss_source)
- NewsSource import successful
- Zero ApifyCollector references in app/
- Scripts updated correctly

### Plan 15-03 Verification (Dependencies & Config)

**Must-haves:** 4/4 verified

Evidence:
- Zero apify-client, feedparser in requirements.txt
- Zero APIFY in .env.example
- Zero apify, is_apify_configured in config.py
- Config loads successfully
- Only 17 intentional references remain (DB/schema compatibility)

Preserved references:
- SourceType.APIFY enum (DB compatibility)
- source_type Literal (schema compatibility)
- Historical comments and SQL defaults (backward compatibility)

---

**Verification Summary:**

Phase 15 goal fully achieved. All 15 must-haves from 3 plans verified:
- Plan 15-01: 5/5 verified — Factiva-only pipeline with inline storage
- Plan 15-02: 6/6 verified — ApifyCollector and sources deleted
- Plan 15-03: 4/4 verified — Dependencies and config cleaned

No gaps. All imports successful. Only intentional DB/schema compatibility references remain. Ready to proceed.

---

_Verified: 2026-02-26T21:43:07Z_  
_Verifier: Claude (gsd-verifier)_
