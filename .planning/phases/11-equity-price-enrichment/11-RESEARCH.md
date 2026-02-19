# Phase 11: Equity Price Enrichment - Research

**Researched:** 2026-02-18
**Domain:** Equity Price API client (MMC Core API), SQLAlchemy ORM table, pipeline enrichment step, Jinja2 template inline display
**Confidence:** HIGH — all findings are based on direct reading of in-repo source files. No external API documentation was accessible (equity PDFs are image-based). API shape is inferred from the Factiva collector pattern as a confirmed parallel.

---

## Summary

Phase 11 adds equity price enrichment to the pipeline. After AI classification produces entities extracted from articles, the pipeline looks up a DB-stored entity-to-ticker mapping and calls the MMC Core API equity price endpoint for each mapped entity. The returned price data is attached to each article dict before report generation. The HTML brief templates are then updated to render this data inline within each article card.

The codebase is already well-prepared for this phase. `ApiEventType` already defines `EQUITY_FETCH` and `EQUITY_FALLBACK`. `Settings.is_mmc_api_key_configured()` covers the auth check. `FactivaCollector` in `app/collectors/factiva.py` is the definitive pattern for a sync `httpx` + `tenacity` + structlog + `_record_event` API client. The `FactivaConfig` ORM model and its admin page are the definitive patterns for a single-row admin configuration table and its CRUD UI.

Phase 11 introduces three additions: (1) an `EquityTicker` ORM model that persists entity-to-ticker mappings as individual DB rows (admin-managed, many rows), (2) an `EquityPriceClient` in `app/collectors/equity.py` that queries the equity endpoint per ticker and returns enrichment dicts with graceful fallback, and (3) a pipeline enrichment step (Step 3b) inserted between classification and report generation that calls the client per article and attaches results as an `equity_data` key on each article dict.

**Primary recommendation:** Model Phase 11 entirely on the Phase 10 Factiva pattern. Same HTTP client style (`httpx.Client`, `tenacity`, `X-Api-Key`), same event recording pattern (`ApiEvent` with `EQUITY_FETCH`/`EQUITY_FALLBACK`), same admin config pattern (ORM model + `GET`/`POST` admin route + Jinja2 form template). The only structural difference is that `EquityTicker` is a multi-row table (one row per mapping) rather than a single config row.

---

## Standard Stack

All libraries already in `requirements.txt`. No new dependencies required.

### Core (already present)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | pinned | HTTP client for equity REST calls | Already used by `factiva.py` and `token_manager.py` |
| `tenacity` | pinned | Retry with exponential backoff | Already used in `factiva.py` for transient failures |
| `structlog` | pinned | Structured logging | Project-wide logging standard |
| `sqlalchemy` | pinned | ORM for `EquityTicker` mapping table | Project ORM |
| `jinja2` | pinned | HTML brief templates | Reporter service standard |
| `pydantic-settings` | pinned | Settings access | `get_settings()` pattern |

### No New Dependencies
The equity endpoint is a plain REST API returning JSON. All tooling already present.

**Installation:** No new packages.

---

## Architecture Patterns

### Additions to Project Structure
```
app/
├── collectors/
│   ├── factiva.py           # EXISTING — reference pattern
│   └── equity.py            # NEW: EquityPriceClient class
├── models/
│   ├── equity_ticker.py     # NEW: EquityTicker ORM model (multi-row mapping table)
│   └── __init__.py          # UPDATE: export EquityTicker
├── routers/
│   └── admin.py             # UPDATE: add /admin/equity GET + POST routes
├── services/
│   └── pipeline.py          # UPDATE: add Step 3b equity enrichment
└── templates/
    ├── admin/
    │   └── equity.html      # NEW: admin equity mapping config page
    └── role_brief.html      # UPDATE: inline equity display in article card
    └── email/
        └── role_email.html  # UPDATE: inline equity display (table-safe)
```

### Pattern 1: EquityPriceClient (models factiva.py exactly)

