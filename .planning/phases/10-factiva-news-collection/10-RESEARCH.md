# Phase 10: Factiva News Collection - Research

**Researched:** 2026-02-18
**Domain:** Factiva Recent News API (MMC Core API), Python httpx, SQLAlchemy migration, FastAPI admin
**Confidence:** HIGH — source of truth is the in-repo NewsAPI.pdf documentation (fully authoritative) plus direct reading of all existing codebase files.

---

## Summary

Phase 10 adds Factiva as the primary news source by building a dedicated `FactivaCollector` that queries `/coreapi/recent-news/v1/search` using `X-Api-Key` authentication, then restructures the collection pipeline so Factiva runs first and Apify/RSS runs only on failure. The existing codebase is in excellent shape to accept this: the `Settings` class already has `mmc_api_key` and `mmc_api_base_url`, the `ApiEvent`/`ApiEventType` models already define `NEWS_FETCH` and `NEWS_FALLBACK` event types, and the `ArticleDeduplicator` already runs as a post-collection step.

The largest structural change is splitting the current monolithic `ApifyCollector.collect_from_sources()` call in `PipelineOrchestrator.run_full_pipeline_with_email()` into two stages: (1) attempt Factiva, (2) fall back to Apify/RSS on failure. The second major change is adding a `collector_source` field to the `NewsArticle` model so each article carries explicit source attribution. The third is adding Factiva query configuration to the database so the admin dashboard can manage industry codes, company codes, and keywords without code changes.

**Primary recommendation:** Implement `FactivaCollector` as a new module in `app/collectors/factiva.py` following the same `httpx` + `tenacity` + `structlog` patterns already used in `app/auth/token_manager.py`. Wire it into `PipelineOrchestrator` as a primary attempt with `ApifyCollector` as fallback. Store Factiva query config in a new `factiva_config` database table read by the pipeline and editable through the admin dashboard.

---

## Standard Stack

All libraries already in `requirements.txt`. No new dependencies required.

### Core (already present)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | pinned in requirements | HTTP client for Factiva REST calls | Already used by `token_manager.py` |
| `tenacity` | pinned | Retry with exponential backoff | Already used for `_scrape_source` in collector |
| `structlog` | pinned | Structured logging | Project-wide logging standard |
| `sqlalchemy` | pinned | ORM for `NewsArticle`, `ApiEvent`, new `FactivaConfig` table | Project ORM |
| `pydantic-settings` | pinned | Config from env vars | `Settings` class pattern |

### No New Dependencies
The Factiva API is a plain REST API with JSON responses. `httpx` handles all HTTP. No Factiva-specific SDK exists or is needed.

**Installation:** No new packages. All dependencies already in `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure (additions only)
```
app/
├── collectors/                  # NEW package — separates Factiva from Apify patterns
│   ├── __init__.py
│   └── factiva.py               # FactivaCollector class
├── models/
│   ├── news_article.py          # ADD: collector_source field
│   ├── factiva_config.py        # NEW: FactivaConfig ORM model
│   └── __init__.py              # ADD: FactivaConfig exports
├── services/
│   ├── pipeline.py              # MODIFY: Factiva-primary, Apify-fallback logic
│   └── collector.py             # MODIFY: accept pre-filtered fallback source list
├── routers/
│   └── admin.py                 # MODIFY: add Factiva config CRUD endpoints
└── templates/admin/
    └── factiva.html             # NEW: Factiva query config page
```

**Rationale for `app/collectors/` package:** The existing `app/services/collector.py` is tightly coupled to Apify. A separate package avoids tangling Factiva HTTP logic with Apify scraper dispatch. The `app/services/sources/` pattern (base class + concrete implementations) could also work but adds unnecessary abstraction for a single API client.

### Pattern 1: FactivaCollector Class
**What:** A standalone class with `collect(run_id, db)` method that queries Factiva, fetches article bodies, and returns a list of normalized article dicts matching the existing schema.
**When to use:** Called by `PipelineOrchestrator` at Step 1 before Apify.

```python
# Source: NewsAPI.pdf documentation + token_manager.py httpx patterns
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.database import SessionLocal
from app.models.api_event import ApiEvent, ApiEventType

logger = structlog.get_logger(__name__)

