# Phase 16: Dashboard & Config Updates - Research

**Researched:** 2025-02-26
**Domain:** Admin Dashboard UI & Configuration
**Confidence:** HIGH

## Summary

Phase 16 updates the admin dashboard and configuration files to reflect the Factiva-only architecture established in Phase 15. This is a cosmetic cleanup phase focused on removing Apify/RSS traces from the UI, simplifying source presentation for single-source model, and ensuring FactivaConfig clearly communicates its role as the sole collection configuration.

Research focused on understanding the current dashboard implementation (dashboard health monitoring, run source breakdown, fallback event display), source management UI (type dropdowns, actor_id fields), FactivaConfig admin page (misleading fallback hints), .env.example structure, and historical data rendering in templates (search results, email templates, brief templates).

**Primary recommendation:** Use FastAPI Jinja2 templating for all UI updates, maintain backward-compatible DB schema while updating defaults, and coordinate changes across Python backend (admin.py routes), HTML templates (dashboard.html, factiva.html, sources.html), and .env.example configuration documentation.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.104+ | Web framework for admin routes | Current framework, handles routing and forms |
| Jinja2 | 3.1+ | HTML templating engine | Built-in FastAPI template rendering |
| SQLAlchemy | 2.0+ | ORM for DB queries | Current ORM, handles model layer |
| Bootstrap | 5.3 | CSS framework for admin UI | Current UI framework (confirmed in templates) |
| HTMX | 1.9+ | Dynamic partial updates | Current approach for interactive UI |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic | 2.0+ | Form validation schemas | Admin form validation (existing in schemas/admin.py) |
| structlog | N/A | Structured logging | Admin action logging (existing pattern) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 templates | React/Vue SPA | Current approach is simpler, avoids API layer complexity |
| HTMX partials | Full page reloads | HTMX provides better UX with minimal JS |
| Bootstrap | Tailwind CSS | Bootstrap already integrated, no benefit to switching |

**Installation:**
No new dependencies required — all work uses existing stack.

## Architecture Patterns

### Recommended Project Structure
Current structure is well-organized:
```
app/
├── routers/
│   └── admin.py              # All admin routes (GET/POST endpoints)
├── templates/
│   └── admin/
│       ├── dashboard.html     # Main dashboard page
│       ├── factiva.html       # Factiva config page
│       ├── sources.html       # Source management page
│       └── partials/          # HTMX partial templates
│           ├── search_results.html
│           ├── source_form.html
│           └── source_row.html
├── models/
│   ├── source.py              # Source ORM model
│   ├── api_event.py           # ApiEvent ORM model
│   └── news_article.py        # NewsArticle ORM model
└── schemas/
    └── admin.py               # Pydantic validation schemas
```

### Pattern 1: Admin Route Handler
**What:** FastAPI route handler with Jinja2 template rendering
**When to use:** All admin page updates
**Example:**
```python
# Source: app/routers/admin.py (existing pattern)
@router.get("/factiva", response_class=HTMLResponse)
def get_factiva_config():
    """Serve Factiva configuration page."""
    db = SessionLocal()
    try:
        config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
        template = jinja_env.get_template("admin/factiva.html")
        return HTMLResponse(template.render(
            config=config,
            active_nav="factiva",
            success=None,
            error=None,
        ))
    finally:
        db.close()
```

### Pattern 2: Dashboard Data Query with Status Calculation
**What:** Query helper function for dashboard status cards
**When to use:** Health monitoring, API status display
**Example:**
```python
# Source: app/routers/admin.py lines 52-110 (existing pattern)
def _get_enterprise_api_status(db) -> list:
    """
    Query api_events table for most recent event per enterprise API.

    Returns list of dicts with: api_name, display_name, status, last_checked, reason
    Status values: healthy, degraded, offline, unknown
    """
    DISPLAY_NAMES = {
        "auth": "Authentication",
        "news": "News (Factiva)",  # Already shows "News (Factiva)"
        "equity": "Equity Prices",
        "email": "Email Delivery",
    }
    FALLBACK_TYPES = {
        ApiEventType.NEWS_FALLBACK,  # Remove this for news
        ApiEventType.EQUITY_FALLBACK,
        ApiEventType.EMAIL_FALLBACK,
    }
    # ... query latest event and return status dict
```