The client follows the identical structure as `FactivaCollector`:

```python
# Source: app/collectors/factiva.py — reference implementation
class EquityPriceClient:
    BASE_PATH = "/coreapi/equity-price/v1/price"  # inferred — confirm from API

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.mmc_api_base_url.rstrip("/")
        self.api_key = settings.mmc_api_key
        self.logger = structlog.get_logger(__name__).bind(service="equity_client")

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _build_headers(self) -> Dict[str, str]:
        return {"X-Api-Key": self.api_key, "Accept": "application/json"}

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    def _fetch_price(self, ticker: str, exchange: str) -> Dict[str, Any]:
        url = f"{self.base_url}{self.BASE_PATH}"
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                url,
                params={"ticker": ticker, "exchange": exchange},
                headers=self._build_headers()
            )
            if 400 <= response.status_code < 500:
                self.logger.warning("equity_client_error",
                                    ticker=ticker, status=response.status_code)
                return {}
            response.raise_for_status()
            return response.json()

    def get_price(self, ticker: str, exchange: str,
                  run_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch equity price for a single ticker.

        Returns dict with price, change, change_pct on success.
        Returns None on any failure (API error, timeout, unmapped).
        Records ApiEvent regardless of outcome.
        """
        try:
            data = self._fetch_price(ticker, exchange)
            if not data:
                self._record_event(ApiEventType.EQUITY_FALLBACK, False,
                                   f"No data for {ticker}:{exchange}", run_id)
                return None
            result = {
                "ticker": ticker,
                "exchange": exchange,
                "price": data.get("price") or data.get("lastPrice"),
                "change": data.get("change") or data.get("priceChange"),
                "change_pct": data.get("changePct") or data.get("priceChangePct"),
                "currency": data.get("currency", "USD"),
                "as_of": data.get("timestamp") or data.get("asOf"),
            }
            self._record_event(ApiEventType.EQUITY_FETCH, True,
                               json.dumps({"ticker": ticker, "exchange": exchange}),
                               run_id)
            return result
        except Exception as exc:
            self.logger.warning("equity_fetch_failed", ticker=ticker, error=str(exc))
            self._record_event(ApiEventType.EQUITY_FALLBACK, False,
                               f"{type(exc).__name__}: {str(exc)[:200]}", run_id)
            return None

    def _record_event(self, event_type, success, detail=None, run_id=None):
        # Identical to factiva._record_event — isolated DB session, swallow errors
        try:
            with SessionLocal() as session:
                event = ApiEvent(
                    event_type=event_type,
                    api_name="equity",
                    timestamp=datetime.utcnow(),
                    success=success,
                    detail=detail[:500] if detail else None,
                    run_id=run_id,
                )
                session.add(event)
                session.commit()
        except Exception as exc:
            self.logger.warning("equity_event_record_failed", error=str(exc))
```

### Pattern 2: EquityTicker ORM Model (many-row table)

Unlike `FactivaConfig` (single-row), `EquityTicker` is a many-row lookup table — one row per entity-to-ticker mapping.

```python
# Source: app/models/factiva_config.py — reference for ORM style
class EquityTicker(Base):
    __tablename__ = "equity_tickers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_name = Column(String(200), nullable=False, unique=True,
                         comment="Company name as extracted by AI classification")
    ticker = Column(String(20), nullable=False,
                    comment="Exchange ticker symbol, e.g. AIG")
    exchange = Column(String(20), nullable=False, default="NYSE",
                      comment="Exchange code, e.g. NYSE, NASDAQ")
    enabled = Column(Boolean, nullable=False, default=True,
                     comment="If False, skip this mapping silently")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True)
```

**Key design notes:**
- `entity_name` must be unique — each company maps to one ticker
- `entity_name` is the exact string as extracted by AI classification (lowercase comparison should be used when matching, as AI extraction may vary in casing)
- `enabled` flag allows disabling a mapping without deleting it
- No startup migration seed needed — table starts empty, admin populates it