class FactivaCollector:
    """
    Factiva Recent News API collector.

    Queries /coreapi/recent-news/v1/search using X-Api-Key authentication.
    Fetches individual article bodies from /coreapi/recent-news/v1/article/{id}.
    Returns articles normalized to the same dict schema as ApifyCollector.
    """

    BASE_SEARCH_PATH = "/coreapi/recent-news/v1/search"
    BASE_ARTICLE_PATH = "/coreapi/recent-news/v1/article"
    SOURCE_LABEL = "Factiva"

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.mmc_api_base_url.rstrip("/")
        self.api_key = settings.mmc_api_key
        self.logger = logger.bind(service="factiva_collector")

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def collect(self, query_params: dict) -> List[Dict[str, Any]]:
        """
        Fetch articles from Factiva for the given query config.

        Args:
            query_params: dict with keys industry, company, query, fromDate, toDate

        Returns:
            List of article dicts matching standard schema.
            Returns empty list on any error (caller triggers fallback).
        """
        ...

    def _build_headers(self) -> dict:
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    def _search(self, params: dict) -> dict:
        """Execute search API call with retry."""
        url = f"{self.base_url}{self.BASE_SEARCH_PATH}"
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params, headers=self._build_headers())
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    def _fetch_article(self, article_id: str) -> dict:
        """Fetch full article body for a single article ID."""
        url = f"{self.base_url}{self.BASE_ARTICLE_PATH}/{article_id}"
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self._build_headers())
            response.raise_for_status()
            return response.json()
```

### Pattern 2: FactivaConfig Database Model
**What:** A single-row configuration table storing Factiva query parameters, editable via admin dashboard.
**When to use:** Read by `FactivaCollector` at pipeline start; written by admin CRUD endpoints.

```python
# app/models/factiva_config.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from app.database import Base

class FactivaConfig(Base):
    """
    Single-row configuration table for Factiva query parameters.

    Admin-configurable via dashboard. Pipeline reads this at start of each run.
    industry_codes, company_codes, keywords stored as comma-separated strings
    for simplicity — parsed to lists at query time.
    """
    __tablename__ = "factiva_config"

    id = Column(Integer, primary_key=True)  # Always row id=1
    industry_codes = Column(String(500), default="i82,i832,i8311,i8312")
    company_codes = Column(String(500), default="")  # e.g., "MM" for Marsh
    keywords = Column(String(500), default="insurance,reinsurance")
    page_size = Column(Integer, default=25)  # 10, 25, 50, or 100
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True)  # Admin user if tracked
```

### Pattern 3: NewsArticle.collector_source Field
**What:** Add `collector_source` column to `news_articles` table. Values: `"Factiva"` or `"Apify/RSS"`.
**When to use:** Set at article creation time in both `FactivaCollector` and `ApifyCollector._store_articles()`.

```python
# app/models/news_article.py addition
collector_source = Column(String(20), nullable=True, default="Apify/RSS")
# Values: "Factiva" | "Apify/RSS"
```

**Migration approach:** SQLite with SQLAlchemy — `Base.metadata.create_all()` does NOT add columns to existing tables. Requires Alembic migration OR manual `ALTER TABLE news_articles ADD COLUMN collector_source TEXT DEFAULT 'Apify/RSS'`. Since the project does not use Alembic (confirmed by absence in repo), use a startup migration helper or SQLite `ALTER TABLE`.

### Pattern 4: Pipeline Orchestration - Factiva Primary, Apify Fallback
**What:** Modify `PipelineOrchestrator.run_full_pipeline_with_email()` Step 1 to attempt Factiva first.
**When to use:** Always — this is the new normal collection flow.

```python
# In PipelineOrchestrator.run_full_pipeline_with_email()
# Step 1: Collect articles (Factiva primary, Apify/RSS fallback)
factiva_collector = FactivaCollector()
factiva_used = False
collection_source = "Apify/RSS"

