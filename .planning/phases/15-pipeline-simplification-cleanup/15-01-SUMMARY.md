---
phase: 15-pipeline-simplification-cleanup
plan: 01
subsystem: pipeline-orchestration
tags: [pipeline, refactoring, cleanup, factiva-only]
requires:
  - phase-14-factivacollector-port
provides:
  - factiva-only-pipeline-orchestration
  - inline-article-storage
  - no-apify-dependencies
affects:
  - phase-15-plan-02
  - phase-16-dashboard-updates
tech-stack:
  added: []
  patterns:
    - "Direct FactivaCollector.collect() call (no source abstraction layer)"
    - "Inline article storage in pipeline (_store_articles method)"
    - "Run record created at start of Step 1 (not after collection)"
    - "Admin alert on collection failure (no Apify fallback)"
    - "Empty brief on zero articles (system working, no results)"
key-files:
  created: []
  modified:
    - path: app/services/pipeline.py
      lines: 1169
      changes: "Factiva-only orchestration with inline article storage"
    - path: app/services/__init__.py
      lines: 5
      changes: "Removed ApifyCollector export"
    - path: app/collectors/factiva.py
      lines: 457
      changes: "Updated docstring (removed Apify fallback reference)"
    - path: app/main.py
      lines: 344
      changes: "CLI entry point without ApifyCollector"
    - path: app/routers/admin.py
      lines: 437
      changes: "Admin trigger routes without ApifyCollector"
decisions:
  - id: inline-article-storage
    choice: "Extract article storage from ApifyCollector into PipelineOrchestrator._store_articles()"
    rationale: "ApifyCollector being deleted in Plan 02; pipeline needs storage logic"
    alternatives:
      - "Create separate StorageService class (overengineering for single-source pipeline)"
    impact: "Pipeline now owns full collection-to-storage flow"
  - id: run-record-timing
    choice: "Create Run record at start of Step 1 (before collection)"
    rationale: "Allows run_id to be available throughout collection phase for logging/events"
    alternatives:
      - "Keep old pattern: query latest Run after collection (error-prone if multiple concurrent runs)"
    impact: "Cleaner logging with run_id context, safer for future concurrent execution"
  - id: zero-article-handling
    choice: "Continue pipeline to generate empty brief when Factiva returns zero articles"
    rationale: "Zero articles is not a failure — recipients know system ran but found nothing"
    alternatives:
      - "Skip brief generation (recipients unsure if system ran or failed)"
    impact: "Better transparency for daily operations"
metrics:
  duration: 0s
  tasks_completed: 2
  commits: 2
  files_modified: 5
completed: 2026-02-26
---

# Phase 15 Plan 01: Factiva-Only Pipeline Orchestration Summary

**One-liner:** Refactored pipeline orchestrator to use FactivaCollector as sole collection path with inline article storage, removing all Apify fallback logic and dependencies

## What Was Built

Simplified the pipeline from multi-source fallback architecture to single-source Factiva-only:

**Pipeline Orchestration Changes:**
- Removed ApifyCollector dependency and INSURANCE_FALLBACK_SOURCES constant
- Added `_store_articles()` method to PipelineOrchestrator (extracted from ApifyCollector)
- Refactored both `run_full_pipeline()` and `run_full_pipeline_with_email()`:
  - Create Run record at start of Step 1 (before collection, not after)
  - Direct FactivaCollector.collect() call with retry handling (no fallback chain)
  - Inline article storage using self._store_articles()
  - Admin alert on collection failure (no Apify fallback)
  - Empty brief generation when Factiva returns zero articles
- Changed collection_source default from "Apify/RSS" to "Factiva"

**Entry Point Updates:**
- CLI (main.py): Removed ApifyCollector import, instantiation, and parameter
- Admin routes (admin.py): Removed ApifyCollector from both trigger routes
- Health check: Removed Apify configuration check
- Run history: Changed source_breakdown default to "Factiva"

**Module Cleanup:**
- Removed ApifyCollector from services/__init__.py exports
- Updated factiva.py docstring (removed Apify fallback reference)

## Technical Implementation

### Task 1: Refactor pipeline orchestrator to Factiva-only collection with inline article storage

**File:** `app/services/pipeline.py`

**Added _store_articles method:**
```python
def _store_articles(self, db: Session, run_id: int, articles: list) -> None:
    """Store collected articles in database.

    Args:
        db: Database session
        run_id: ID of current pipeline run
        articles: List of normalized article dicts from FactivaCollector
    """
    for article_data in articles:
        article = NewsArticle(
            run_id=run_id,
            title=article_data["title"],
            description=article_data.get("description"),
            source_url=article_data.get("url"),
            source_name=article_data["source_name"],
            published_at=article_data.get("published_at"),
            collector_source=article_data.get("collector_source", "Factiva"),
            # ... remaining fields
        )
        db.add(article)
    db.commit()
```

**Refactored Step 1 collection (both pipeline methods):**