### Pattern 3: Pipeline Enrichment Step (Step 3b)

Insert between Step 3 (classification) and Step 4 (re-query classified articles) in `PipelineOrchestrator.run_full_pipeline()` and `run_full_pipeline_with_email()`:

```python
# In pipeline.py — after Step 3 (classify_articles), before Step 4 (re-query)
# Step 3b: Equity enrichment
self.logger.info("step_3b_equity_enrichment_started")
equity_client = EquityPriceClient()
if equity_client.is_configured():
    # Load all enabled ticker mappings into a dict for O(1) lookup
    ticker_map = {
        row.entity_name.lower(): {"ticker": row.ticker, "exchange": row.exchange}
        for row in db.query(EquityTicker).filter(EquityTicker.enabled == True).all()
    }

    # Track which tickers we've already fetched this run (dedup API calls)
    fetched_prices: Dict[str, Optional[Dict]] = {}

    for article in articles:
        # Parse entities from JSON
        entities = []
        if article.entities:
            try:
                entities = json.loads(article.entities) if isinstance(article.entities, str) else article.entities
            except Exception:
                pass

        equity_hits = []
        for entity in entities:
            entity_name = (entity.get("name") or "").lower()
            if entity_name in ticker_map:
                mapping = ticker_map[entity_name]
                cache_key = f"{mapping['ticker']}:{mapping['exchange']}"

                if cache_key not in fetched_prices:
                    fetched_prices[cache_key] = equity_client.get_price(
                        mapping["ticker"], mapping["exchange"],
                        run_id=latest_run.id
                    )

                if fetched_prices[cache_key]:
                    equity_hits.append(fetched_prices[cache_key])

        # Attach equity data to article ORM object as a transient attribute
        # (not persisted — enrichment is ephemeral, per-run)
        article._equity_data = equity_hits  # list of price dicts, may be empty

    self.logger.info("step_3b_equity_enrichment_completed",
                     tickers_fetched=len(fetched_prices))
else:
    self.logger.info("step_3b_equity_enrichment_skipped",
                     reason="MMC API key not configured")
    for article in articles:
        article._equity_data = []
```

**Critical design decision:** Equity data is NOT persisted to the database. It is attached as a transient attribute (`article._equity_data`) on the ORM object for the duration of the pipeline run. This avoids schema changes to `news_articles`, keeps the enrichment ephemeral (prices are stale by next run anyway), and requires no migration.

### Pattern 4: Passing Equity Data Through the Reporter

The `_prepare_articles()` method in `reporter.py` converts ORM objects to dicts. It must be updated to include `_equity_data`:

```python
# In reporter.py _prepare_articles()
article_dict = {
    ...existing fields...,
    'equity_data': getattr(article, '_equity_data', []),  # list of price dicts
}
```

The template then receives `article.equity_data` as a list. Each article may have 0, 1, or multiple equity entries (multiple tracked entities in one article).

### Pattern 5: Inline Equity Display in role_brief.html

Add equity data within the existing `article-body` div, after the summary and before the "Read full article" link. Display is conditional — renders nothing if `article.equity_data` is empty.

```html
<!-- Insert in article-body div, after article-summary, before article-link -->
{% if article.equity_data %}
<div class="equity-strip" style="margin: 8px 0 12px; display: flex; gap: 10px; flex-wrap: wrap;">
    {% for eq in article.equity_data %}
    <span class="equity-chip" style="
        display: inline-flex; align-items: center; gap: 6px;
        background: #f0f4ff; border: 1px solid #c7d4f0;
        border-radius: 6px; padding: 4px 10px; font-size: 0.82em; font-weight: 600;
    ">
        <span style="color: #00263e;">{{ eq.ticker }}</span>
        <span style="color: #495057;">{{ eq.price }}</span>
        {% if eq.change_pct is not none %}
            {% if eq.change_pct >= 0 %}
            <span style="color: #28a745;">+{{ "%.2f"|format(eq.change_pct) }}%</span>
            {% else %}
            <span style="color: #dc3545;">{{ "%.2f"|format(eq.change_pct) }}%</span>
            {% endif %}
        {% endif %}
    </span>
    {% endfor %}
</div>
{% endif %}
```