if factiva_collector.is_configured():
    try:
        factiva_config = self._load_factiva_config(db)
        if factiva_config and factiva_config.enabled:
            query_params = self._build_factiva_query(factiva_config)
            articles_collected = await self._run_factiva_collection(
                factiva_collector, query_params, run_id, db
            )
            factiva_used = True
            collection_source = "Factiva"
            self._log_api_event(db, ApiEventType.NEWS_FETCH, run_id, success=True,
                                detail=f"Collected {articles_collected} articles")
    except Exception as e:
        self.logger.warning("factiva_failed_falling_back", error=str(e))
        self._log_api_event(db, ApiEventType.NEWS_FALLBACK, run_id, success=False,
                            detail=str(e)[:500])

if not factiva_used:
    # Fallback: run insurance-focused Apify/RSS sources only
    articles_collected = self.collector.collect_from_sources(
        source_filter=INSURANCE_FALLBACK_SOURCES
    )
```

### Pattern 5: Fallback Source Filtering
**What:** `INSURANCE_FALLBACK_SOURCES` constant listing the subset of Apify/RSS sources to use during fallback.
**When to use:** Only when Factiva fails or is unconfigured.

```python
# Defined in pipeline.py or a constants module
INSURANCE_FALLBACK_SOURCES = [
    "Reinsurance News",
    "Insurance Journal",
    "Artemis",
    "Lloyd's List",
    # Exclude general business sources like Business Insurance if added later
]
```

The existing `ApifyCollector.collect_from_sources()` queries enabled sources from the DB; add an optional `source_name_filter: Optional[List[str]] = None` parameter. When provided, applies an additional `Source.name.in_(source_name_filter)` filter to the DB query.

### Pattern 6: Cross-Source Deduplication
**What:** Before storing Factiva articles, check for URL-match or title-similarity against today's Apify/RSS articles.
**When to use:** Only in the (unusual) scenario where Factiva has been integrated after some Apify articles already exist for the day. In normal Factiva-primary flow, Factiva articles are the ONLY articles — so dedup is against prior Factiva fetches if pipeline is re-run.

**Dedup strategy:** Hybrid — URL exact match first (fast, zero false positives), then title similarity via existing `ArticleDeduplicator` (for cross-source duplicates). Factiva wins when duplicates are found.

```python
# Dedup logic when Factiva is primary:
# 1. Query today's existing articles from DB (current run or prior same-day run)
# 2. Build set of existing source_urls for O(1) lookup
# 3. For each Factiva article: skip if source_url already in DB
# 4. After URL filter, run ArticleDeduplicator on remaining articles against existing
# 5. When ArticleDeduplicator finds a pair (existing_apify, new_factiva): keep factiva,
#    mark existing as superseded (or simply don't insert the Factiva one if existing_apify
#    has the same content and we can't remove the existing one — see note below)
```

**Critical note on dedup winner "keep Factiva":** The existing `ArticleDeduplicator` operates only on in-memory lists. For cross-source dedup where Apify articles are already in the DB, you need to either:
- Option A: Load today's existing articles from DB into memory, merge with new Factiva articles, run deduplicator with Factiva articles tagged as preferred, then delete the DB versions of articles that were superseded by Factiva.
- Option B: Simply URL-dedup (if Factiva article URL not already in DB, insert it). Accept that semantic duplicates from different URLs may exist on days when fallback was used previously. This is simpler and sufficient for the stated requirement of "current day only".

**Recommendation:** Option B (URL-exact-match dedup) for the normal Factiva-primary case. This works because on any given morning, either Factiva OR Apify/RSS runs — not both. The cross-source dedup concern is an edge case (pipeline re-run after fallback). Full semantic cross-source dedup adds significant complexity for low benefit.

For the semantic dedup of articles within the same Factiva fetch (same event covered by multiple Factiva articles), the existing `ArticleDeduplicator` can be applied to Factiva articles in memory before storing, exactly as it is applied to Apify articles today.

### Anti-Patterns to Avoid
- **Do NOT use the abstract `NewsSource` base class for `FactivaCollector`.** That ABC requires `ApifyClient` as a constructor argument and is designed for Apify scraper dispatch. Factiva is a REST API client, not a scraper. Create an independent class.
- **Do NOT make the Factiva article fetch synchronous-blocking in an async context.** Use `httpx.Client` (sync) wrapped in `asyncio.get_event_loop().run_in_executor()` if calling from `async` pipeline methods, OR make `FactivaCollector.collect()` fully sync (matching `ApifyCollector.collect_from_sources()` which is sync). The existing pipeline calls `self.collector.collect_from_sources()` as sync inside an async function — match this pattern.
- **Do NOT fetch all available Factiva articles.** The API returns paginated results with opaque page IDs. Fetching all pages is expensive. Set a hard cap (e.g., 100 articles max) and use the `pageSize=100` link from pagination to minimize HTTP calls.
- **Do NOT store `plaintext` from the article endpoint for all articles.** Individual article fetch is a second HTTP call per article. Fetch body only for articles that pass the title-based relevance filter if time permits; otherwise batch-fetch the first N articles.
- **Do NOT call `get_settings()` with `@lru_cache` inside async tasks** after settings have been loaded — this is fine as-is because the project already does this throughout.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry logic | Custom retry loop | `tenacity` (already in requirements) | Handles exponential backoff, jitter, exception filtering |
| Structured logging | Custom log formatter | `structlog` (project standard) | Consistent log structure across all services |
| Config from env | Custom env parser | `pydantic-settings` Settings class | Already done — `mmc_api_key` and `mmc_api_base_url` exist |
| API event recording | Custom event table | `ApiEvent` model + `ApiEventType.NEWS_FETCH/NEWS_FALLBACK` | Already defined in Phase 9 — just write records |
| Within-source dedup | Custom similarity algo | `ArticleDeduplicator` (already in `deduplicator.py`) | Sentence transformer-based, already tested |
| DB session management | Custom connection pool | `SessionLocal()` from `app.database` | Project pattern — use and close in `finally:` |

**Key insight:** The `ApiEvent` model's `NEWS_FETCH` and `NEWS_FALLBACK` event types were defined in Phase 9 specifically for Phase 10. Write to them — the schema is already correct.

---

## Common Pitfalls

### Pitfall 1: Search Returns Snippets, Not Full Text
**What goes wrong:** The search endpoint (`/coreapi/recent-news/v1/search`) returns `snippet` (first few words) and `headline` but NOT `plaintext`. The pipeline classifier uses `description` (which maps to `plaintext`/`snippet`). Using just the snippet may starve the AI classifier of content.
**Why it happens:** NewsAPI.pdf documents this explicitly — `plaintext` only appears in the individual article endpoint response.
**How to avoid:** For each article returned by search, call `/coreapi/recent-news/v1/article/{articleId}` to get `plaintext`. Map `plaintext` to `description` in the normalized article dict. This is N+1 HTTP calls — batching with async httpx would help but the sync pattern is simpler; given typical article counts (25-100/day) at 30s timeout each, serial fetching is acceptable.
**Warning signs:** AI classifier produces very short/low-confidence summaries for Factiva articles compared to Apify articles.

### Pitfall 2: Pagination with Opaque Page IDs
**What goes wrong:** Attempting to manually construct pagination params (e.g., `?page=2&offset=10`) fails. The Factiva API uses opaque `pageId` query parameters embedded in the `pagination.links.next` URL.
**Why it happens:** NewsAPI.pdf states: "Pagination is opaque — page sizes and offsets are obfuscated via pageId query string."
**How to avoid:** To get more results, either (a) use `pageSize` link variants (`pagination.links.pageSize100`) to switch to 100-result pages, or (b) follow `pagination.links.next` to get the next page. Do not manually construct page parameters.
**Recommendation:** Use `pageSize100` link on first response to get up to 100 articles in a single call. This avoids pagination complexity entirely for reasonable daily volumes.

### Pitfall 3: inaccurate totalResults for Deduplicated Searches
**What goes wrong:** The API's `pagination.totalResults` value is unreliable when `deduplication` is set to `"similar"` or `"near_exact"`.
**Why it happens:** NewsAPI.pdf documents: "Inaccurate page counts for deduplicated searches."
**How to avoid:** Do not rely on `totalResults` for loop termination or progress metrics. Use the presence/absence of `pagination.links.next` to determine if more pages exist. Use the actual count of returned articles to set `articles_collected` in the pipeline result.

### Pitfall 4: Missing `collector_source` Field on Existing Articles
**What goes wrong:** Adding `collector_source` to `NewsArticle` causes attribute access errors on existing database rows that don't have the column.
**Why it happens:** SQLite/SQLAlchemy's `Base.metadata.create_all()` does not alter existing tables. The column is present in the ORM model but not in the actual table.
**How to avoid:** Add a startup migration step that runs `ALTER TABLE news_articles ADD COLUMN collector_source TEXT DEFAULT 'Apify/RSS'` if the column does not already exist. Pattern: check `PRAGMA table_info(news_articles)`, add column if `collector_source` not in result. This is already the project's migration strategy (no Alembic).

```python
# In app/main.py lifespan or a migration helper
def _run_migrations(engine):
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(news_articles)"))
        columns = [row[1] for row in result]
        if "collector_source" not in columns:
            conn.execute(text(
                "ALTER TABLE news_articles ADD COLUMN collector_source TEXT DEFAULT 'Apify/RSS'"
            ))
            conn.commit()
