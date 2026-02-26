# Phase 14: FactivaCollector Port - Research

**Researched:** 2026-02-26
**Domain:** HTTP API client, MMC Core API integration, Factiva/Dow Jones news collection
**Confidence:** HIGH

## Summary

Phase 14 ports BrasilIntel's proven FactivaCollector (453 lines) to MDInsights as the foundation before cleanup. The BrasilIntel implementation has been production-tested and refined through 6 Factiva-related commits, addressing critical issues like URL encoding, API parameter alignment, and keyword search strategies.

**Key differences between implementations:**
- **BrasilIntel** (reference): `date_range_hours` parameter, URL-encoded article IDs, API params (`industry`, `company`, `query`), OR-joined keywords
- **MDInsights** (current): Fixed 24h window, no URL encoding, different API params (`industryCodes`, `companyCodes`, `keywords`), space-joined keywords

**Critical discovery:** MDInsights current implementation uses INCORRECT API parameter names (`industryCodes`, `companyCodes`, `keywords`) that don't match the MMC Core API specification. BrasilIntel commit `a1e523f` documents the alignment to correct API spec with params: `industry`, `company`, `query`.

**Primary recommendation:** Port BrasilIntel's mature patterns including configurable date range, URL encoding, correct API parameter names, and OR-joined keywords for broader coverage.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | Latest stable | Async HTTP client | Modern replacement for requests, better async support, timeout handling |
| tenacity | 8.x | Retry with exponential backoff | Industry standard for resilient API calls, decorator-based API |
| structlog | Latest | Structured logging | Consistent with project logging strategy, JSON-friendly output |
| urllib.parse | stdlib | URL encoding | Python standard library, reliable quote() function for path segments |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy | 2.x | ORM and database | Already in use for SessionLocal, ApiEvent, FactivaConfig models |
| datetime | stdlib | Date/time handling | UTC timezone handling, timedelta for date range calculations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | aiohttp | httpx already used in project, simpler sync/async API |
| tenacity | backoff | tenacity more feature-rich, better exception handling |
| urllib.parse.quote | requests.utils.quote | stdlib avoids dependency, safe='' pattern for paths |

**Installation:**
```bash
# All dependencies already in MDInsights requirements.txt
pip install httpx tenacity structlog sqlalchemy
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── collectors/          # Collection layer
│   ├── factiva.py      # FactivaCollector class (port from BrasilIntel)
│   └── equity.py       # EquityPriceClient (existing)
├── models/             # ORM models
│   ├── factiva_config.py  # Configuration model (existing)
│   └── api_event.py    # Event tracking (existing)
└── services/           # Business logic
    └── pipeline.py     # Orchestrator (existing, will be simplified in Phase 15)
```

### Pattern 1: Collector with Configuration Injection
**What:** Collector reads Settings on init, loads FactivaConfig row at collection time
**When to use:** Allows dynamic config changes without restart
**Example:**
```python
class FactivaCollector:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url: str = settings.mmc_api_base_url.rstrip("/")
        self.api_key: str = settings.mmc_api_key

    def collect(self, query_params: Dict[str, Any], run_id: Optional[int] = None):
        # query_params comes from FactivaConfig row fetched by pipeline
        date_range_hours = int(query_params.get("date_range_hours", 48))
        # ...
```

### Pattern 2: Graceful Degradation on Article Fetch
**What:** Individual article body fetch failures fall back to search snippet
**When to use:** Prevents entire collection failure when single articles unavailable
**Example:**
```python
def _fetch_article(self, article_id: str) -> Dict[str, Any]:
    url = f"{self.base_url}{self.BASE_ARTICLE_PATH}/{quote(article_id, safe='')}"
    response = client.get(url, headers=self._build_headers())

    # 4xx = article unavailable (not found, paywalled, access denied)
    if 400 <= response.status_code < 500:
        self.logger.warning("factiva_article_client_error", article_id=article_id)
        return {}  # Normalizer will use snippet fallback

    response.raise_for_status()  # Propagate 5xx errors
    return response.json()
```

### Pattern 3: Isolated Event Recording
**What:** Event recording opens own DB session, never crashes collection flow
**When to use:** ApiEvent tracking must never interfere with primary operation
**Example:**
```python
def _record_event(self, event_type, success, detail, run_id):
    try:
        with SessionLocal() as session:  # Isolated session
            event = ApiEvent(...)
            session.add(event)
            session.commit()
    except Exception as exc:
        # Never propagate DB errors into collection flow
        self.logger.warning("api_event_record_failed", error=str(exc))
```