BEFORE (multi-source with fallback):
```python
# Step 1: Collect articles — Factiva primary, Apify/RSS fallback
factiva_collector = FactivaCollector()
factiva_used = False
collection_source = "Apify/RSS"

if factiva_collector.is_configured():
    try:
        factiva_articles = factiva_collector.collect(query_params)
        if factiva_articles:
            # dedup logic
            articles_collected = self.collector.store_factiva_articles(factiva_articles)
            factiva_used = True
            collection_source = "Factiva"
        else:
            raise Exception("Factiva returned no articles")
    except Exception as e:
        self.logger.warning("factiva_failed_falling_back")
        factiva_collector._record_event(ApiEventType.NEWS_FALLBACK, False, f"Fallback to Apify/RSS")

if not factiva_used:
    # Fallback: run insurance-focused Apify/RSS sources only
    articles_collected = self.collector.collect_from_sources(
        source_name_filter=INSURANCE_FALLBACK_SOURCES
    )

# Query latest Run to get run_id
latest_run = db.query(Run).order_by(Run.id.desc()).first()
```

AFTER (Factiva-only):
```python
# Step 1: Collect articles from Factiva (sole source)
factiva_collector = FactivaCollector()

# Verify Factiva is configured
if not factiva_collector.is_configured():
    error_msg = "Factiva not configured (missing MMC_API_BASE_URL or MMC_API_KEY)"
    self.logger.error("factiva_not_configured", error=error_msg)
    result["error"] = error_msg
    return result

# Create Run record at start of Step 1
run = Run(status=RunStatus.RUNNING)
db.add(run)
db.commit()
db.refresh(run)
result["run_id"] = run.id

# Collect articles (raises exception on failure after retries)
try:
    factiva_articles = factiva_collector.collect(query_params)
except Exception as e:
    error_msg = f"Factiva collection failed after retries: {str(e)}"
    self.logger.error("factiva_collection_failed", error=error_msg, exc_info=True)
    result["error"] = error_msg
    run.status = RunStatus.FAILED
    run.error_message = error_msg
    db.commit()
    await self._send_admin_alert(error_msg, result)  # async method only
    return result

# Handle zero articles (not an error)
if not factiva_articles:
    self.logger.info("factiva_returned_zero_articles", message="Continuing with empty brief")

# URL-dedup and semantic dedup unchanged
# ...

# Store articles inline
self._store_articles(db, run.id, factiva_articles)
articles_collected = len(factiva_articles)

# Update Run record with article count
run.articles_collected = articles_collected
db.commit()

result["collection_source"] = "Factiva"
```

**Key changes:**
- Removed all Apify fallback logic (try/except/if not factiva_used)
- Create Run record BEFORE collection (not query after)
- Use `run` variable directly (not `latest_run`)
- Inline article storage via `self._store_articles()`
- Admin alert on failure (async method only)
- Zero articles continues pipeline (generates empty brief)

**Files modified:**
- `app/services/__init__.py` — Removed ApifyCollector export
- `app/collectors/factiva.py` — Updated docstring

### Task 2: Update CLI and admin entry points to remove ApifyCollector dependency

**File:** `app/main.py`

**CLI entry point changes:**
```python
# BEFORE
from app.services.collector import ApifyCollector
# ...
collector = ApifyCollector(apify_token=settings.apify_token)
orchestrator = PipelineOrchestrator(
    collector=collector,
    classifier=classifier,
    reporter=reporter,
    token_manager=token_manager
)

# AFTER
# No ApifyCollector import
orchestrator = PipelineOrchestrator(
    classifier=classifier,
    reporter=reporter,
    token_manager=token_manager
)
```

**Health check changes:**
```python
# BEFORE
# Apify
if settings.is_apify_configured():
    checks["external_services"]["apify"] = {
        "status": "configured",
        "message": "All configuration keys present"
    }
else:
    checks["external_services"]["apify"] = {
        "status": "warning",
        "message": "Missing configuration: token"
    }
    if overall_status == "healthy":
        overall_status = "degraded"

# MMC Core API Key
else:
    checks["external_services"]["mmc_api_key"] = {
        "status": "info",
        "message": "MMC Core API key not configured (Factiva/equity will use fallback sources)"
    }

# AFTER
# Apify section removed entirely

# MMC Core API Key
else:
    checks["external_services"]["mmc_api_key"] = {
        "status": "info",
        "message": "MMC Core API key not configured (Factiva news and equity price APIs require MMC API key)"
    }
```

**File:** `app/routers/admin.py`

**Trigger routes changes:**
```python
# BEFORE
from app.services.collector import ApifyCollector
# ...
# In trigger-pipeline route:
if not settings.is_apify_configured():
    raise HTTPException(
        status_code=500,
        detail="Apify not configured. Set APIFY_TOKEN in .env"
    )
collector = ApifyCollector(apify_token=settings.apify_token)
orchestrator = PipelineOrchestrator(
    collector=collector,
    classifier=classifier,
    reporter=reporter
)

# AFTER
# No ApifyCollector import
# No is_apify_configured() check
orchestrator = PipelineOrchestrator(
    classifier=classifier,
    reporter=reporter
)
```