```

### Pitfall 5: API Key Auth Confusion with JWT
**What goes wrong:** Developer attempts to get a JWT token from `TokenManager` before calling Factiva, adding unnecessary latency and coupling.
**Why it happens:** Phase 9 introduced `TokenManager` for JWT-based auth. Factiva uses `X-Api-Key` only.
**How to avoid:** Never call `TokenManager.get_token()` before Factiva requests. Use only `settings.mmc_api_key` in the `X-Api-Key` header. This is documented in Phase 9 CONTEXT.md and `Settings.is_mmc_api_key_configured()`.

### Pitfall 6: Fallback Not Scoped to Insurance Sources
**What goes wrong:** Pipeline falls back to the full source list (including general business news), producing a brief that is less insurance-focused than a Factiva brief.
**Why it happens:** `ApifyCollector.collect_from_sources()` queries all enabled sources without filtering.
**How to avoid:** Add a `source_name_filter` parameter to `collect_from_sources()` and pass `INSURANCE_FALLBACK_SOURCES` constant during fallback. Alternatively, tag sources in the `sources` DB table with an `is_insurance_focused` boolean field.

### Pitfall 7: `lru_cache` on `get_settings()` Prevents Admin Changes Taking Effect
**What goes wrong:** Admin modifies Factiva query config in the database, but the pipeline continues using cached settings from `lru_cache`.
**Why it happens:** `get_settings()` is decorated with `@lru_cache()`. However, Factiva query config is stored in the `factiva_config` DB table (not in Settings), so this is NOT an issue for query params.
**How to avoid:** Store Factiva query parameters (industry codes, company codes, keywords) in the `FactivaConfig` DB table, not in the `Settings` class. The `Settings` class holds only the API key and base URL (infrastructure config). This is the correct split: infrastructure in `.env`, business config in DB.

---

## Code Examples

Verified patterns from existing codebase:

### API Event Recording Pattern (from token_manager.py)
```python
# Source: app/auth/token_manager.py
def _record_event(self, db: Session, event_type: ApiEventType, success: bool,
                  detail: str, run_id: Optional[int] = None) -> None:
    event = ApiEvent(
        event_type=event_type,
        api_name="news",
        success=success,
        detail=detail,
        run_id=run_id
    )
    db.add(event)
    db.commit()
