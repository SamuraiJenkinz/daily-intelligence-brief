# Phase 15: Pipeline Simplification & Cleanup - Research

**Researched:** 2026-02-26
**Domain:** Pipeline refactoring, dependency cleanup, infrastructure removal
**Confidence:** HIGH

## Summary

Phase 15 removes all Apify/RSS collection infrastructure after Phase 14 successfully deployed FactivaCollector as the sole news source. This is a pure cleanup operation that simplifies the pipeline from a multi-source fallback chain to a single-source architecture while preserving deduplication and classification layers for future extensibility.

The current codebase has extensive Apify infrastructure across 8 source implementation files, a generic ApifyCollector orchestrator, and fallback logic woven throughout pipeline.py. The cleanup requires systematic removal across code, configuration, dependencies, tests, and documentation.

**Primary recommendation:** Execute cleanup in strict dependency order: pipeline orchestrator first (removes fallback logic), then collector service (removes ApifyCollector class), then source implementations (removes dead files), then dependencies and configuration (removes external references). This sequence prevents orphaned code and ensures each step is independently testable.

## Standard Stack

### Core Dependencies to Remove

| Library | Current Version | Purpose | Removal Impact |
|---------|----------------|---------|----------------|
| apify-client | (latest) | Apify API client for web scraping | No longer needed - Factiva is sole source |
| feedparser | 6.0.12 | RSS/Atom feed parsing | No longer needed - RSS sources being removed |

### Dependencies to Retain

| Library | Version | Purpose | Why Retained |
|---------|---------|---------|--------------|
| sentence-transformers | >=5.0.0 | Semantic deduplication | Still needed for Factiva near-duplicate detection |
| httpx | (latest) | HTTP client | Used by FactivaCollector for API calls |
| tenacity | (latest) | Retry logic with exponential backoff | Used by FactivaCollector retry decorator |

### Configuration Changes

**Settings to Remove:**
- `apify_token: str = ""` — No longer used
- `is_apify_configured()` method — No validation needed

**.env.example sections to remove:**
- APIFY_TOKEN configuration block (lines 92-105)
- APIFY CONFIGURATION section header

**Settings to Retain:**
- All MMC Core API settings (base_url, api_key) — Used by FactivaCollector
- All Azure OpenAI settings — Used by classifier
- All email settings — Used by reporter

## Architecture Patterns

### Current Pipeline Architecture (Multi-Source with Fallback)

```
Pipeline.run_full_pipeline_with_email():
├─ Step 1: Collection
│  ├─ Try: FactivaCollector.collect()
│  │  ├─ URL-dedup against today's articles
│  │  └─ Semantic dedup (ArticleDeduplicator)
│  └─ Fallback: ApifyCollector.collect_from_sources(INSURANCE_FALLBACK_SOURCES)
│     ├─ Loop: 4 Apify/RSS sources
│     ├─ Phase 1: Scrape all sources
│     ├─ Phase 2: Semantic dedup (ArticleDeduplicator)
│     └─ Phase 3: Store articles
├─ Step 2: Query articles
├─ Step 3: Classify (RoleClassificationService)
├─ Step 4: Re-query classified
├─ Step 5: Generate unified report
├─ Step 6: Generate per-role emails
├─ Step 7: Archive reports
└─ Step 8: Send emails
```

### Target Pipeline Architecture (Single-Source)

```
Pipeline.run_full_pipeline_with_email():
├─ Step 1: Collection
│  ├─ FactivaCollector.collect()
│  │  ├─ Retry: tenacity (2 attempts, exponential backoff 2-10s)
│  │  ├─ URL-dedup against today's articles
│  │  └─ Semantic dedup (ArticleDeduplicator)
│  └─ On failure: Skip brief + alert admin (no fallback)
├─ Step 2: Query articles
├─ Step 3: Classify (RoleClassificationService)
├─ Step 4: Re-query classified
├─ Step 5: Generate unified report
├─ Step 6: Generate per-role emails
├─ Step 7: Archive reports
└─ Step 8: Send emails
```

**Key Changes:**
- Remove fallback chain entirely — no Apify/RSS sources loop
- Collapse to direct FactivaCollector call
- Keep deduplication exactly as-is (semantic + URL dedup still valuable for Factiva)
- Retry handled by FactivaCollector's existing `@retry` decorator (2 attempts, exponential backoff)
- Failure mode: log error, record ApiEvent, send admin alert, skip brief generation

### Pattern: Deduplication Layers (Retained for Future Extensibility)

