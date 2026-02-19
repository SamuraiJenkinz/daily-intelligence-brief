# Phase 13: Admin Dashboard Enterprise Status - Research

**Researched:** 2026-02-19
**Domain:** FastAPI + Jinja2 + Bootstrap 5 + HTMX admin dashboard extension
**Confidence:** HIGH

## Summary

This phase adds enterprise visibility to an existing admin dashboard. The codebase is well-understood: FastAPI with Jinja2 templates, Bootstrap 5.3.3, HTMX 2.0.4, SQLite via SQLAlchemy. All data needed already exists in the database — `api_events` table (Phase 9), `collector_source` on `news_articles` (Phase 10), and structured log data. The work is purely additive: new routes, templates, and one new sidebar page.

The four deliverables are: (1) enterprise API status panel at top of dashboard, (2) new Enterprise Config sidebar page for credential management, (3) per-article source badge in archive view, and (4) fallback event log on the dashboard or a dedicated section. No new models are needed. No changes to pipeline logic are required. All data already exists.

The primary architectural pattern throughout this codebase is: router function queries DB → builds data dict → renders Jinja2 template → returns HTMLResponse. Partial HTMX updates follow the same pattern with `hx-get`/`hx-target` for dynamic filtering. Credential changes write to `.env` file and call `get_settings.cache_clear()` — this pattern already exists in the recipients page and must be reused for enterprise credentials.

**Primary recommendation:** Follow the existing router/template/partial pattern exactly. Read every relevant existing file before writing any new file. The highest risk is credential scope decisions and masked-field UX — implement the same hidden+checkbox pattern used throughout for booleans, and use `type="password"` inputs with placeholder bullet characters for masked credentials.

## Standard Stack

The stack is fully determined by what already exists in the project. Do not introduce new libraries.

### Core (already installed and in use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (existing) | HTTP routing, HTMLResponse | All admin routes use this |
| Jinja2 | (existing) | Template rendering | All templates use `jinja_env.get_template()` |
| Bootstrap | 5.3.3 CDN | UI components, cards, badges | Loaded in base.html |
| Bootstrap Icons | 1.11.3 CDN | Icon set | Used throughout (`bi-*` classes) |
| HTMX | 2.0.4 CDN | Dynamic partial updates | Already loaded in base.html |
| SQLAlchemy | (existing) | ORM queries | All DB access uses `SessionLocal()` |
| structlog | (existing) | Structured logging | Used in all services |
| pydantic-settings | (existing) | Config/credential management | `get_settings()` pattern |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv (via pydantic-settings) | (existing) | .env read/write | Credential save flow (same as recipients page) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| .env file writes for credentials | DB table for credentials | DB is safer and transactional, but .env is the established pattern for recipients — use .env for consistency unless a new DB model is created |
| Bootstrap traffic lights | Custom SVG status indicators | Custom SVG adds complexity; Bootstrap badges/dots are already in use |

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure

New files for this phase:

```
app/
├── routers/
│   └── admin.py                          # Add new routes at bottom
├── templates/admin/
│   ├── dashboard.html                    # Add enterprise status panel at top
│   ├── enterprise_config.html            # NEW: sidebar page for credentials
│   ├── archive.html                      # Add source filter, article badge logic
│   └── partials/
│       ├── enterprise_status_panel.html  # NEW: status panel partial for HTMX
│       ├── archive_list.html             # Modify: add source badge to article rows
│       └── fallback_log.html             # NEW: fallback event log partial
```

### Pattern 1: Dashboard Section Injection

The dashboard.html currently has: Page Header → Summary Cards (4 cols) → Recent Runs Table.

The enterprise status panel goes BEFORE the summary cards row. The pattern is a new `<div class="row mb-4">` containing a full-width card with 4 API status indicators inside it.

**What:** A Bootstrap card spanning full width, with 4 inline status items (one per API). Each item shows: API name, colored status badge (healthy/degraded/offline), last checked time, and reason text when not healthy.