### Pattern 6: Admin Equity Mapping Page

Model exactly on `factiva.html` + `admin.py` `/admin/factiva` routes:

- `GET /admin/equity` — display table of all `EquityTicker` rows + add form
- `POST /admin/equity` — create new mapping
- `POST /admin/equity/{id}` — update existing row
- `DELETE /admin/equity/{id}` — delete row (HTMX removes the row)
- Template: `admin/equity.html` extending `admin/base.html`
- Add `equity` nav link to `admin/base.html` sidebar

### Anti-Patterns to Avoid

- **Persisting equity prices to DB**: Prices are run-ephemeral. Do not add columns to `news_articles`. The `_equity_data` transient attribute pattern is correct.
- **Blocking the pipeline on equity failure**: Any exception in equity enrichment must be caught per-ticker, not per-article. A failed ticker must not prevent other tickers or the full pipeline from completing.
- **Async equity calls**: The pipeline's `run_full_pipeline()` is sync. Follow the Factiva pattern — use `httpx.Client` (sync), not `httpx.AsyncClient`.
- **Calling the API once per article**: If 5 articles mention "AIG", call the API once and cache the result. Use `fetched_prices` dict keyed by `ticker:exchange`.
- **Case-sensitive entity matching**: AI may extract "aig", "AIG", or "Aig". Always normalize to lowercase before matching against `ticker_map`.
- **Hard-failing on missing `_equity_data` attribute**: Templates and `_prepare_articles()` must use `getattr(article, '_equity_data', [])` — the attribute won't exist on articles processed before Step 3b runs.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry with backoff | Custom retry loop | `tenacity` with `retry_if_exception_type` | Already in every collector; handles timeout/connect errors correctly |
| Structured logging | `print()` / `logging.info()` | `structlog.get_logger()` with `.bind()` | Project-wide standard; provides structured JSON logs |
| DB session isolation for events | Pass session into `_record_event` | Open own session inside `_record_event`, swallow errors | Same pattern as `factiva._record_event` — prevents event recording from interfering with pipeline transaction |
| Jinja2 number formatting | Manual string formatting | Jinja2's `"%.2f"|format()` filter | Already available in the template environment |

---

## Common Pitfalls

### Pitfall 1: Equity API endpoint path unknown (image-only PDF)
**What goes wrong:** The equity PDFs (`equityaip.pdf`, `equityref.pdf`) are image-based and cannot be text-extracted. The exact API path, query parameters, and response schema are not confirmed.
**Why it happens:** Documentation is not machine-readable.
**How to avoid:** Use a placeholder path (`/coreapi/equity-price/v1/price`) as a best guess based on the Factiva path pattern (`/coreapi/recent-news/v1/search`). Write the client with a configurable `BASE_PATH` class attribute so it can be corrected without touching request logic. Log the actual URL called at INFO level so the team can verify it against network traffic on first run.
**Warning signs:** 404 or 401 on first equity call — check the path and that `X-Api-Key` is present in the request.

### Pitfall 2: Entity name mismatch between AI extraction and mapping table
**What goes wrong:** AI extracts "American International Group" but admin mapped "AIG". Zero matches.
**Why it happens:** AI uses full legal names; admins enter ticker symbols or short names.
**How to avoid:** Admin UI should display the `entity_name` field with explicit help text: "Enter the company name exactly as it appears in article classifications. Check the Article Search page to see actual extracted entity names." Consider also noting this in the mapping table UI.
**Warning signs:** `equity_tickers` table has rows but zero equity chips appear in the brief. Check `entity_tracker` section of the brief for the actual entity names being extracted.