The deduplication system is designed for multi-source collection and remains valuable even with single-source Factiva:

```python
# URL deduplication (prevents exact duplicates from same wire service)
existing_urls = set(
    url for (url,) in db.query(NewsArticle.source_url).filter(
        func.date(NewsArticle.created_at) == today,
        NewsArticle.source_url.isnot(None)
    ).all()
)
factiva_articles = [a for a in factiva_articles if a.get("url") not in existing_urls]

# Semantic deduplication (prevents near-duplicates from different wire services)
if len(factiva_articles) > 1:
    deduplicator = ArticleDeduplicator()
    factiva_articles = deduplicator.deduplicate(factiva_articles)
```

**Why retain both layers:**
1. **URL dedup:** Factiva may return same article URL multiple times in different queries
2. **Semantic dedup:** Factiva indexes multiple wire services (Reuters, AP, Bloomberg) that often publish identical content with different headlines
3. **Future extensibility:** Keeps generic interface intact for when Phase 17+ adds new sources

**ArticleDeduplicator interface (keep as-is):**
- Accepts `List[Dict[str, Any]]` — generic article dicts from any source
- Returns deduplicated list with merged `source_name` fields
- Source-agnostic similarity threshold (0.85 cosine similarity)
- No changes needed to support single-source Factiva usage

### Pattern: Admin Notification on Failure

When FactivaCollector fails after retries, pipeline should notify admin and skip brief:

```python
# Existing admin alert pattern (from pipeline.py)
async def _send_admin_alert(self, error_msg: str, result: dict):
    settings = get_settings()
    if not settings.admin_email:
        return

    email_service = GraphEmailService()
    subject = f"[MDInsights] Pipeline Failed - {datetime.utcnow().strftime('%d %B %Y')}"
    html_body = f"""
    <html>
    <body style="font-family: sans-serif; padding: 20px;">
        <h2 style="color: #dc3545;">MDInsights Pipeline Failure</h2>
        <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p><strong>Error:</strong> {error_msg}</p>
    </body>
    </html>
    """
    await email_service.send_email([settings.admin_email], subject, html_body)
```

**New failure mode for Factiva-only pipeline:**
- FactivaCollector.collect() raises exception after retries
- Catch at pipeline level, call `_send_admin_alert()`
- Mark Run as FAILED with error message
- Return early from pipeline (no brief generation)
- Admin investigates and manually re-runs when Factiva is available

**Zero articles scenario (not a failure):**
- FactivaCollector.collect() returns empty list `[]`
- Pipeline continues normally, generates empty brief
- Recipients see "No articles collected today" message
- No admin alert needed — system is working correctly

## Don't Hand-Roll

Problems that have existing solutions or patterns already in codebase:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry logic for Factiva | Custom retry loops | Existing `@retry` decorator in FactivaCollector | Already configured with 2 attempts, exponential backoff 2-10s |
| Admin notifications | New alerting system | Existing `_send_admin_alert()` method | Already works, sends via Graph API |
| Empty brief handling | New template | Existing no-articles path in pipeline | Already returns early with simple HTML |
| Database session management | Manual transaction handling | Existing SessionLocal() context manager | Already handles commit/rollback |
| ApiEvent recording | Manual event logging | Existing `_record_event()` in FactivaCollector | Already records NEWS_FETCH and NEWS_FALLBACK events |

**Key insight:** Phase 14 already built all the infrastructure needed for Factiva-only operation. Phase 15 is pure subtraction — remove Apify code, not replace it with new code.

## Common Pitfalls

### Pitfall 1: Database Schema Assumptions
**What goes wrong:** Assuming `collector_source` column is Apify-specific and removing it
**Why it happens:** Field was added in Phase 10 for Apify/Factiva distinction
**How to avoid:** Keep `collector_source` field — it's still used by FactivaCollector to set "Factiva" value and provides value for future source additions
**Warning signs:** grep for `collector_source` shows it's still referenced in FactivaCollector._normalize_article()

**Evidence:**
```python
# app/collectors/factiva.py line 417
return {
    "title": title,
    "description": description,
    "url": url,
    "published_at": published_at,
    "source_name": self.SOURCE_LABEL,
    "collector_source": self.SOURCE_LABEL,  # Still used!
}
```

### Pitfall 2: Incomplete Comment Cleanup
**What goes wrong:** Removing code but leaving comments that reference Apify fallback logic
**Why it happens:** Comments are easy to miss in grep searches that focus on imports/classes
**How to avoid:** Run full codebase grep for `apify`, `Apify`, `APIFY`, `fallback`, `RSS` and review ALL matches including comments
**Warning signs:** Documentation mentions "Apify fallback" but code doesn't implement it