**Status badge mapping:**
- `healthy` → `badge bg-success` with `bi-check-circle-fill`
- `degraded` → `badge bg-warning text-dark` with `bi-exclamation-triangle-fill`
- `offline` → `badge bg-danger` with `bi-x-circle-fill`
- `unknown` (no events yet) → `badge bg-secondary` with `bi-question-circle`

**Data source:** Query `api_events` table. For each of the 4 `api_name` values (`auth`, `news`, `equity`, `email`), get the most recent event and derive status.

**Status derivation logic:**
```python
# For each api_name in ["auth", "news", "equity", "email"]:
# Get most recent ApiEvent for that api_name
# If no events: status = "unknown", last_checked = None, reason = None
# If most recent event.success = True: status = "healthy"
# If most recent event.success = False: status = "offline" (or "degraded" for fallback events)
# Fallback event types (NEWS_FALLBACK, EQUITY_FALLBACK, EMAIL_FALLBACK, TOKEN_FAILED):
#   success=False + fallback type → "degraded" (service worked via fallback)
#   success=False + non-fallback → "offline"
```

**Example:**
```python
# Source: existing admin.py pattern for DB queries
def _get_enterprise_api_status(db) -> list[dict]:
    from app.models.api_event import ApiEvent, ApiEventType
    FALLBACK_TYPES = {
        ApiEventType.NEWS_FALLBACK,
        ApiEventType.EQUITY_FALLBACK,
        ApiEventType.EMAIL_FALLBACK,
    }
    apis = ["auth", "news", "equity", "email"]
    statuses = []
    for api_name in apis:
        latest = db.query(ApiEvent).filter(
            ApiEvent.api_name == api_name
        ).order_by(ApiEvent.timestamp.desc()).first()

        if not latest:
            statuses.append({
                "api_name": api_name,
                "status": "unknown",
                "last_checked": None,
                "reason": None,
            })
        elif latest.success:
            statuses.append({
                "api_name": api_name,
                "status": "healthy",
                "last_checked": latest.timestamp.strftime("%Y-%m-%d %H:%M UTC"),
                "reason": None,
            })
        else:
            # Determine degraded vs offline
            is_fallback = latest.event_type in FALLBACK_TYPES
            statuses.append({
                "api_name": api_name,
                "status": "degraded" if is_fallback else "offline",
                "last_checked": latest.timestamp.strftime("%Y-%m-%d %H:%M UTC"),
                "reason": latest.detail[:100] if latest.detail else None,
            })
    return statuses
```

### Pattern 2: New Sidebar Page (Enterprise Config)

**What:** A dedicated page at `/admin/enterprise-config` for viewing and updating enterprise API credentials. Modelled after the existing Factiva Config and Recipients pages.

**Sidebar nav entry** (in base.html, after Equity Tickers):
```html
<!-- Source: base.html lines 231-242 pattern -->
<li class="nav-item">
    <a class="nav-link {% if active_nav == 'enterprise_config' %}active{% endif %}" href="/admin/enterprise-config">
        <i class="bi bi-shield-lock"></i>
        <span>Enterprise Config</span>
    </a>
</li>
```

**Credential fields to expose on this page:**
- MMC API Base URL (`mmc_api_base_url`) — shown, editable
- MMC API Client ID (`mmc_api_client_id`) — shown, editable
- MMC API Client Secret (`mmc_api_client_secret`) — MASKED
- MMC API Key (`mmc_api_key`) — MASKED
- MMC Sender Email (`mmc_sender_email`) — shown, editable
- Microsoft Tenant ID (`microsoft_tenant_id`) — shown, editable
- Microsoft Client ID (`microsoft_client_id`) — shown, editable
- Microsoft Client Secret (`microsoft_client_secret`) — MASKED
- Graph Sender Email (`sender_email`) — shown, editable

**Masking pattern:** Use `type="password"` for secret fields. Placeholder shows `••••••••` when value is set (non-empty), empty otherwise. Admin must clear the field to re-enter. On save, if the submitted value is blank for a masked field, skip that field (keep existing value). This prevents accidental deletion of secrets.

**Save mechanism:** Same as recipients page — write directly to `.env` file and call `get_settings.cache_clear()`. Use `re.sub()` to replace existing lines, append if not present.