### Pattern 3: Jinja2 Template with Conditional Rendering
**What:** HTML template with conditional logic for source badges
**When to use:** Search results, dashboard run breakdown
**Example:**
```html
<!-- Source: app/templates/admin/partials/search_results.html lines 35-43 -->
{% if article.collector_source == 'Factiva' %}
<span class="badge me-3" style="background-color: #0077c8; font-size: 0.7rem;">
    <i class="bi bi-newspaper me-1"></i>Factiva
</span>
{% elif article.collector_source %}
<span class="badge bg-secondary me-3" style="font-size: 0.7rem;">
    <i class="bi bi-rss me-1"></i>{{ article.collector_source }}
</span>
{% endif %}
```

### Pattern 4: Backward-Compatible DB Schema Updates
**What:** Preserve enum values in DB while updating defaults
**When to use:** Model changes that affect existing data
**Example:**
```python
# Source: app/models/news_article.py line 39 (current)
collector_source = Column(String(20), nullable=True, default="Apify/RSS")

# Updated default (Phase 16):
collector_source = Column(String(20), nullable=True, default="Factiva")
```

### Anti-Patterns to Avoid
- **Breaking existing data**: Don't remove enum values from SourceType (would break existing rows) — keep for schema stability
- **Changing migration SQL**: Don't alter startup migration code that already ran (documents schema evolution)
- **Removing historical rendering**: Keep Apify/RSS badge rendering paths in templates (fresh DB planned but safe fallback)
- **Forcing schema changes**: Don't require DB migration for cosmetic updates (use application-layer defaults)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation | Manual string checks | Pydantic schemas (existing in schemas/admin.py) | Type safety, error messages, validation rules |
| Template rendering | String concatenation | Jinja2 templates (existing pattern) | Auto-escaping, maintainability, separation of concerns |
| Dashboard status calculation | Ad-hoc queries | Helper functions like _get_enterprise_api_status | Reusable, testable, documented logic |
| HTML partial updates | JavaScript DOM manipulation | HTMX attributes (existing pattern) | Simpler, declarative, less client-side code |

**Key insight:** All infrastructure for this phase already exists — this is purely UI cleanup using established patterns.

## Common Pitfalls

### Pitfall 1: Breaking Backward Compatibility
**What goes wrong:** Removing enum values or changing DB constraints breaks existing data
**Why it happens:** Temptation to "clean up" DB schema when removing features
**How to avoid:**
- Keep SourceType.APIFY and SourceType.RSS enums (DB compatibility)
- Keep historical migration SQL unchanged (documents schema evolution)
- Change defaults, not constraints
**Warning signs:** Seeing "constraint violation" or "invalid enum value" errors in logs

### Pitfall 2: Incomplete Template Updates
**What goes wrong:** Apify/RSS badges still render in some templates but not others
**Why it happens:** Missing search across all template types (admin, email, brief)
**How to avoid:**
- Search for all template files: `*.html` in templates/
- Check all rendering paths: search results, dashboard, email templates, brief templates
- Maintain consistent badge logic (Factiva vs historical)
**Warning signs:** User reports seeing "Apify/RSS" badges in some contexts

### Pitfall 3: Misleading Configuration Hints
**What goes wrong:** Users disable Factiva thinking fallback exists, breaking collection
**Why it happens:** Old hint text says "automatically falls back to Apify/RSS"
**How to avoid:**
- Replace fallback hints with clear warnings
- Add header notes explaining sole-source architecture
- Use warning styling (text-danger, exclamation icon) for critical hints
**Warning signs:** Support requests about "why is collection stopped" after disabling Factiva

### Pitfall 4: Inconsistent News API Status Logic
**What goes wrong:** Dashboard shows "degraded" state for news API when no fallback exists
**Why it happens:** Legacy status calculation treats NEWS_FALLBACK as valid state
**How to avoid:**
- Remove NEWS_FALLBACK from FALLBACK_TYPES set in _get_enterprise_api_status
- Simplify news status: healthy (Factiva working) or offline (Factiva down)
- Update ApiEventType docstring to clarify NEWS_FALLBACK is historical
**Warning signs:** Dashboard shows "degraded" for news when it should be offline

## Code Examples

Verified patterns from codebase:

### Health Monitoring Update (Remove NEWS_FALLBACK)
```python
# Source: app/routers/admin.py lines 52-110
# BEFORE (current):
FALLBACK_TYPES = {
    ApiEventType.NEWS_FALLBACK,      # Remove this
    ApiEventType.EQUITY_FALLBACK,
    ApiEventType.EMAIL_FALLBACK,
}

# AFTER (Phase 16):
FALLBACK_TYPES = {
    ApiEventType.EQUITY_FALLBACK,
    ApiEventType.EMAIL_FALLBACK,
}

# Status calculation simplifies to binary for news:
# - success=True → "healthy"
# - success=False → "offline" (no degraded state)
```