### Pitfall 3: `_equity_data` missing on articles not yet enriched
**What goes wrong:** `article._equity_data` raises `AttributeError` in template or reporter.
**Why it happens:** Articles queried before enrichment step won't have the attribute if code path skips enrichment.
**How to avoid:** Always use `getattr(article, '_equity_data', [])` in `_prepare_articles()`. Never access directly.

### Pitfall 4: Logging too many "entity not mapped" events
**What goes wrong:** With 20 articles each mentioning 3-5 entities, pipeline logs 60-100 "unmapped" warnings per run, flooding logs.
**Why it happens:** Unmapped entities are the normal state — most entities won't be mapped.
**How to avoid:** Do NOT log at WARNING for unmapped entities. Log at DEBUG or not at all. Only log when a mapped entity's API call fails (that warrants a WARNING). Log a single INFO summary at the end: "equity_enrichment_completed, tickers_fetched=N, articles_enriched=M".

### Pitfall 5: Double-fetching the same ticker
**What goes wrong:** 10 articles mention "AIG" — 10 API calls made instead of 1.
**Why it happens:** Naive per-article-per-entity loop without caching.
**How to avoid:** Use `fetched_prices` dict keyed by `"{ticker}:{exchange}"` — populate on first fetch, reuse for subsequent articles. This is critical for both performance and API rate limit compliance.

### Pitfall 6: Equity data missing in email template
**What goes wrong:** Equity chips appear in the browser brief but not in emailed briefs.
**Why it happens:** `role_email.html` (email template) is a separate file from `role_brief.html` — both must be updated.
**How to avoid:** Update both `role_brief.html` (browser) and `email/role_email.html` (email) in Plan 11-03. The email template uses table-based layout, so the equity chip must use `<td>` elements or inline-block `<span>` elements compatible with email clients.

### Pitfall 7: Equity enrichment step runs before classification
**What goes wrong:** `article.entities` is `None` for all articles — no equity lookups happen.
**Why it happens:** Step ordering error — enrichment inserted before classification writes entity data.
**How to avoid:** Step 3b must run AFTER Step 3 (`classify_articles`), which is when `entities` is written. The plan must be explicit: enrich the in-memory `articles` list (the same objects passed to classifier), after the classifier has populated their `.entities` field.

---

## Code Examples

### Loading Ticker Map from DB

```python
# Source: inferred from factiva_config pattern in pipeline.py
from app.models.equity_ticker import EquityTicker

ticker_map = {
    row.entity_name.lower(): {"ticker": row.ticker, "exchange": row.exchange}
    for row in db.query(EquityTicker).filter(EquityTicker.enabled == True).all()
}
# Returns {} if table is empty — enrichment gracefully skips all articles
```

### Admin Route Pattern (GET)

```python
# Source: app/routers/admin.py get_factiva_config() — reference pattern
@router.get("/equity", response_class=HTMLResponse)
def get_equity_mappings():
    db = SessionLocal()
    try:
        mappings = db.query(EquityTicker).order_by(EquityTicker.entity_name).all()
        template = jinja_env.get_template("admin/equity.html")
        return HTMLResponse(template.render(
            mappings=mappings,
            active_nav="equity",
            success=None,
            error=None,
        ))
    finally:
        db.close()
```

### Conditional Rendering in Jinja2 Template

```html
{# Only render equity strip if article has equity data #}
{% if article.equity_data %}
<div class="equity-strip">
    {% for eq in article.equity_data %}
    <!-- render chip -->
    {% endfor %}
</div>
{% endif %}
{# If article.equity_data is [] or missing, nothing renders — brief is unaffected #}
```

---

## State of the Art