```python
# Source: admin.py lines 855-878 (recipients update pattern)
def _update_env_var(env_content: str, var_name: str, value: str) -> str:
    import re
    pattern = re.compile(f"^{re.escape(var_name)}=.*$", re.MULTILINE)
    if pattern.search(env_content):
        return pattern.sub(f"{var_name}={value}", env_content)
    else:
        if env_content and not env_content.endswith("\n"):
            env_content += "\n"
        return env_content + f"{var_name}={value}\n"
```

**Save flow UX:** Standard POST form with save button (same as Factiva Config page). No confirmation dialog needed — the masked display already provides friction. Show success/error alert banner after save (Bootstrap dismissible alert, same pattern as factiva.html lines 57-69).

**Grouping:** Group credentials into two sections on the page — "MMC Core API" (auth, news, equity, email) and "Microsoft Graph API" (Graph email fallback). Each section is a Bootstrap card.

### Pattern 3: Per-Article Source Badge in Archive View

The archive view currently shows date cards with role-based report links (brokers/leadership/compliance/underwriting). The archive view shows **reports** (HTML files), not individual articles. The requirement for "per-article source attribution" means the source badge needs to appear when viewing an individual article in the search results (where articles are listed individually) or the archived report HTML itself.

**Critical clarification from code inspection:** The archive view (`/admin/archive`) shows reports (HTML files) grouped by date — it does NOT show individual articles. Individual articles are visible in `/admin/search`. The success criterion says "report archive view shows a source badge per article" — this most naturally applies to the search results view where articles are listed individually.

**Recommended implementation:** Add `collector_source` badge to search results (`partials/search_results.html`) AND to the archive article listing if articles are shown there. The `collector_source` field already exists on `NewsArticle` with values `"Factiva"` or `"Apify/RSS"`.

**Badge pattern** (consistent with pipeline runs table in dashboard.html lines 202-213):
```html
<!-- Source: dashboard.html source_breakdown badge pattern -->
{% if article.collector_source == 'Factiva' %}
    <span class="badge" style="background-color: #0077c8;">
        <i class="bi bi-newspaper"></i> Factiva
    </span>
{% else %}
    <span class="badge bg-secondary">
        <i class="bi bi-rss"></i> Apify/RSS
    </span>
{% endif %}
```

**Placement:** Inline with article headline/source line in search results. Add as a small badge next to the source name, not on a separate line.

**For the archive view specifically:** The archive shows HTML report files, not article rows. Source badges cannot be injected into pre-rendered HTML files. The practical implementation is: badges in search results + a summary note on the archive run row (which already exists via `source_breakdown` on runs). No additional archive.html changes needed beyond what already exists.

### Pattern 4: Fallback Event Log

**What:** A table showing all fallback events from `api_events` where `event_type IN (NEWS_FALLBACK, EQUITY_FALLBACK, EMAIL_FALLBACK, TOKEN_FAILED)`.

**Placement:** A new card section on the dashboard, below the Recent Pipeline Runs table. Title: "Fallback Event Log". Show last 20 events, most recent first.

**Columns:** Timestamp | API | Event Type | Reason (detail field, truncated to 100 chars)

**Data source:** Direct query of `api_events` table filtering on fallback event types:
```python
from app.models.api_event import ApiEvent, ApiEventType
FALLBACK_TYPES = [
    ApiEventType.NEWS_FALLBACK,
    ApiEventType.EQUITY_FALLBACK,
    ApiEventType.EMAIL_FALLBACK,
    ApiEventType.TOKEN_FAILED,
]
fallback_events = db.query(ApiEvent).filter(
    ApiEvent.event_type.in_(FALLBACK_TYPES)
).order_by(ApiEvent.timestamp.desc()).limit(20).all()
```

**Render:** Jinja2 table partial (same Bootstrap `table-striped table-hover` pattern as runs table).

### Anti-Patterns to Avoid