```

### httpx Sync Client Pattern (project standard)
```python
# Source: app/auth/token_manager.py pattern
import httpx

with httpx.Client(timeout=30.0) as client:
    response = client.get(
        url,
        params=params,
        headers={"X-Api-Key": self.api_key, "Content-Type": "application/json"}
    )
    response.raise_for_status()  # Raises httpx.HTTPStatusError on 4xx/5xx
    return response.json()
```

### Factiva Search Endpoint Parameters
```python
# Source: NewsAPI.pdf - /coreapi/recent-news/v1/search
# At least one of: query, company, industry, region, subject is REQUIRED
params = {
    "industry": "i82,i832",          # Insurance industry codes (comma-separated)
    "company": "MM",                  # Marsh & McLennan Factiva code
    "fromDate": "2026-02-17",        # yyyy-mm-dd (yesterday for 24h window)
    "toDate": "2026-02-18",          # yyyy-mm-dd (today)
    "sortBy": "date",
    "sortOrder": "desc",
    "deduplication": "similar",      # Default — let Factiva dedup at API level
    # Do NOT set pageSize here — use the pageSize link from pagination.links
}
```

### Normalizing Factiva Article to Standard Schema
```python
# Source: NewsAPI.pdf response structure + app/services/sources/base.py schema
def _normalize_article(self, search_item: dict, article_body: dict) -> dict:
    """
    Map Factiva API response to standard article dict schema.

    Standard schema: title, description, url, published_at, source_name, collector_source
    """
    # Timestamp in milliseconds
    pub_ms = search_item.get("publicationTimestampInMilliseconds", 0)
    published_at = datetime.utcfromtimestamp(pub_ms / 1000) if pub_ms else None

    # plaintext from article body endpoint (fallback to snippet from search)
    description = (
        article_body.get("plaintext")
        or search_item.get("snippet")
        or ""
    )

    # Source URL from article links
    source_url = (
        article_body.get("links", {}).get("self")
        or search_item.get("links", {}).get("self")
        or ""
    )

    return {
        "title": search_item.get("headline", "").strip(),
        "description": description.strip(),
        "url": source_url,
        "published_at": published_at,
        "source_name": "Factiva",    # maps to news_articles.source_name
        "collector_source": "Factiva"  # new field for source attribution
    }