### Pattern 4: URL Encoding for Path Segments
**What:** Use `quote(article_id, safe='')` to encode article IDs in URL paths
**When to use:** When inserting dynamic values into URL paths (not query params)
**Why critical:** Article IDs may contain special characters that break URLs if not encoded
**Example:**
```python
from urllib.parse import quote

# WRONG (current MDInsights): No encoding
url = f"{self.base_url}/article/{article_id}"

# CORRECT (BrasilIntel pattern): URL-encode path segment
url = f"{self.base_url}/article/{quote(article_id, safe='')}"
```
**Source:** BrasilIntel commit `21157a3` - "fix: URL-encode article IDs in Factiva detail fetch"

### Pattern 5: API Parameter Name Alignment
**What:** Use exact parameter names from API specification: `industry`, `company`, `query`
**When to use:** When building search query params for MMC Core API
**Why critical:** Incorrect param names cause API to ignore filters, returning unfiltered results
**Example:**
```python
# WRONG (current MDInsights): Incorrect param names
params = {
    "industryCodes": ",".join(industry_codes),  # API doesn't recognize this
    "companyCodes": ",".join(company_codes),    # API doesn't recognize this
    "keywords": " ".join(keywords),              # API doesn't recognize this
}

# CORRECT (BrasilIntel pattern): Aligned with API spec
params = {
    "industry": ",".join(industry_codes),  # API recognizes this
    "company": ",".join(company_codes),    # API recognizes this
    "query": " OR ".join(keywords),        # API recognizes this, OR for broader coverage
}
```
**Source:** BrasilIntel commit `a1e523f` - "fix: align FactivaCollector query params with MMC Recent News API spec"

### Pattern 6: Configurable Date Range
**What:** Use `date_range_hours` parameter instead of fixed 24h lookback
**When to use:** Provides flexibility for different collection schedules and backfill scenarios
**Example:**
```python
# WRONG (current MDInsights): Fixed 24h window
yesterday = today - timedelta(days=1)

# CORRECT (BrasilIntel pattern): Configurable hours
date_range_hours = int(query_params.get("date_range_hours", 48))
lookback = today - timedelta(hours=date_range_hours)
```

### Anti-Patterns to Avoid
- **Auto-committing in collector:** Collector returns data, pipeline handles persistence
- **Suppressing 5xx errors:** Only suppress 4xx (client errors), propagate 5xx (server errors)
- **Infinite retries:** Always use `stop_after_attempt(n)` to prevent runaway retries
- **Blocking on event recording:** DB failures in event tracking must never crash collection

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry logic | Custom retry loops | tenacity decorators | Handles exponential backoff, jitter, exception filtering, max attempts |
| URL encoding | String replacement | urllib.parse.quote() | Handles edge cases, unicode, reserved chars correctly |
| HTTP timeouts | Default httpx | Client(timeout=30.0) | Prevents hanging on slow/dead connections |
| Date range calc | Manual arithmetic | timedelta(hours=N) | Handles DST, leap seconds, timezone math |
| JSON logging | print() statements | structlog.bind() | Structured, filterable, context-aware logs |

**Key insight:** HTTP client resilience is complex - connection pooling, timeout handling, retry logic, and error classification require battle-tested libraries. Don't reimplement these patterns.

## Common Pitfalls

### Pitfall 1: Incorrect API Parameter Names
**What goes wrong:** API ignores unrecognized parameters, returns unfiltered results consuming quota and returning irrelevant articles
**Why it happens:** API documentation uses different naming than expected (industry vs industryCodes)
**How to avoid:** Reference BrasilIntel commit `a1e523f` for confirmed working parameter names
**Warning signs:**
- Search returns articles outside specified industries
- Keyword filtering doesn't work
- Company code filtering ineffective
**Fix:** Use `industry`, `company`, `query` as parameter names, not `industryCodes`, `companyCodes`, `keywords`

### Pitfall 2: Missing URL Encoding on Article IDs
**What goes wrong:** Article fetch returns 400/404 errors when article ID contains special characters
**Why it happens:** Article IDs may include slashes, spaces, or other URL-unsafe characters
**How to avoid:** Always use `quote(article_id, safe='')` when inserting into URL path
**Warning signs:**
- Intermittent 400/404 errors on article fetch
- Errors correlate with specific article IDs
- Error rate varies by source/publisher
**Fix:** `url = f"{base}{path}/{quote(article_id, safe='')}"`