| Concern | Pattern Used | Notes |
|---------|-------------|-------|
| Sync vs async HTTP | Sync `httpx.Client` | Matches Factiva pattern — pipeline's `run_full_pipeline()` is sync |
| Retry strategy | 2 attempts, exponential backoff 2-10s | Same as Factiva — sufficient for transient failures |
| Event recording | Isolated session, errors swallowed | Same as Factiva — event recording never crashes the pipeline |
| Enrichment persistence | Transient `_equity_data` attribute | Not persisted to DB — prices are ephemeral |
| Fallback behavior | Return `None`, log warning, continue | Consistent with FALL-03 requirement |
| Admin UI | HTMX + Bootstrap 5 form | Matches Factiva config admin page pattern |

---

## Open Questions

1. **Exact equity API endpoint path and query parameters**
   - What we know: Proxy name is `coreapi-equity-price`. Factiva path is `/coreapi/recent-news/v1/search`. Pattern suggests `/coreapi/equity-price/v1/price` or similar.
   - What's unclear: Exact path, query parameter names (ticker? symbol? exchange?), response field names (price? lastPrice? change? priceChange?).
   - Recommendation: Build `EquityPriceClient` with clearly named constants (`BASE_PATH`, field mapping in `get_price()`) that can be corrected on first test run. Do not hard-code field names scattered across the code. The `get_price()` method should try multiple field name variants via `data.get("price") or data.get("lastPrice")`.

2. **Response schema for equity endpoint**
   - What we know: Returns JSON. Likely includes price, daily change, change percent, currency.
   - What's unclear: Exact field names, whether data is nested or flat, date/timestamp format.
   - Recommendation: Log the raw response dict at DEBUG level on first successful call so the team can verify and update field mappings if needed.

3. **Exchange code format**
   - What we know: `EquityTicker` model has an `exchange` field. Common values: NYSE, NASDAQ, LSE, ASX.
   - What's unclear: Whether the API accepts standard exchange codes or uses an MMC-specific format.
   - Recommendation: Default to "NYSE" in the model. Admin UI should show a text field, not a dropdown, so it can accept any format.

---

## Sources

### Primary (HIGH confidence)
- `app/collectors/factiva.py` — definitive HTTP client pattern for X-Api-Key MMC Core API calls
- `app/models/api_event.py` — confirms `EQUITY_FETCH` and `EQUITY_FALLBACK` event types already exist
- `app/config.py` — confirms `mmc_api_key`, `mmc_api_base_url`, `is_mmc_api_key_configured()` already present
- `app/models/factiva_config.py` — definitive ORM model pattern for admin-managed config table
- `app/routers/admin.py` — definitive admin route pattern (GET/POST, Jinja2, HTMX)
- `app/services/pipeline.py` — pipeline step structure, step numbering convention
- `app/services/reporter.py` `_prepare_articles()` — article dict preparation pattern
- `app/templates/role_brief.html` — article card structure, impact strip pattern for inline chips
- `app/templates/email/role_email.html` — email template table-based layout requirements
- `app/templates/admin/base.html` — sidebar nav link pattern and Bootstrap 5 + HTMX stack
- `app/templates/admin/factiva.html` — admin config page pattern

### Secondary (MEDIUM confidence)
- `app/main.py` — startup migration pattern (ALTER TABLE, seed rows) for new ORM models

### Tertiary (LOW confidence — not verified)
- Equity API endpoint path `/coreapi/equity-price/v1/price` — inferred from Factiva path naming pattern, not confirmed from API documentation (PDFs are image-based)
- Equity response field names (`price`, `change`, `changePct`) — assumed from standard equity API conventions, not confirmed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt, confirmed in source
- Architecture (HTTP client, event recording, admin UI): HIGH — direct pattern from factiva.py
- Pipeline integration (Step 3b position, transient attribute): HIGH — based on pipeline.py structure
- Equity API shape (endpoint, response fields): LOW — PDFs unreadable; inferred from naming patterns only
- Template rendering (Jinja2 conditional, chip styling): HIGH — based on existing chip/badge patterns in role_brief.html

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (30 days — codebase is stable; API shape LOW-confidence items need verification on first test run)