- **Don't use HTMX polling for status refresh:** Status is updated on each pipeline run, not real-time. Page load query is sufficient. The CONTEXT.md explicitly says "not real-time polling."
- **Don't create a new DB model for enterprise API status:** The `api_events` table already has all needed data. Derive status from it at query time.
- **Don't expose raw secret values:** Credential fields that are secrets (keys, secrets, passwords) must use `type="password"`. Never render actual secret values in HTML source.
- **Don't modify pipeline logic:** This phase is dashboard-only. The pipeline already writes `ApiEvent` rows. Do not change pipeline.py.
- **Don't break the `get_settings()` cache:** Always call `get_settings.cache_clear()` after writing to `.env`.
- **Don't assume api_events are present:** The table may be empty if the pipeline has never run. Handle `None` from `.first()` gracefully.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Status badge color logic | Custom CSS classes | Bootstrap `bg-success/warning/danger/secondary` | Already loaded, no new CSS needed |
| Icon library | Custom SVGs | Bootstrap Icons `bi-*` classes | Already loaded via CDN |
| Credential form fields | Custom masked input | HTML `type="password"` | Browser handles masking natively |
| .env file parsing | Custom parser | Python `re.compile()` + string operations | Same pattern as recipients page (admin.py:855-878) |
| Settings reload | Custom config reload | `get_settings.cache_clear()` | Already done in recipients page |
| HTMX partial returns | Custom JS | `HX-Request` header detection + template partial | Pattern already in sources, archive, search routes |
| DB query for status | Status polling service | Direct `SessionLocal()` query in route handler | Consistent with all other routes |

**Key insight:** Every problem in this phase has an existing solution in the codebase. The recipients page solves credential save flow. The dashboard solves status card layout. The factiva page solves form+success/error UX. Read and copy these patterns.

## Common Pitfalls

### Pitfall 1: Archive View vs Search Results Confusion

**What goes wrong:** Developer adds source badge to `archive_list.html` but the archive shows HTML report files, not articles. The badge has no per-article data to attach to.
**Why it happens:** "Report archive view" is ambiguous — it could mean the archive browser or the individual article list.
**How to avoid:** Read `archive.html` and `archive_list.html` carefully. The archive shows date-grouped report file links, not article rows. Source badges belong in `search_results.html` where individual `NewsArticle` rows are rendered.
**Warning signs:** If you find yourself trying to inject badges into pre-rendered HTML files.

### Pitfall 2: Revealing Credential Values in HTML Source

**What goes wrong:** Rendering actual secret values (API keys, client secrets) in template → visible in browser dev tools, logs.
**Why it happens:** Treating credentials like normal text fields.
**How to avoid:** Use `type="password"` for all secret fields. Never pass actual secret values to template context — pass only a boolean `is_set` flag to show the placeholder. When rendering: `<input type="password" placeholder="{{ '••••••••' if is_set else '' }}" name="mmc_api_key">`. The form action must skip blank submissions for masked fields.
**Warning signs:** Template rendering `{{ settings.mmc_api_key }}` directly.

### Pitfall 3: Empty api_events Table