**Search strategy:**
```bash
# Find all Apify references (case-insensitive)
grep -ri "apify" --include="*.py" --include="*.md" --include="*.html"

# Find fallback logic comments
grep -ri "fallback" --include="*.py" | grep -i "apify\|rss"

# Find RSS references
grep -ri "rss" --include="*.py"
```

### Pitfall 3: Source Model Preservation
**What goes wrong:** Deleting the `Source` ORM model and `sources` table because no Apify sources are used
**Why it happens:** Model appears unused after removing ApifyCollector
**How to avoid:** Keep Source model and sources table — generic infrastructure for future source additions (Phase 17+)
**Warning signs:** Admin dashboard's source health monitoring breaks

**Evidence from requirements:**
- CLEAN-05: "Dead source implementation files removed (app/services/sources/*)"
- Note: Says "implementation files", not "Source model"
- Keep: base.py (abstract interface), Source model, sources table
- Remove: artemis.py, business_insurance.py, insurance_journal.py, lloyds_list.py, reinsurance_news.py, rss_source.py

### Pitfall 4: Test File Incomplete Cleanup
**What goes wrong:** Removing production code but leaving Apify test files and fixtures
**Why it happens:** Test scripts in `scripts/` directory are easy to overlook
**How to avoid:** Check scripts/test_collection.py which explicitly tests ApifyCollector
**Warning signs:** test_collection.py fails with ImportError after ApifyCollector removal

**Files to update:**
```
scripts/test_collection.py — Remove or rewrite to test FactivaCollector
scripts/test_pipeline.py — May have Apify-specific assertions
```

### Pitfall 5: Premature Pipeline Stage Merging
**What goes wrong:** Merging collection + dedup + classification into single function since there's only one source
**Why it happens:** Trying to optimize for current single-source state
**How to avoid:** Keep distinct pipeline steps (Step 1: collect, Step 2: query, Step 3: classify) even though they're sequential — maintains clarity and future extensibility
**Warning signs:** Pipeline becomes harder to understand and debug

**Keep separation:**
- Step 1: Collection (FactivaCollector.collect) → returns article dicts
- Step 2: Storage (store_factiva_articles) → creates Run record
- Step 3: Query (db.query articles by run_id)
- Step 4: Classification (classifier.classify_articles)
- Step 5: Reporting (reporter.generate_role_brief)

## Code Examples

### Example 1: Simplified Pipeline Orchestrator (Step 1 Collection)

```python
# app/services/pipeline.py — Step 1 after cleanup

async def run_full_pipeline_with_email(self) -> Dict:
    """Execute complete pipeline from collection to email delivery."""
    db = SessionLocal()
    result = {
        "run_id": None,
        "articles_collected": 0,
        "articles_classified": 0,
        # ... other fields
        "status": "failed",
        "error": None
    }

    try:
        # Step 1: Collect articles from Factiva (sole source)
        step_start = datetime.utcnow()
        self.logger.info("step_1_collection_started")

        factiva_collector = FactivaCollector()

        # Verify Factiva is configured
        if not factiva_collector.is_configured():
            error_msg = "Factiva not configured (missing MMC_API_BASE_URL or MMC_API_KEY)"
            self.logger.error("factiva_not_configured", error=error_msg)
            result["error"] = error_msg
            await self._send_admin_alert(error_msg, result)
            return result

        # Load query params from database config
        factiva_config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
        if not factiva_config or not factiva_config.enabled:
            error_msg = "Factiva disabled in admin dashboard"
            self.logger.warning("factiva_disabled", error=error_msg)
            result["error"] = error_msg
            return result

        query_params = {
            "industry_codes": factiva_config.industry_codes or "",
            "company_codes": factiva_config.company_codes or "",
            "keywords": factiva_config.keywords or "",
            "page_size": factiva_config.page_size or 25,
            "date_range_hours": factiva_config.date_range_hours or 48,
        }

        # Collect articles (raises exception on failure after retries)
        try:
            factiva_articles = factiva_collector.collect(query_params)
        except Exception as e:
            error_msg = f"Factiva collection failed after retries: {str(e)}"
            self.logger.error("factiva_collection_failed", error=error_msg, exc_info=True)
            result["error"] = error_msg
            await self._send_admin_alert(error_msg, result)
            return result

        # Handle zero articles (not an error — system working, just no results)
        if not factiva_articles:
            self.logger.info("factiva_returned_zero_articles", message="Generating empty brief")
            # Continue pipeline to generate "No articles today" brief

        # URL-dedup against today's existing articles
        from datetime import date as date_type
        from sqlalchemy import func as sqla_func
        today = date_type.today()
        existing_urls = set(
            url for (url,) in db.query(NewsArticle.source_url).filter(
                sqla_func.date(NewsArticle.created_at) == today,
                NewsArticle.source_url.isnot(None)
            ).all()
        )
        pre_url_dedup = len(factiva_articles)
        factiva_articles = [a for a in factiva_articles if a.get("url") not in existing_urls]
        self.logger.info("url_dedup_complete", before=pre_url_dedup, after=len(factiva_articles))

        # Semantic dedup (handles wire service near-duplicates)
        if len(factiva_articles) > 1:
            from app.services.deduplicator import ArticleDeduplicator
            deduplicator = ArticleDeduplicator()
            pre_semantic_dedup = len(factiva_articles)
            factiva_articles = deduplicator.deduplicate(factiva_articles)
            self.logger.info("semantic_dedup_complete",
                           before=pre_semantic_dedup,
                           after=len(factiva_articles))

        # Store articles (creates Run record internally)
        articles_collected = self.collector.store_factiva_articles(factiva_articles)
        result["articles_collected"] = articles_collected

        step_duration = (datetime.utcnow() - step_start).total_seconds()
        self.logger.info(
            "step_1_collection_completed",
            articles_collected=articles_collected,
            duration_seconds=round(step_duration, 2)
        )

        # Continue with Step 2: Query articles...
```