### Dashboard Run Source Breakdown (Keep Blue Badge)
```html
<!-- Source: app/templates/admin/dashboard.html lines 258-272 -->
<!-- BEFORE (current shows both Factiva and Apify/RSS): -->
{% if run.source_breakdown.get('Factiva') %}
    <span class="badge" style="background-color: #0077c8;">{{ run.source_breakdown['Factiva'] }} Factiva</span>
{% endif %}
{% if run.source_breakdown.get('Apify/RSS') %}
    <span class="badge bg-secondary">{{ run.source_breakdown['Apify/RSS'] }} Apify/RSS</span>
{% endif %}

<!-- AFTER (Phase 16, simplified to Factiva-only): -->
{% if run.source_breakdown.get('Factiva') %}
    <span class="badge" style="background-color: #0077c8;">
        <i class="bi bi-newspaper me-1"></i>{{ run.source_breakdown['Factiva'] }} Factiva
    </span>
{% endif %}
```

### FactivaConfig Warning Update (Replace Misleading Hint)
```html
<!-- Source: app/templates/admin/factiva.html lines 160-163 -->
<!-- BEFORE (current, misleading): -->
<div class="field-hint ms-4">
    When disabled, the pipeline automatically falls back to Apify/RSS collection.
</div>

<!-- AFTER (Phase 16, clear warning): -->
<div class="field-hint ms-4 text-danger">
    <i class="bi bi-exclamation-triangle-fill me-1"></i>
    <strong>Warning:</strong> Disabling Factiva will stop all news collection. No fallback source is available.
</div>
```

### FactivaConfig Page Header (Add Context Note)
```html
<!-- Source: app/templates/admin/factiva.html lines 46-54 -->
<!-- BEFORE (current): -->
<div class="row mb-4 factiva-header">
    <div class="col-12">
        <h3><i class="bi bi-newspaper"></i> Factiva News Collection</h3>
        <p class="text-muted mb-0">Configure Factiva API query parameters for insurance/reinsurance news collection.</p>
    </div>
</div>

<!-- AFTER (Phase 16, add sole-source context): -->
<div class="row mb-4 factiva-header">
    <div class="col-12">
        <h3><i class="bi bi-newspaper"></i> Factiva News Collection</h3>
        <p class="text-muted mb-1">Configure Factiva API query parameters for insurance/reinsurance news collection.</p>
        <div class="alert alert-info py-2 mb-0">
            <i class="bi bi-info-circle me-2"></i>
            <strong>Note:</strong> Factiva is the sole news collection source for MDInsights. All articles are collected via the MMC Core API.
        </div>
    </div>
</div>
```

### Source Management UI (Remove Type Dropdown)
```html
<!-- Source: app/templates/admin/partials/source_form.html lines 38-53 -->
<!-- BEFORE (current with type dropdown): -->
<div class="col-md-4">
    <label for="newSourceType" class="form-label">Source Type <span class="text-danger">*</span></label>
    <select class="form-select" id="newSourceType" name="source_type" required>
        <option value="" disabled selected>Choose...</option>
        <option value="apify">Apify</option>
        <option value="rss">RSS</option>
    </select>
</div>

<!-- AFTER (Phase 16, remove type field entirely): -->
<!-- Field removed from form, source_type hidden input not needed for create/update -->
```

### Source Schema Validation (Tighten Valid Types)
```python
# Source: app/schemas/admin.py lines 10-43
# BEFORE (current):
class SourceCreate(BaseModel):
    source_type: Literal["apify", "rss"]

# AFTER (Phase 16, remove valid types):
class SourceCreate(BaseModel):
    # Remove source_type field entirely — not needed for new sources
    # DB column preserved for existing rows but UI doesn't expose it
    pass  # Other fields remain: name, url, enabled
```

### NewsArticle Default Update
```python
# Source: app/models/news_article.py line 39
# BEFORE (current):
collector_source = Column(String(20), nullable=True, default="Apify/RSS")

# AFTER (Phase 16):
collector_source = Column(String(20), nullable=True, default="Factiva")
```

### Startup Migration SQL Default Update
```python
# Source: app/main.py lines 56-60
# BEFORE (current):
session.execute(
    text("ALTER TABLE news_articles ADD COLUMN collector_source TEXT DEFAULT 'Apify/RSS'")
)

# AFTER (Phase 16):
session.execute(
    text("ALTER TABLE news_articles ADD COLUMN collector_source TEXT DEFAULT 'Factiva'")
)
```