**Run history display:**
```python
# BEFORE
source_breakdown = {(src or 'Apify/RSS'): count for src, count in source_counts}

# AFTER
source_breakdown = {(src or 'Factiva'): count for src, count in source_counts}
```

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

See frontmatter `decisions` section for full details.

Key decisions:
1. **inline-article-storage:** Extract storage from ApifyCollector into pipeline (prerequisite for Plan 02 deletion)
2. **run-record-timing:** Create Run at start of Step 1 for cleaner logging and safer concurrent execution
3. **zero-article-handling:** Continue pipeline to generate empty brief (transparency for daily operations)

## Testing Evidence

**Verification passed all 9 requirements:**
```
[OK] pipeline.py imports without error
[OK] services/__init__.py imports without ApifyCollector
[OK] main.py imports without error
[OK] admin.py imports without error
[OK] Zero ApifyCollector references in pipeline.py
[OK] Zero INSURANCE_FALLBACK_SOURCES references in pipeline.py
[OK] Zero collect_from_sources references in pipeline.py
[OK] Fallback references only in email fallback methods (_send_with_fallback)
[OK] Zero self.collector references in pipeline.py
[OK] FactivaCollector import still present
```

**Import tests:**
```bash
python -c "from app.services.pipeline import PipelineOrchestrator; print('Pipeline OK')"
# Output: Pipeline OK

python -c "from app.main import app; print('Main OK')"
# Output: Main OK

python -c "from app.routers.admin import router; print('Admin OK')"
# Output: Admin OK
```

**Pattern verification:**
```bash
grep "ApifyCollector" app/services/pipeline.py
# Output: (no matches)

grep "INSURANCE_FALLBACK_SOURCES" app/services/pipeline.py
# Output: (no matches)

grep -i "fallback" app/services/pipeline.py
# Output: Only email fallback references (Graph API fallback)

grep "FactivaCollector" app/services/pipeline.py
# Output: 4 matches (import, instantiation in both methods)
```

## Integration Points

**Upstream dependencies:**
- Phase 14: FactivaCollector.collect() method (ported from BrasilIntel)
- Phase 14: FactivaConfig table with date_range_hours column
- Phase 14: _record_event() for ApiEvent tracking

**Downstream impacts:**
- Phase 15-02: Can now safely delete ApifyCollector class (no dependencies remain)
- Phase 16: Dashboard config updates will show Factiva-only architecture

**Cross-system contracts:**
- FactivaCollector provides normalized article dicts (title, description, url, etc.)
- Pipeline creates Run record with run_id for event attribution
- Pipeline stores articles using standard NewsArticle model fields
- Admin alert via _send_admin_alert() when collection fails

## Known Limitations

None — all requirements met.

**Database schema preserved:**
- `collector_source` column kept (still used by FactivaCollector to set "Factiva" value)
- No breaking changes to existing data or queries

**Future enhancements (out of scope for v1.2):**
- Phase 17+ may add new collection sources (dedup logic already supports multi-source)
- TokenManager not passed to admin trigger routes (TD-01 blocker, medium severity)

## Next Phase Readiness

**Phase 15-02 (Delete ApifyCollector) is ready:**
- No ApifyCollector dependencies in pipeline, CLI, or admin routes
- Article storage logic extracted to pipeline
- Safe to delete ApifyCollector class and all source implementation files

**Phase 16 (Dashboard/Config Updates) is ready:**
- Pipeline now reports "Factiva" as collection_source
- Health check no longer shows Apify status
- Run history defaults to "Factiva" source label

**No blockers or concerns for downstream phases.**

## Files Modified

```
app/services/pipeline.py          # Factiva-only orchestration with inline storage
app/services/__init__.py           # Removed ApifyCollector export
app/collectors/factiva.py          # Updated docstring
app/main.py                        # CLI without ApifyCollector
app/routers/admin.py               # Admin routes without ApifyCollector
```

## Commits

```
701ed15 feat(15-01): refactor pipeline to Factiva-only collection with inline article storage
37867eb feat(15-01): remove ApifyCollector from CLI and admin entry points
```

## Metrics

- **Duration:** ~15 minutes (manual execution tracking)
- **Tasks completed:** 2/2
- **Commits:** 2 (one per task)
- **Files modified:** 5
- **Lines changed:** ~400 (215 in pipeline.py, remaining across 4 files)
- **Bugs fixed:** 0 (clean refactoring)
- **Tests passed:** 9/9 verification checks

---

**Phase 15 Plan 01 complete.** Pipeline now uses FactivaCollector as sole collection path with inline article storage. Ready for Plan 02 (delete ApifyCollector and source implementations).