**Source:** Based on existing pipeline.py lines 519-598, simplified to remove fallback logic

### Example 2: Deduplication Interface (No Changes)

```python
# app/services/deduplicator.py — Keep exactly as-is

class ArticleDeduplicator:
    """
    Identifies and merges semantically similar articles using sentence transformers.

    Works with articles from any source — generic interface supports future
    source additions without modification.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.85
    ):
        """Initialize with configurable model and threshold."""
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self._model = None

    def deduplicate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate articles by semantic similarity.

        Args:
            articles: List of dicts with keys: title, description, source_name

        Returns:
            Deduplicated list with merged source_name for duplicates
        """
        if len(articles) <= 1:
            return articles

        # Generate embeddings for title + description
        texts = [f"{a['title']} {a.get('description', '')}" for a in articles]
        embeddings = self._model.encode(texts, convert_to_tensor=True)

        # Find similar pairs (cosine similarity >= 0.85)
        cos_scores = util.cos_sim(embeddings, embeddings)
        # ... grouping and merging logic ...

        return deduplicated
```

**Source:** Existing app/services/deduplicator.py (lines 37-171) — no changes needed

### Example 3: FactivaCollector.is_configured() Check

```python
# app/services/pipeline.py — Factiva readiness check

factiva_collector = FactivaCollector()

# Verify required configuration before attempting collection
if not factiva_collector.is_configured():
    error_msg = "Factiva not configured (check MMC_API_BASE_URL and MMC_API_KEY)"
    self.logger.error("pipeline_blocked_factiva_not_configured")
    result["error"] = error_msg
    await self._send_admin_alert(error_msg, result)
    return result

# Load FactivaConfig from database
factiva_config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
if not factiva_config or not factiva_config.enabled:
    self.logger.warning("factiva_disabled_in_dashboard")
    result["error"] = "Factiva collection disabled"
    return result
```

**What to verify in is_configured():**
- MMC_API_BASE_URL is set (required for API calls)
- MMC_API_KEY is set (required for X-Api-Key header)

**What NOT to verify:**
- FactivaConfig.enabled flag — that's a runtime check in pipeline
- Database connectivity — SessionLocal() handles that separately
- Network connectivity — let httpx raise exception naturally

**Source:** Existing FactivaCollector.is_configured() at app/collectors/factiva.py line 84-86

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Multi-source collection with Apify actors | Single-source Factiva API | Phase 14 (v1.2) | Simpler, faster, more reliable |
| Fallback chain (Factiva → Apify/RSS) | Direct Factiva call, no fallback | Phase 15 (v1.2) | Clearer failure modes, easier debugging |
| Generic NewsSource ABC with 6 implementations | NewsSource ABC with 0 implementations (kept for future) | Phase 15 (v1.2) | Reduced code surface, kept extensibility |
| apify-client + feedparser dependencies | httpx only (via FactivaCollector) | Phase 15 (v1.2) | Fewer external dependencies, smaller attack surface |
| Source health monitoring for Apify sources | Source health monitoring disabled | Phase 15 (v1.2) | Health checks only relevant for multi-source setup |