### .env.example Update (Remove Apify Variables)
```bash
# Source: .env.example (current has no Apify vars, already clean)
# No Apify-specific variables found in current .env.example
# Phase 16 updates:
# 1. Add comment in MMC Core API section clarifying Factiva as sole news source
# 2. Update instructions to reflect single-source architecture
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Multi-source (Apify/RSS + Factiva) | Single-source (Factiva only) | Phase 15 | Dashboard must reflect sole-source model |
| Fallback status for news API | Binary status (healthy/offline) | Phase 16 | Simplified health monitoring |
| Source type dropdown in UI | No type selection needed | Phase 16 | Cleaner UI for single-source reality |
| Generic news API label | "News (Factiva)" branding | Phase 13 | Already implemented, keep consistent |
| Generic fallback hints | Clear warnings about no fallback | Phase 16 | Better user understanding |

**Deprecated/outdated:**
- NEWS_FALLBACK status type: Historical artifact from multi-source era, remove from active status calculation
- Source type UI controls: No longer meaningful with single source, hide from admin forms
- Apify/RSS fallback hints: Misleading post-Phase 15, replace with warnings

## Open Questions

1. **News API Card Label Wording**
   - What we know: Dashboard shows "News (Factiva)" in display name (line 67 of admin.py)
   - What's unclear: Should it match other cards ("Factiva" only) or keep current wording
   - Recommendation: Keep "News (Factiva)" for consistency with existing implementation (Phase 13)

2. **Source Type in DB Model vs UI**
   - What we know: Phase 15-03 decided to preserve SourceType enum for DB compatibility
   - What's unclear: Whether to keep field visible but disabled in UI or hide completely
   - Recommendation: Hide completely from UI (cleaner UX), preserve in DB schema (stability)

3. **Historical Run Source Breakdown Display**
   - What we know: Fresh DB planned means no backwards-compatible rendering needed
   - What's unclear: Whether to keep Apify/RSS rendering path as safety fallback
   - Recommendation: Keep rendering path (low maintenance cost, handles edge cases gracefully)

4. **Date Range Hours Help Text Wording**
   - What we know: Field controls lookback window for article collection
   - What's unclear: Exact wording for user-friendly explanation
   - Recommendation: "How far back to look for articles each run. 48 hours provides overlap to catch late-indexed articles."

## Sources

### Primary (HIGH confidence)
- **Codebase**: app/routers/admin.py — Current dashboard implementation (lines 52-254, status calculation and dashboard routes)
- **Codebase**: app/templates/admin/dashboard.html — Current dashboard UI (lines 18-349, health panel and run breakdown)
- **Codebase**: app/templates/admin/factiva.html — Current FactivaConfig page (lines 1-254, misleading fallback hint at line 162)
- **Codebase**: app/templates/admin/sources.html — Source management page (lines 1-172, type dropdown at lines 85-99)
- **Codebase**: app/templates/admin/partials/source_form.html — Source form UI (lines 38-66, type and actor_id fields)
- **Codebase**: app/templates/admin/partials/search_results.html — Search results rendering (lines 35-43, Factiva badge logic)
- **Codebase**: app/models/source.py — Source ORM model (lines 12-16, SourceType enum)
- **Codebase**: app/models/api_event.py — ApiEvent model (lines 14-43, ApiEventType enum with NEWS_FALLBACK)
- **Codebase**: app/models/news_article.py — NewsArticle model (line 39, collector_source default)
- **Codebase**: app/schemas/admin.py — Admin form validation (lines 10-79, source_type validation)
- **Codebase**: app/main.py — Startup migration SQL (lines 56-60, collector_source column default)
- **Codebase**: .env.example — Configuration template (verified no Apify variables present)

### Secondary (MEDIUM confidence)
- **Phase 15-03 CONTEXT.md**: Decision to preserve DB schema (preserve-db-schema, preserve-migration-sql decisions)
- **Phase Context**: User decisions from discuss-phase (clear guidance on all requirements)

### Tertiary (LOW confidence)
- None — all findings verified with codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use, verified in requirements.txt and imports
- Architecture: HIGH - Patterns extracted from existing codebase, proven and working
- Pitfalls: HIGH - Based on Phase 15 learnings and explicit user decisions in CONTEXT
- Code examples: HIGH - All examples from actual codebase with line numbers

**Research date:** 2025-02-26
**Valid until:** 60 days (stable dashboard implementation, minimal framework churn)