**What goes wrong:** Dashboard crashes or shows unhelpful errors because `api_events` has no rows (pipeline never run, or Phase 9-12 events not yet recorded).
**Why it happens:** `.first()` returns `None`, template tries to access `.timestamp` on `None`.
**How to avoid:** Always check for `None` before accessing fields. Use the "unknown" status state when no events exist. Test with empty table.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'timestamp'` in logs.

### Pitfall 4: Credential Save Skips Blank Masked Fields

**What goes wrong:** Admin saves the Enterprise Config page with masked fields showing placeholder (not typing new values) → blank string overwrites the actual secret in .env.
**Why it happens:** HTML form submits empty string for unfilled password inputs.
**How to avoid:** In the POST handler, for each masked field: `if form_value and form_value.strip(): update_env(...)` — only write if non-empty. This means admins must clear and re-type to change a secret.
**Warning signs:** After saving, pipeline fails because `mmc_api_client_secret` is now empty.

### Pitfall 5: active_nav Not Passed to Dashboard Template

**What goes wrong:** Dashboard sidebar nav has no active highlight.
**Why it happens:** The current `get_admin_dashboard()` doesn't pass `active_nav` to the template. Looking at the template: `{% if active_nav == 'dashboard' %}active{% endif %}` — but `active_nav` is not in the current render call.
**How to avoid:** When modifying the dashboard render call to add enterprise status data, also add `active_nav='dashboard'` to the template context.
**Warning signs:** No sidebar item highlighted when on dashboard.

### Pitfall 6: api_name Values Must Match Exactly

**What goes wrong:** Status query for `api_name == "auth"` returns no results because events were recorded with `api_name = "mmc_auth"` or similar.
**Why it happens:** The `api_name` column is a free-text `String(50)` — no enum constraint. Values depend on how Phase 9-12 recorded them.
**How to avoid:** Check actual values by inspecting how `_record_event()` is called in the collectors. Search for `api_name` in collectors/factiva.py, collectors/equity.py, auth/token_manager.py, services/enterprise_emailer.py before writing the status query.
**Warning signs:** All 4 APIs show "unknown" even after pipeline runs.

## Code Examples

Verified patterns from existing codebase:

### Reading api_name Values from Existing Code
```python
# Source: Check app/collectors/factiva.py, app/collectors/equity.py,
#         app/auth/token_manager.py, app/services/enterprise_emailer.py
# These files call _record_event() or create ApiEvent rows.
# Verify api_name strings before hardcoding in status query.
# Known from model docstring: "auth", "news", "equity", "email"
```

### Adding Enterprise Status to Dashboard Route
```python
# Source: admin.py get_admin_dashboard() pattern (lines 52-127)
@router.get("", response_class=HTMLResponse)
def get_admin_dashboard():
    db = SessionLocal()
    try:
        # ... existing queries ...

        # NEW: Enterprise API status
        enterprise_status = _get_enterprise_api_status(db)

        # NEW: Fallback event log
        fallback_events = _get_fallback_events(db, limit=20)

        template = jinja_env.get_template('admin/dashboard.html')
        html = template.render(
            active_nav='dashboard',          # ADD THIS (currently missing)
            active_sources=active_sources,
            total_sources=total_sources,
            articles_today=articles_today,
            today_date=today.strftime('%Y-%m-%d'),
            last_run=last_run_data,
            runs=runs_data,
            enterprise_status=enterprise_status,   # NEW
            fallback_events=fallback_events,       # NEW
        )
        return HTMLResponse(content=html)
    finally:
        db.close()
```

### Enterprise Config GET Route
```python
# Source: admin.py get_factiva_config() pattern (lines 1137-1173)
@router.get("/enterprise-config", response_class=HTMLResponse)
def get_enterprise_config():
    settings = get_settings()
    # Build masked display: show placeholder, not actual value
    def is_set(value: str) -> bool:
        return bool(value and value.strip())

    config_display = {
        "mmc_api_base_url": settings.mmc_api_base_url,
        "mmc_api_client_id": settings.mmc_api_client_id,
        "mmc_api_client_secret_set": is_set(settings.mmc_api_client_secret),
        "mmc_api_key_set": is_set(settings.mmc_api_key),
        "mmc_sender_email": settings.mmc_sender_email,
        "microsoft_tenant_id": settings.microsoft_tenant_id,
        "microsoft_client_id": settings.microsoft_client_id,
        "microsoft_client_secret_set": is_set(settings.microsoft_client_secret),
        "sender_email": settings.sender_email,
    }

    template = jinja_env.get_template("admin/enterprise_config.html")
    return HTMLResponse(template.render(
        config=config_display,
        active_nav="enterprise_config",
        success=None,
        error=None,
    ))