**Deprecated/outdated:**
- **ApifyCollector class**: Replaced by FactivaCollector in Phase 14, now being removed in Phase 15
- **Apify source implementations**: All 6 source-specific scrapers (artemis.py, business_insurance.py, etc.) are dead code
- **RSS feed parsing**: feedparser library no longer needed without RSS sources
- **INSURANCE_FALLBACK_SOURCES list**: Hardcoded source filter for fallback path being removed
- **Source type enum value APIFY**: SourceType.APIFY still in database schema but unused (safe to deprecate, risky to remove)

## Open Questions

### 1. Database Schema: Remove Apify-Specific Columns?

**What we know:**
- `news_articles.collector_source` is used by FactivaCollector to set "Factiva" value
- `sources.actor_id` is Apify-specific (stores Apify actor ID)
- `sources.source_type` enum has APIFY and RSS values

**What's unclear:**
- Risk/benefit of dropping `sources.actor_id` column (migration required)
- Risk/benefit of removing SourceType.APIFY enum value (breaks existing Source rows)

**Recommendation:** Keep database schema as-is for Phase 15. Schema changes are high-risk migrations with minimal benefit. The unused columns are harmless and preserve option to re-enable Apify sources in emergency. If we remove schema elements and later need emergency fallback, we'd have to restore via migration.

### 2. Source Health Monitoring: Disable or Remove?

**What we know:**
- SourceHealthMonitor checks all enabled Source rows for collection health
- With no Apify sources, all Source rows will be disabled
- Health check currently runs in Step 1b of pipeline

**What's unclear:**
- Whether to disable health check (skip Step 1b) or keep it for future sources
- Whether disabled sources should appear in admin dashboard

**Recommendation:** Keep health monitoring code but disable Step 1b execution in pipeline. Comment out the health check call with note "Re-enable when multi-source collection is restored (Phase 17+)". This preserves the monitoring infrastructure for future use without overhead of checking zero sources.

### 3. base.py Interface: Full ABC or Minimal Stub?

**What we know:**
- NewsSource ABC defines `scrape()` method returning `List[Dict[str, Any]]`
- No implementations remain after cleanup (all 6 source files being deleted)
- FactivaCollector doesn't implement NewsSource ABC

**What's unclear:**
- Whether to keep full ABC with abstract methods
- Whether to simplify to empty class as placeholder
- Whether base.py provides value without implementations

**Recommendation:** Keep base.py with full NewsSource ABC interface unchanged. The abstract interface documents the contract for future source implementations (Phase 17+) and costs nothing to maintain. Removing it would mean re-designing the interface when multi-source support is needed again.

**Rationale:**
```python
# Keep this interface as reference documentation
class NewsSource(ABC):
    """Abstract base for news source scrapers."""

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """Return articles matching standard schema."""
        pass
```

This documents the expected article dict schema (`title`, `description`, `url`, `published_at`, `source_name`) for future implementers.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: app/services/pipeline.py (current fallback implementation)
- Codebase analysis: app/collectors/factiva.py (retry logic, error handling)
- Codebase analysis: app/services/collector.py (ApifyCollector to be removed)
- Codebase analysis: app/services/deduplicator.py (semantic dedup to retain)
- Codebase analysis: requirements.txt (dependencies to remove)
- Codebase analysis: app/config.py (settings to remove)
- Codebase analysis: .env.example (configuration blocks to remove)
- Phase 14 verification: .planning/phases/14-factivacollector-port/14-VERIFICATION.md
- Phase context: .planning/phases/15-pipeline-simplification-cleanup/15-CONTEXT.md

### Secondary (MEDIUM confidence)
- Python tenacity documentation: Retry decorator patterns (verified via codebase usage)
- sentence-transformers documentation: Model loading and embedding generation (verified via codebase usage)

### Tertiary (LOW confidence)
- None — all findings based on direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Dependencies verified in requirements.txt, usage verified via grep
- Architecture: HIGH — Pipeline code inspected directly, fallback paths traced through codebase
- Pitfalls: HIGH — Based on actual codebase patterns and common refactoring mistakes
- Open questions: MEDIUM — Schema changes are inherently uncertain without production data inspection

**Research date:** 2026-02-26
**Valid until:** 2026-03-29 (30 days for stable codebase cleanup task)