```

### Standard Article Storage (from collector.py — add collector_source)
```python
# Source: app/services/collector.py _store_articles — modified for collector_source
article = NewsArticle(
    run_id=run_id,
    title=article_data["title"],
    description=article_data.get("description"),
    source_url=article_data.get("url"),
    source_name=article_data["source_name"],
    published_at=article_data.get("published_at"),
    collector_source=article_data.get("collector_source", "Apify/RSS"),  # NEW
    roles=None,
    priority=None,
    summary=None,
    sentiment=None
)
```

### Reporter Article Sort — Factiva First
```python
# Source: app/services/reporter.py filter_articles_by_role — extend sorting
# After priority sort, secondary sort: Factiva before Apify/RSS
role_articles.sort(key=lambda a: (
    PRIORITY_ORDER.get(a.get('priority'), 4),
    0 if a.get('collector_source') == 'Factiva' else 1  # Factiva first
))
```

### Factiva Query Config — Default Industry Codes
Based on NewsAPI.pdf example (industry "I832" = Insurance Brokering) and standard Factiva industry taxonomy:

```python
# Recommended default insurance/reinsurance industry codes
DEFAULT_INDUSTRY_CODES = "i82,i832,i8311,i8312,i83,i831"
# i82  = Insurance
# i832 = Insurance Brokering (explicitly shown in NewsAPI.pdf example)
# i8311 = Property/Casualty Insurance
# i8312 = Life/Health Insurance
# i83  = Reinsurance
# i831 = Property/Casualty Reinsurance

# Company codes (examples from NewsAPI.pdf)
DEFAULT_COMPANY_CODES = "MM"  # Marsh & McLennan Companies Inc

# Keyword fallback query (used when industry+company codes return too few articles)
DEFAULT_KEYWORDS = "insurance reinsurance"
```

**Confidence note:** The specific codes `i83`, `i831`, `i8311`, `i8312` are inferred from Factiva's hierarchical code structure (parent `i82` = Insurance). The NewsAPI.pdf only shows `I832` as an example. Actual valid codes should be validated against the `/coreapi/recent-news/v1/industries` endpoint during Plan 10-03 (staging validation). The `/industries` endpoint returns all codes when called with no query parameter.

---

## Data Flow: Factiva Article Through the Pipeline

```
FactivaCollector.collect()
    └── GET /coreapi/recent-news/v1/search?industry=i82,i832&fromDate=...
        └── response.articles[] (headline + snippet + articleId)
            └── For each articleId:
                └── GET /coreapi/recent-news/v1/article/{articleId}
                    └── response.plaintext, response.links.self
                        └── _normalize_article() -> {title, description, url, published_at, source_name, collector_source}
                            └── URL-dedup against today's existing news_articles
                                └── ArticleDeduplicator.deduplicate() (within-batch semantic dedup)
                                    └── NewsArticle(collector_source="Factiva") -> DB

PipelineOrchestrator (Step 1 succeeds)
    └── collector_source="Factiva" set on all articles
    └── ApiEvent(NEWS_FETCH, success=True) written