### Pitfall 3: Keyword Joining Strategy
**What goes wrong:** Space-separated keywords use implicit AND logic, returning too few results
**Why it happens:** Factiva API treats space-separated terms as required (AND), not optional (OR)
**How to avoid:** Join keywords with " OR " for broader coverage
**Warning signs:**
- Very low article counts
- Missing obviously relevant articles
- Coverage improves when reducing keyword count
**Fix:** `params["query"] = " OR ".join(keywords)`
**Source:** BrasilIntel commit `96db169` - "fix: join Factiva keywords with OR for broader search coverage"

### Pitfall 4: Fixed 24h Lookback Window
**What goes wrong:** Can't adjust for different schedules (weekend runs, backfill, testing)
**Why it happens:** Hard-coded timedelta(days=1) instead of configurable parameter
**How to avoid:** Use `date_range_hours` parameter with sensible default (48h)
**Warning signs:**
- Weekend runs miss Friday articles
- Can't backfill missed periods
- Testing requires code changes
**Fix:** `date_range_hours = int(query_params.get("date_range_hours", 48))`

### Pitfall 5: Inconsistent Field Naming (url vs source_url)
**What goes wrong:** Normalized article dict uses `url` but NewsArticle model expects `source_url`
**Why it happens:** Different naming conventions between systems
**How to avoid:** Check target schema before implementing normalizer
**Warning signs:**
- Articles stored with null source_url
- URL field populated but not queryable
- Broken links in reports
**Current state:** MDInsights uses `url` in normalizer (line 412), matches schema at line 34 (`source_url`)
**Action:** Keep MDInsights naming (`url` → `source_url` mapping handled in pipeline)

## Code Examples

Verified patterns from BrasilIntel production code:

### Configurable Date Range
```python
# Source: BrasilIntel app/collectors/factiva.py lines 111-116
date_range_hours = int(query_params.get("date_range_hours", 48))
today = datetime.now(timezone.utc)
lookback = today - timedelta(hours=date_range_hours)
from_date = lookback.strftime("%Y-%m-%d")
to_date = today.strftime("%Y-%m-%d")
```

### URL Encoding for Article Fetch
```python
# Source: BrasilIntel app/collectors/factiva.py line 335
from urllib.parse import quote

url = f"{self.base_url}{self.BASE_ARTICLE_PATH}/{quote(article_id, safe='')}"
```

### Correct API Parameter Names
```python
# Source: BrasilIntel app/collectors/factiva.py lines 133-145
# Industry codes
if industry_codes:
    params["industry"] = ",".join(industry_codes)

# Company codes
if company_codes:
    params["company"] = ",".join(company_codes)

# Keywords with OR joining
if keywords:
    params["query"] = " OR ".join(keywords)
```

### Tenacity Retry Pattern
```python
# Source: BrasilIntel app/collectors/factiva.py lines 263-267
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
)
def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
    # Only retries on timeout/connection errors
    # Propagates 4xx/5xx for caller to handle
```

### Graceful 4xx Handling
```python
# Source: BrasilIntel app/collectors/factiva.py lines 336-350
response = client.get(url, headers=self._build_headers())

# 4xx = article unavailable (not found, paywalled, access denied)
# Log warning and return empty dict so caller uses snippet fallback
if 400 <= response.status_code < 500:
    self.logger.warning(
        "factiva_article_client_error",
        article_id=article_id,
        status_code=response.status_code,
    )
    return {}

response.raise_for_status()  # Propagate 5xx errors
return response.json()
```