```

### Enterprise Config POST Route (skip blank masked fields)
```python
# Source: admin.py update_recipients() .env write pattern (lines 843-890)
@router.post("/enterprise-config", response_class=HTMLResponse)
def update_enterprise_config(
    mmc_api_base_url: str = Form(""),
    mmc_api_client_id: str = Form(""),
    mmc_api_client_secret: str = Form(""),   # blank = keep existing
    mmc_api_key: str = Form(""),             # blank = keep existing
    mmc_sender_email: str = Form(""),
    microsoft_tenant_id: str = Form(""),
    microsoft_client_id: str = Form(""),
    microsoft_client_secret: str = Form(""), # blank = keep existing
    sender_email: str = Form(""),
):
    env_path = Path(".env")
    env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

    # Always-update fields (non-secret)
    always_update = {
        "MMC_API_BASE_URL": mmc_api_base_url,
        "MMC_API_CLIENT_ID": mmc_api_client_id,
        "MMC_SENDER_EMAIL": mmc_sender_email,
        "MICROSOFT_TENANT_ID": microsoft_tenant_id,
        "MICROSOFT_CLIENT_ID": microsoft_client_id,
        "SENDER_EMAIL": sender_email,
    }
    # Masked fields — only update if non-blank
    secret_update = {
        "MMC_API_CLIENT_SECRET": mmc_api_client_secret,
        "MMC_API_KEY": mmc_api_key,
        "MICROSOFT_CLIENT_SECRET": microsoft_client_secret,
    }

    for var_name, value in always_update.items():
        env_content = _update_env_var(env_content, var_name, value)

    for var_name, value in secret_update.items():
        if value.strip():  # Only overwrite if admin typed something
            env_content = _update_env_var(env_content, var_name, value)

    env_path.write_text(env_content, encoding="utf-8")
    get_settings.cache_clear()
    logger.info("enterprise_config_updated")

    # Re-render with success message
    settings = get_settings()
    # ... build config_display again, render template with success=...
```

### Status Panel Bootstrap HTML Pattern
```html
<!-- Source: dashboard.html card pattern (lines 19-122) -->
<!-- Enterprise API Status Panel — goes before Summary Cards row -->
<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <i class="bi bi-shield-check"></i>
                Enterprise API Status
                <small class="text-muted fw-normal ms-2">Updated on each pipeline run</small>
            </div>
            <div class="card-body">
                <div class="row g-3">
                    {% for api in enterprise_status %}
                    <div class="col-md-3">
                        <div class="d-flex align-items-start gap-2">
                            {% if api.status == 'healthy' %}
                                <i class="bi bi-check-circle-fill text-success fs-4 mt-1"></i>
                            {% elif api.status == 'degraded' %}
                                <i class="bi bi-exclamation-triangle-fill text-warning fs-4 mt-1"></i>
                            {% elif api.status == 'offline' %}
                                <i class="bi bi-x-circle-fill text-danger fs-4 mt-1"></i>
                            {% else %}
                                <i class="bi bi-question-circle text-secondary fs-4 mt-1"></i>
                            {% endif %}
                            <div>
                                <div class="fw-semibold text-capitalize">{{ api.api_name }}</div>
                                <div>
                                    {% if api.status == 'healthy' %}
                                        <span class="badge bg-success">Healthy</span>
                                    {% elif api.status == 'degraded' %}
                                        <span class="badge bg-warning text-dark">Degraded</span>
                                    {% elif api.status == 'offline' %}
                                        <span class="badge bg-danger">Offline</span>
                                    {% else %}
                                        <span class="badge bg-secondary">Unknown</span>
                                    {% endif %}
                                </div>
                                {% if api.last_checked %}
                                    <small class="text-muted">{{ api.last_checked }}</small>
                                {% else %}
                                    <small class="text-muted">No events recorded</small>
                                {% endif %}
                                {% if api.reason %}
                                    <div class="text-danger" style="font-size:0.75rem;">{{ api.reason }}</div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</div>