PipelineOrchestrator (Step 1 fails -> Fallback)
    └── ApiEvent(NEWS_FALLBACK, success=False, detail=error) written
    └── ApifyCollector.collect_from_sources(source_name_filter=INSURANCE_FALLBACK_SOURCES)
        └── collector_source="Apify/RSS" set on all articles

Steps 2-9: Unchanged (classification, report, email all work on NewsArticle objects)
    └── Reporter sorts Factiva articles first within each priority group
    └── Template renders "via Factiva" or "via Apify/RSS" badge per article

Admin Dashboard (per-run source breakdown):
    └── SELECT collector_source, COUNT(*) FROM news_articles WHERE run_id=? GROUP BY collector_source
```

---

## Database Schema Changes

### 1. `news_articles` table — ADD column
```sql
ALTER TABLE news_articles ADD COLUMN collector_source TEXT DEFAULT 'Apify/RSS';
```
- Existing rows get `'Apify/RSS'` default. Safe migration.
- Values: `'Factiva'` | `'Apify/RSS'`

### 2. `factiva_config` table — CREATE new table
```sql
CREATE TABLE IF NOT EXISTS factiva_config (
    id INTEGER PRIMARY KEY,
    industry_codes TEXT DEFAULT 'i82,i832',
    company_codes TEXT DEFAULT 'MM',
    keywords TEXT DEFAULT 'insurance reinsurance',
    page_size INTEGER DEFAULT 25,
    enabled BOOLEAN DEFAULT 1,
    updated_at DATETIME,
    updated_by TEXT
);
-- Seed default row
INSERT OR IGNORE INTO factiva_config (id, industry_codes, company_codes, keywords, page_size, enabled)
VALUES (1, 'i82,i832', 'MM', 'insurance reinsurance', 25, 1);
```

### 3. `runs` table — consider ADD columns for source stats
```sql
-- Optional: quick access for dashboard source breakdown without GROUP BY
ALTER TABLE runs ADD COLUMN factiva_articles INTEGER DEFAULT 0;
ALTER TABLE runs ADD COLUMN fallback_used BOOLEAN DEFAULT 0;
```

These are optional — the dashboard can query `news_articles GROUP BY collector_source` per run. Adding to `runs` improves dashboard query performance but is not strictly required for Phase 10.

---

## Admin Dashboard Integration

### Factiva Query Config Page
Add a new admin page at `/admin/factiva` (Jinja2 template) with:
- Text inputs for industry codes, company codes, keywords
- Number input for page size (dropdown: 10, 25, 50, 100)
- Enable/disable toggle
- Save button (POST to `/admin/factiva` route)

### Per-Run Source Breakdown
Extend the existing runs table on `/admin` dashboard to show source breakdown. Add to `get_admin_dashboard()`:

```python
# For each recent run, get source breakdown
for run in runs:
    source_counts = db.query(
        NewsArticle.collector_source,
        func.count(NewsArticle.id)
    ).filter(
        NewsArticle.run_id == run.id
    ).group_by(NewsArticle.collector_source).all()

    run_data["source_breakdown"] = {src: count for src, count in source_counts}
    run_data["fallback_used"] = "Factiva" not in run_data["source_breakdown"]