### Isolated Event Recording
```python
# Source: BrasilIntel app/collectors/factiva.py lines 434-453
def _record_event(self, event_type, success, detail, run_id):
    try:
        with SessionLocal() as session:  # Isolated session
            event = ApiEvent(
                event_type=event_type,
                api_name="news",
                timestamp=datetime.utcnow(),
                success=success,
                detail=detail[:500] if detail else None,
                run_id=run_id,
            )
            session.add(event)
            session.commit()
    except Exception as exc:
        # Never propagate DB errors into collection flow
        self.logger.warning("api_event_record_failed", error=str(exc))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed 24h window | Configurable date_range_hours | BrasilIntel production | Flexibility for schedules, backfill, testing |
| No URL encoding | quote(article_id, safe='') | Feb 2024 (BrasilIntel) | Fixes 400/404 on special chars in article IDs |
| Wrong param names | industry/company/query | Jan 2024 (BrasilIntel) | API actually filters results correctly |
| Space-joined keywords | OR-joined keywords | Jan 2024 (BrasilIntel) | Broader coverage, more articles per run |
| `is_configured()` inline | Delegate to Settings | BrasilIntel current | Consistent auth check across collectors |

**Deprecated/outdated:**
- **MDInsights API param names** (`industryCodes`, `companyCodes`, `keywords`): Don't match API spec, replaced by `industry`, `company`, `query`
- **Fixed 24h lookback**: Too inflexible, replaced by configurable `date_range_hours`
- **No URL encoding**: Causes intermittent failures, replaced by `quote(article_id, safe='')`

## Open Questions

Things that couldn't be fully resolved:

1. **Should MDInsights add date_range_hours to FactivaConfig model?**
   - What we know: BrasilIntel uses it as query_param with default 48h, not a DB field
   - What's unclear: Whether MDInsights admin UI should expose this, or keep as code default
   - Recommendation: Start with code default (48h), defer UI control to Phase 16 if needed

2. **Factiva industry code meanings (i82, i832)?**
   - What we know: BrasilIntel uses i82 only (commit `de24a47`), MDInsights defaults to "i82,i832"
   - What's unclear: Exact meaning and whether i832 is valid for insurance sector
   - Recommendation: Use i82 only initially (proven in BrasilIntel), research i832 separately
   - Research needed: Factiva Industry Classification documentation, contact MMC API support

3. **Should pipeline instantiate FactivaCollector with dependency injection?**
   - What we know: Current pipeline creates `FactivaCollector()` inline (no DI)
   - What's unclear: Whether Phase 14 should refactor to DI pattern for testability
   - Recommendation: Keep inline instantiation in Phase 14 (minimize scope), defer DI refactor to future phase

4. **Keyword seed data for insurance/reinsurance?**
   - What we know: BrasilIntel uses Portuguese "seguro,seguradora", MDInsights uses English "insurance reinsurance"
   - What's unclear: Optimal English keyword set for 4 MDInsights audience roles
   - Recommendation: Start with "insurance reinsurance" (current default), refine based on result quality in production

## Sources

### Primary (HIGH confidence)
- **BrasilIntel FactivaCollector** (C:\BrasilIntel\app\collectors\factiva.py) - Production-tested reference implementation with 6+ refinement commits
- **MDInsights FactivaCollector** (C:\MDInsights\app\collectors\factiva.py) - Current v1.1 implementation with parameter name issues
- **MDInsights FactivaConfig model** (C:\MDInsights\app\models\factiva_config.py) - Configuration schema
- **MDInsights NewsArticle model** (C:\MDInsights\app\models\news_article.py) - Target data schema
- **MDInsights Pipeline** (C:\MDInsights\app\services\pipeline.py) - Integration context
- **BrasilIntel Git History** - Commits documenting API alignment and bug fixes:
  - `21157a3`: URL encoding fix
  - `96db169`: OR-joined keywords fix
  - `a1e523f`: API parameter name alignment
  - `de24a47`: Valid industry code (i82 only)

### Secondary (MEDIUM confidence)
- [HTTPX Documentation](https://www.python-httpx.org/) - URL encoding, query params, timeout handling
- [Tenacity Documentation](https://tenacity.readthedocs.io/) - Retry patterns, exponential backoff
- [Python urllib.parse](https://docs.python.org/3/library/urllib.parse.html) - URL encoding reference

### Tertiary (LOW confidence - requires verification)
- [Factiva LibGuides](https://proquest.libguides.com/factiva) - General Factiva field codes (not specific to insurance codes i82/i832)
- [REST API Best Practices 2026](https://oneuptime.com/blog/post/2026-02-20-api-design-rest-best-practices/view) - General pagination patterns
- General search results on Factiva industry codes - no authoritative source found for i82/i832 definitions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use, proven patterns
- Architecture: HIGH - BrasilIntel production implementation provides verified patterns
- Pitfalls: HIGH - Documented in BrasilIntel git commits with fixes
- Industry codes: LOW - No authoritative source for i82/i832 meanings found
- API parameter names: HIGH - Verified in BrasilIntel production after alignment fix

**Research date:** 2026-02-26
**Valid until:** 90 days (stable enterprise API, proven implementation patterns)

**Critical findings:**
1. MDInsights current implementation has 3 major bugs that BrasilIntel already fixed
2. API parameter names must be: `industry`, `company`, `query` (not `industryCodes`, `companyCodes`, `keywords`)
3. URL encoding is required for article ID path segments
4. OR-joined keywords provide better coverage than space-separated
5. Configurable date range (48h default) more flexible than fixed 24h