```

### Source Badge in Search Results
```html
<!-- Source: dashboard.html source_breakdown badge style (lines 202-213) -->
<!-- Add to search_results.html article rows -->
{% if article.collector_source == 'Factiva' %}
    <span class="badge" style="background-color: #0077c8; font-size: 0.7rem;">
        <i class="bi bi-newspaper"></i> Factiva
    </span>
{% elif article.collector_source %}
    <span class="badge bg-secondary" style="font-size: 0.7rem;">
        <i class="bi bi-rss"></i> {{ article.collector_source }}
    </span>
{% endif %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual .env editing for credentials | Admin UI writes .env + cache_clear | Phase 5 (recipients) | Pattern already proven; reuse for enterprise creds |
| No source attribution | `collector_source` field on articles | Phase 10 | Data exists, just needs surfacing |
| No API event tracking | `api_events` table with structured events | Phase 9 | Data exists, just needs surfacing |

**Deprecated/outdated:**
- None relevant to this phase.

## Open Questions

1. **Exact `api_name` values used in Phase 9-12 ApiEvent records**
   - What we know: The model docstring says `"auth"`, `"news"`, `"equity"`, `"email"`. The `ApiEventType` enum describes these categories.
   - What's unclear: The actual string values written by `_record_event()` calls in the collector files. May differ from the docstring description.
   - Recommendation: Before writing the status query, grep for `api_name` in `app/collectors/factiva.py`, `app/collectors/equity.py`, `app/auth/token_manager.py`, `app/services/enterprise_emailer.py`. Verify the actual strings.

2. **Whether `api_events` rows have been written at all**
   - What we know: The model exists and the pipeline references `_record_event()` for fallback cases.
   - What's unclear: Whether every pipeline path records events, or only failure/fallback paths.
   - Recommendation: Handle the empty table case gracefully. The "unknown" status covers this.

3. **Credential scope: which env var names map to which Settings fields**
   - What we know: `config.py` shows Settings field names and their env var equivalents (pydantic-settings uses `case_sensitive=False`, so `mmc_api_client_secret` maps to env var `MMC_API_CLIENT_SECRET`).
   - What's unclear: Whether any credentials are stored in DB models (like FactivaConfig) vs .env only.
   - Recommendation: Factiva query parameters are in the DB (FactivaConfig). Enterprise API credentials (MMC, Graph) are in .env via Settings. The Enterprise Config page should write to .env for MMC/Graph credentials. Factiva query parameters already have their own page — do NOT duplicate them on Enterprise Config.

4. **Archive view source attribution**
   - What we know: The archive shows HTML report files, not article rows. Source badges cannot be injected into pre-rendered HTML.
   - What's unclear: Does the success criterion really mean per-article badges in the archive browser, or does it mean within the viewed report HTML?
   - Recommendation: Add source badges to the search page (most natural per-article view). The archive browser already shows per-run source counts via `source_breakdown` in the runs table. If the success criterion requires archive browser enhancement, interpret it as adding a source filter dropdown to the archive browser (already in Claude's discretion scope).

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `app/routers/admin.py` — complete router file, all patterns
- Direct code inspection: `app/templates/admin/base.html` — Bootstrap 5.3.3, Bootstrap Icons 1.11.3, HTMX 2.0.4 CDN versions
- Direct code inspection: `app/templates/admin/dashboard.html` — existing card layout, source_breakdown badge style
- Direct code inspection: `app/templates/admin/factiva.html` — success/error form pattern
- Direct code inspection: `app/models/api_event.py` — ApiEvent model, ApiEventType enum, all field names
- Direct code inspection: `app/models/news_article.py` — collector_source field
- Direct code inspection: `app/models/run.py` — Run model fields
- Direct code inspection: `app/config.py` — Settings fields, is_mmc_*_configured() methods, lru_cache pattern
- Direct code inspection: `app/templates/admin/archive.html` and `partials/archive_list.html` — archive shows report files, not articles
- Direct code inspection: `app/logging_config.py` — structlog JSON structured logging

### Secondary (MEDIUM confidence)
- Direct code inspection: `app/services/pipeline.py` lines 100-250 — confirms ApiEventType.NEWS_FALLBACK recorded on fallback, confirms `_record_event()` pattern

### Tertiary (LOW confidence)
- Model docstring assertion that api_name values are "auth", "news", "equity", "email" — needs verification against actual collector code before using in queries

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — fully determined by existing codebase, no new libraries
- Architecture: HIGH — all patterns exist in codebase and were read directly
- Pitfalls: HIGH — derived from direct code inspection of relevant files
- api_name values: LOW — from model docstring only, needs verification in collector files

**Research date:** 2026-02-19
**Valid until:** Stable — this phase extends a fixed existing codebase. Valid until Phase 13 planning is complete.