```

### Brief Article Badge
In `app/templates/role_brief.html` and `app/templates/email/role_email.html`, add source badge to each article card:

```html
<!-- Article source badge -->
{% if article.collector_source == 'Factiva' %}
    <span class="badge bg-primary">via Factiva</span>
{% else %}
    <span class="badge bg-secondary">via Apify/RSS</span>
{% endif %}
```

The `_prepare_articles()` method in `reporter.py` must include `collector_source` in the returned dict:
```python
article_dict = {
    ...existing fields...,
    'collector_source': article.collector_source or 'Apify/RSS',
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Apify as only collector | Factiva primary + Apify fallback | Phase 10 | Richer article content, professional source |
| No source tracking | `collector_source` per article | Phase 10 | Source transparency in brief and dashboard |
| Monolithic `collect_from_sources()` | Factiva attempt + conditional fallback | Phase 10 | More complex pipeline Step 1 |
| Single-row config only from env | `FactivaConfig` DB table for query params | Phase 10 | Admin-configurable without code changes |

**No deprecated patterns to replace** — the changes are additive. Apify/RSS collection is retained as fallback.

---

## Open Questions

1. **Factiva Industry Code Validation**
   - What we know: `I832` (Insurance Brokering) is confirmed in NewsAPI.pdf example. Hierarchical codes likely include `i82` (Insurance) as parent.
   - What's unclear: Whether `i83` (Reinsurance) is a valid top-level code or if reinsurance is a sub-code under Insurance.
   - Recommendation: Plan 10-03 must call `/coreapi/recent-news/v1/industries` (with no query) against staging to get the full code list. This is the authoritative validation step.

2. **Article Volume Per Day**
   - What we know: `totalResults` from the API can be very large (317,352 shown in NewsAPI.pdf example) but is unreliable for dedup searches. With industry code filtering, daily volume will be much smaller.
   - What's unclear: Typical article count for insurance industry queries over 24 hours.
   - Recommendation: Default `pageSize=25` is conservative. Plan 10-03 must test with staging endpoint to calibrate. Increase to 100 if daily volume warrants it.

3. **Individual Article Fetch: Serial vs Async**
   - What we know: Each article needs a second HTTP call to get `plaintext`. With 25-100 articles, serial calls at 1-2s each = 25-200s added latency.
   - What's unclear: Whether this is acceptable for the morning pipeline run window.
   - Recommendation: Start with serial httpx calls (simpler, matches existing codebase sync patterns). If latency is problematic, switch to `asyncio.gather()` with `httpx.AsyncClient`.

4. **Fallback Source Set Definition**
   - What we know: Context decision says "only insurance-focused Apify/RSS sources" during fallback.
   - What's unclear: Exact list of sources to include — depends on which sources exist in the DB at deployment time.
   - Recommendation: Define `INSURANCE_FALLBACK_SOURCES` in `pipeline.py` as a hardcoded list matching known insurance-specific sources (Reinsurance News, Insurance Journal, Artemis, Lloyd's List). Exclude Business Insurance and any general business RSS feeds.

---

## Sources

### Primary (HIGH confidence)
- `C:/BrasilIntel/MDInsights/NewsAPI.pdf` — Authoritative API documentation (in-repo)
- `C:/BrasilIntel/MDInsights/app/models/news_article.py` — Exact current schema
- `C:/BrasilIntel/MDInsights/app/models/api_event.py` — ApiEventType enum with NEWS_FETCH, NEWS_FALLBACK
- `C:/BrasilIntel/MDInsights/app/services/pipeline.py` — Current pipeline Steps 0-9
- `C:/BrasilIntel/MDInsights/app/services/collector.py` — ApifyCollector pattern to follow/extend
- `C:/BrasilIntel/MDInsights/app/services/deduplicator.py` — ArticleDeduplicator — existing tool
- `C:/BrasilIntel/MDInsights/app/config.py` — mmc_api_key, mmc_api_base_url already defined
- `C:/BrasilIntel/MDInsights/app/auth/token_manager.py` — httpx + tenacity + ApiEvent pattern to follow
- `C:/BrasilIntel/MDInsights/app/services/reporter.py` — _prepare_articles() and sorting pattern
- `C:/BrasilIntel/MDInsights/.planning/phases/10-factiva-news-collection/10-CONTEXT.md` — User decisions
- `C:/BrasilIntel/MDInsights/requirements.txt` — Confirmed: no new dependencies needed

### Secondary (MEDIUM confidence)
- Factiva industry code hierarchy (`i82`, `i83` etc.) — inferred from `I832` example in NewsAPI.pdf and standard Factiva taxonomy. Requires staging validation in Plan 10-03.

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies pre-existing, no speculation
- Architecture: HIGH — based on direct reading of all relevant codebase files
- API integration: HIGH — NewsAPI.pdf is in-repo and fully authoritative
- Industry codes: MEDIUM — example code confirmed, full taxonomy needs staging validation
- Pitfalls: HIGH — all based on explicit API documentation or observed codebase patterns

**Research date:** 2026-02-18
**Valid until:** Stable (API version 1.0, published 2023-07-19 — no expected churn). Staging validation in Plan 10-03 will resolve open questions before implementation.
