# Phase 6: Admin Dashboard - Research

**Researched:** 2026-02-07
**Domain:** FastAPI + HTMX + Bootstrap 5 Admin Interface
**Confidence:** HIGH

## Summary

The research focused on implementing a modern admin dashboard for MDInsights using HTMX with FastAPI and Bootstrap 5. The investigation covered standard patterns for CRUD operations, inline editing, file archive browsing, and security best practices. The existing BrasilIntel project provides an excellent reference implementation using the exact same stack (FastAPI + HTMX + Bootstrap 5 + Jinja2), making this a well-established pattern with proven effectiveness.

**Key findings:**
- HTMX with FastAPI is a mature, production-ready pattern for admin dashboards
- Bootstrap 5 provides comprehensive responsive UI components compatible with HTMX
- Inline editing and bulk operations have well-documented HTMX patterns
- SQLite FTS5 enables efficient full-text search without external dependencies
- FastAPI's static file serving can handle report archive browsing
- The BrasilIntel reference implementation demonstrates all required patterns

**Primary recommendation:** Follow the BrasilIntel admin dashboard architecture pattern exactly. Use Bootstrap 5 base template with HTMX for dynamic updates, implement CRUD operations via HTMX partials, use Pydantic for form validation, and leverage SQLite FTS5 for article search.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115+ | Web framework | High-performance async framework with automatic validation |
| HTMX | 2.0.4 | Dynamic updates | Enables SPA-like experience without JavaScript frameworks |
| Bootstrap | 5.3.3 | UI framework | Industry-standard responsive design with comprehensive components |
| Jinja2 | 3.1+ | Templating | FastAPI's recommended template engine for server-side rendering |
| SQLAlchemy | 2.0+ | ORM | Synchronous sessions for simple admin operations |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic | 2.0+ | Form validation | All form input validation with automatic error handling |
| fastapi-csrf-protect | 0.3+ | CSRF protection | Production deployments with form submissions |
| Bootstrap Icons | 1.11.3 | Icon library | Consistent iconography across admin interface |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTMX | Vue/React SPA | HTMX simpler, no build step, better for small teams |
| Bootstrap 5 | Tailwind CSS | Bootstrap has more components out-of-box, faster development |
| SQLite FTS5 | PostgreSQL FTS | SQLite FTS5 sufficient for <10K articles, simpler deployment |

**Installation:**
```bash
# Already installed in MDInsights project
pip install fastapi jinja2 sqlalchemy pydantic
# Optional for production
pip install fastapi-csrf-protect
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── routers/
│   └── admin.py              # Admin routes (already exists)
├── templates/
│   ├── admin/
│   │   ├── base.html         # Bootstrap 5 + HTMX layout
│   │   ├── sources.html      # Source management page
│   │   ├── recipients.html   # Recipient management page
│   │   ├── archive.html      # Report archive browser
│   │   ├── search.html       # Article search interface
│   │   └── partials/
│   │       ├── source_table.html      # HTMX partial
│   │       ├── recipient_table.html   # HTMX partial
│   │       ├── archive_list.html      # HTMX partial
│   │       └── search_results.html    # HTMX partial
├── schemas/
│   └── admin.py              # Pydantic models for admin forms
├── services/
│   └── search.py             # Article search service (FTS5)
└── storage/
    └── reports/              # Report archive directory
        └── {YYYY-MM-DD}/
            ├── Brokers.html
            ├── Leadership.html
            ├── Compliance.html
            └── Underwriting.html
```

### Pattern 1: Bootstrap 5 Base Template with HTMX
**What:** Layout template with sidebar navigation, responsive design, and HTMX integration
**When to use:** All admin pages inherit from this base
**Example:**
```html
<!-- Source: BrasilIntel base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Admin{% endblock %} | MDInsights Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
    <style>
        :root {
            --marsh-blue: #00263e;
            --marsh-light-blue: #0077c8;
            --sidebar-width: 250px;
        }
        .sidebar {
            position: fixed;
            top: 56px;
            bottom: 0;
            left: 0;
            width: var(--sidebar-width);
            background-color: white;
            border-right: 1px solid #dee2e6;
        }
        .main-content {
            margin-left: var(--sidebar-width);
            padding: 1.5rem;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark fixed-top">
        <a class="navbar-brand" href="/admin"><i class="bi bi-speedometer2"></i> MDInsights Admin</a>
    </nav>
    <div class="sidebar">
        <nav class="nav flex-column">
            <a class="nav-link" href="/admin/sources"><i class="bi bi-globe"></i> Sources</a>
            <a class="nav-link" href="/admin/recipients"><i class="bi bi-people"></i> Recipients</a>
            <a class="nav-link" href="/admin/archive"><i class="bi bi-archive"></i> Archive</a>
            <a class="nav-link" href="/admin/search"><i class="bi bi-search"></i> Search</a>
            <a class="nav-link" href="/admin/trigger"><i class="bi bi-play"></i> Manual Trigger</a>
        </nav>
    </div>
    <main class="main-content" style="margin-top: 56px;">
        {% block content %}{% endblock %}
    </main>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
</body>
</html>
```

### Pattern 2: HTMX Inline Table Editing
**What:** Click-to-edit pattern for table rows with HTMX swaps
**When to use:** Source management, recipient management with inline editing
**Example:**
```html
<!-- Source: https://htmx.org/examples/edit-row/ -->
<tr>
    <td>{{ source.name }}</td>
    <td>{{ source.url }}</td>
    <td>
        <span class="badge bg-{{ 'success' if source.enabled else 'warning' }}">
            {{ 'Enabled' if source.enabled else 'Disabled' }}
        </span>
    </td>
    <td>
        <button class="btn btn-sm btn-outline-primary"
                hx-get="/admin/sources/{{ source.id }}/edit"
                hx-target="closest tr"
                hx-swap="outerHTML">
            <i class="bi bi-pencil"></i> Edit
        </button>
    </td>
</tr>
```

### Pattern 3: HTMX Form with Pydantic Validation
**What:** Form submission via HTMX with server-side validation and error display
**When to use:** Add/edit source forms, recipient management forms
**Example:**
```python
# Source: FastAPI + Pydantic best practices
from pydantic import BaseModel, HttpUrl, field_validator
from fastapi import HTTPException, Form

class SourceCreate(BaseModel):
    name: str
    url: HttpUrl
    source_type: str
    actor_id: str | None = None
    enabled: bool = True

    @field_validator('source_type')
    def validate_source_type(cls, v):
        if v not in ['apify', 'rss']:
            raise ValueError('Invalid source type')
        return v

@router.post("/admin/sources/create", response_class=HTMLResponse)
async def create_source(
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form(...),
    actor_id: str = Form(None),
    enabled: bool = Form(True)
):
    try:
        # Validate with Pydantic
        source_data = SourceCreate(
            name=name, url=url, source_type=source_type,
            actor_id=actor_id, enabled=enabled
        )
        # Create source...
        # Return updated table partial
        return template.render("admin/partials/source_table.html")
    except ValidationError as e:
        # Return error partial with validation errors
        return template.render("admin/partials/form_errors.html", errors=e.errors())
```

### Pattern 4: HTMX Search with Debounce
**What:** Real-time search with debounced input to reduce server requests
**When to use:** Article search, source filtering, recipient filtering
**Example:**
```html
<!-- Source: BrasilIntel insurers.html -->
<input type="text"
       class="form-control"
       id="search-input"
       name="search"
       placeholder="Search articles by keyword..."
       hx-get="/admin/search"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#search-results"
       hx-include="[name='date_from'], [name='date_to'], [name='role']">
```

### Pattern 5: File Archive Browsing
**What:** List archived HTML reports by date with navigation and preview
**When to use:** Report archive browser
**Example:**
```python
# Source: FastAPI static files + directory listing pattern
from pathlib import Path
from fastapi.responses import FileResponse

@router.get("/admin/archive")
async def archive_list():
    reports_dir = Path("app/storage/reports")

    # Group reports by date (directory structure)
    archive = {}
    for date_dir in sorted(reports_dir.iterdir(), reverse=True):
        if date_dir.is_dir():
            reports = [f.name for f in date_dir.glob("*.html")]
            archive[date_dir.name] = reports

    return template.render("admin/archive.html", archive=archive)

@router.get("/admin/archive/{date}/{role}")
async def view_report(date: str, role: str):
    report_path = Path(f"app/storage/reports/{date}/{role}.html")
    if not report_path.exists():
        raise HTTPException(404, "Report not found")
    return FileResponse(report_path, media_type="text/html")
```

### Pattern 6: SQLite FTS5 Article Search
**What:** Full-text search on article title, description, and summary using SQLite FTS5
**When to use:** Article search interface
**Example:**
```python
# Source: https://charlesleifer.com/blog/using-sqlite-full-text-search-with-python/
from sqlalchemy import text

# Create FTS5 virtual table (migration)
CREATE_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    article_id UNINDEXED,
    title,
    description,
    summary,
    content=news_articles,
    content_rowid=id
);

-- Triggers to keep FTS5 in sync
CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON news_articles BEGIN
  INSERT INTO articles_fts(rowid, article_id, title, description, summary)
  VALUES (new.id, new.id, new.title, new.description, new.summary);
END;
"""

# Search query with ranking
@router.get("/admin/search")
async def search_articles(q: str, role: str = None, date_from: str = None):
    db = SessionLocal()

    # FTS5 search with BM25 ranking
    sql = text("""
        SELECT a.*, bm25(fts.rowid) as rank
        FROM articles_fts fts
        JOIN news_articles a ON a.id = fts.article_id
        WHERE fts MATCH :query
        ORDER BY rank
        LIMIT 50
    """)

    results = db.execute(sql, {"query": q}).fetchall()

    # Filter by role and date if provided
    # Return partial HTML
    return template.render("admin/partials/search_results.html", articles=results)
```

### Anti-Patterns to Avoid
- **Full page reloads for CRUD operations:** Use HTMX partials instead to swap only affected table rows
- **Client-side JavaScript validation only:** Always validate on server with Pydantic models
- **Storing file paths in database:** Use predictable directory structure (date-based) instead
- **Building custom pagination:** Use HTMX with Bootstrap pagination component
- **Complex JavaScript state management:** Let HTMX handle state via server responses

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSRF protection | Custom token generation | fastapi-csrf-protect | Handles cookie/header patterns, integrates with HTMX |
| Full-text search | LIKE queries | SQLite FTS5 | 100x faster, supports ranking, stemming, phrase matching |
| Form validation | Manual field checks | Pydantic BaseModel | Automatic validation, error formatting, type coercion |
| Pagination | Manual offset/limit | Bootstrap + HTMX pattern | Handles URL state, page numbers, edge cases |
| Date filtering | String manipulation | Python datetime + SQL | Proper timezone handling, validation, SQL compatibility |
| Inline editing | Custom JavaScript | HTMX edit-row pattern | Handles swap, validation errors, cancel button |

**Key insight:** The BrasilIntel reference implementation already solved these problems. Copy its patterns for source management to build recipient management, archive browsing, and search interfaces.

## Common Pitfalls

### Pitfall 1: HTMX Request Detection Failure
**What goes wrong:** Endpoint returns JSON when HTMX expects HTML, causing render failures
**Why it happens:** FastAPI routes default to JSON responses, HTMX requests need HTML partials
**How to avoid:** Always check HX-Request header and use response_class=HTMLResponse for HTMX endpoints
**Warning signs:** Network tab shows JSON responses, HTMX swap fails silently
**Solution:**
```python
from fastapi import Request
from fastapi.responses import HTMLResponse

@router.get("/admin/sources", response_class=HTMLResponse)
async def get_sources(request: Request):
    # Check if HTMX request
    is_htmx = request.headers.get("HX-Request") == "true"

    if is_htmx:
        # Return partial HTML for HTMX swap
        return template.render("admin/partials/source_table.html", sources=sources)
    else:
        # Return full page for direct navigation
        return template.render("admin/sources.html", sources=sources)
```

### Pitfall 2: Table Form Nesting Violations
**What goes wrong:** Forms inside `<tr>` elements violate HTML spec, causing parse errors
**Why it happens:** HTML doesn't allow `<form>` tags directly inside `<tr>`, browsers auto-close them
**How to avoid:** Wrap entire table in form, use hx-include to target specific row inputs
**Warning signs:** Form data not submitted, validation errors for wrong fields
**Solution:**
```html
<!-- Wrap entire table, not individual rows -->
<form id="bulk-form">
    <table class="table">
        <tbody>
            <tr>
                <td><input type="checkbox" name="selected" value="{{ source.id }}"></td>
                <td>{{ source.name }}</td>
                <td>
                    <button hx-post="/admin/sources/{{ source.id }}/edit"
                            hx-include="closest tr [name]"
                            hx-target="closest tr">
                        Edit
                    </button>
                </td>
            </tr>
        </tbody>
    </table>
</form>
```

### Pitfall 3: Missing HTMX After-Swap Handlers
**What goes wrong:** Dynamic content loses event listeners after HTMX swaps, buttons stop working
**Why it happens:** HTMX replaces DOM elements, destroying attached event listeners
**How to avoid:** Use htmx:afterSwap event to re-initialize JavaScript components
**Warning signs:** Checkboxes, buttons work initially but fail after HTMX updates
**Solution:**
```javascript
// Re-initialize after HTMX swaps (from BrasilIntel)
document.body.addEventListener('htmx:afterSwap', function(e) {
    if (e.detail.target.id === 'source-list') {
        // Reset bulk action buttons
        const selectAll = document.getElementById('select-all');
        if (selectAll) selectAll.checked = false;
        updateBulkButtons();
    }
});
```

### Pitfall 4: URL State Management Issues
**What goes wrong:** Browser back button breaks, filters reset unexpectedly, URLs don't reflect state
**Why it happens:** HTMX swaps update content but don't always update URL or browser history
**How to avoid:** Use hx-push-url="true" on navigation links and filter changes
**Warning signs:** Back button doesn't restore previous filter state, URLs don't show current filters
**Solution:**
```html
<!-- Push URL state for filters (from BrasilIntel pattern) -->
<select id="role-filter"
        hx-get="/admin/search"
        hx-trigger="change"
        hx-target="#search-results"
        hx-push-url="true"
        hx-include="[name='search']">
    <option value="">All Roles</option>
    <option value="Brokers">Brokers</option>
</select>
```

### Pitfall 5: Pydantic Validation Error Display
**What goes wrong:** Validation errors return 422 JSON instead of user-friendly HTML
**Why it happens:** FastAPI's default validation error handler returns JSON for API consistency
**How to avoid:** Catch ValidationError, format errors in template, return HTML partial
**Warning signs:** Users see raw JSON error responses, HTMX doesn't swap error content
**Solution:**
```python
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Check if HTMX request
    if request.headers.get("HX-Request") == "true":
        # Return HTML error partial for HTMX
        errors = [{"field": err["loc"][-1], "message": err["msg"]} for err in exc.errors()]
        return HTMLResponse(
            content=template.render("admin/partials/validation_errors.html", errors=errors),
            status_code=422
        )
    else:
        # Return JSON for API requests
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
```

### Pitfall 6: Report Archive File Path Traversal
**What goes wrong:** Malicious date parameter can access files outside archive directory
**Why it happens:** User input (date, role) used directly in Path construction without validation
**How to avoid:** Validate date format, sanitize role name, use Path.resolve() to check final path
**Warning signs:** Security scanner flags directory traversal vulnerability
**Solution:**
```python
from pathlib import Path
from fastapi import HTTPException
import re

@router.get("/admin/archive/{date}/{role}")
async def view_report(date: str, role: str):
    # Validate date format (YYYY-MM-DD)
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(400, "Invalid date format")

    # Validate role against allowed values
    if role not in ['Brokers', 'Leadership', 'Compliance', 'Underwriting']:
        raise HTTPException(400, "Invalid role")

    # Construct path and check it's within archive directory
    reports_dir = Path("app/storage/reports").resolve()
    report_path = (reports_dir / date / f"{role}.html").resolve()

    # Ensure resolved path is within reports directory
    if not str(report_path).startswith(str(reports_dir)):
        raise HTTPException(403, "Access denied")

    if not report_path.exists():
        raise HTTPException(404, "Report not found")

    return FileResponse(report_path)
```

## Code Examples

Verified patterns from official sources:

### Example 1: Source Management CRUD Router
```python
# Source: BrasilIntel admin patterns + FastAPI best practices
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from app.database import SessionLocal
from app.models import Source

router = APIRouter(prefix="/admin/sources", tags=["Admin Sources"])

class SourceCreate(BaseModel):
    name: str
    url: HttpUrl
    source_type: str
    actor_id: str | None = None
    enabled: bool = True

@router.get("", response_class=HTMLResponse)
async def list_sources(
    search: str = "",
    enabled: str = "",
    page: int = 1,
    limit: int = 50
):
    """List sources with search and filtering."""
    db = SessionLocal()
    try:
        query = db.query(Source)

        # Apply filters
        if search:
            query = query.filter(Source.name.contains(search))
        if enabled:
            query = query.filter(Source.enabled == (enabled == "true"))

        # Pagination
        total = query.count()
        sources = query.offset((page - 1) * limit).limit(limit).all()

        # Return partial or full page based on HX-Request
        return template.render("admin/partials/source_table.html",
                             sources=sources, total=total, page=page)
    finally:
        db.close()

@router.post("/create", response_class=HTMLResponse)
async def create_source(
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form(...),
    actor_id: str = Form(None),
    enabled: bool = Form(True)
):
    """Create new source with validation."""
    db = SessionLocal()
    try:
        # Pydantic validation
        source_data = SourceCreate(
            name=name, url=url, source_type=source_type,
            actor_id=actor_id, enabled=enabled
        )

        # Create database record
        source = Source(**source_data.dict())
        db.add(source)
        db.commit()
        db.refresh(source)

        # Return updated table
        sources = db.query(Source).all()
        return template.render("admin/partials/source_table.html", sources=sources)
    except ValidationError as e:
        return HTMLResponse(
            content=template.render("admin/partials/form_errors.html", errors=e.errors()),
            status_code=422
        )
    finally:
        db.close()

@router.get("/{source_id}/edit", response_class=HTMLResponse)
async def edit_source(source_id: int):
    """Return edit form row."""
    db = SessionLocal()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(404, "Source not found")
        return template.render("admin/partials/source_edit_row.html", source=source)
    finally:
        db.close()

@router.post("/{source_id}", response_class=HTMLResponse)
async def update_source(
    source_id: int,
    name: str = Form(...),
    url: str = Form(...),
    enabled: bool = Form(False)
):
    """Update source."""
    db = SessionLocal()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(404, "Source not found")

        source.name = name
        source.url = url
        source.enabled = enabled
        db.commit()
        db.refresh(source)

        # Return updated row
        return template.render("admin/partials/source_row.html", source=source)
    finally:
        db.close()

@router.delete("/{source_id}", response_class=HTMLResponse)
async def delete_source(source_id: int):
    """Delete source."""
    db = SessionLocal()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(404, "Source not found")

        db.delete(source)
        db.commit()

        # Return empty response (HTMX will remove row)
        return HTMLResponse(content="", status_code=200)
    finally:
        db.close()
```

### Example 2: Recipient Configuration Management
```python
# Source: MDInsights config.py pattern + CRUD best practices
from pydantic import BaseModel, EmailStr

class RecipientUpdate(BaseModel):
    """Schema for updating email recipients."""
    role: str
    to: list[EmailStr] = []
    cc: list[EmailStr] = []
    bcc: list[EmailStr] = []

@router.get("/admin/recipients", response_class=HTMLResponse)
async def list_recipients():
    """Display recipient configuration for all roles."""
    settings = get_settings()

    # Get current recipients for each role
    recipients = {
        "Brokers": settings.get_email_recipients("Brokers"),
        "Leadership": settings.get_email_recipients("Leadership"),
        "Compliance": settings.get_email_recipients("Compliance"),
        "Underwriting": settings.get_email_recipients("Underwriting"),
    }

    return template.render("admin/recipients.html", recipients=recipients)

@router.post("/admin/recipients/{role}", response_class=HTMLResponse)
async def update_recipients(
    role: str,
    to: str = Form(""),
    cc: str = Form(""),
    bcc: str = Form("")
):
    """Update recipient list for a role."""
    # Parse comma-separated emails
    to_list = [e.strip() for e in to.split(",") if e.strip()]
    cc_list = [e.strip() for e in cc.split(",") if e.strip()]
    bcc_list = [e.strip() for e in bcc.split(",") if e.strip()]

    # Validate with Pydantic
    try:
        recipient_data = RecipientUpdate(role=role, to=to_list, cc=cc_list, bcc=bcc_list)
    except ValidationError as e:
        return HTMLResponse(
            content=template.render("admin/partials/validation_errors.html", errors=e.errors()),
            status_code=422
        )

    # Update .env file (production would use database)
    env_file = Path(".env")
    env_content = env_file.read_text()

    # Update environment variables
    prefix = f"REPORT_RECIPIENTS_{role.upper()}"
    env_content = re.sub(
        f"^{prefix}=.*$",
        f"{prefix}={','.join(to_list)}",
        env_content,
        flags=re.MULTILINE
    )
    env_content = re.sub(
        f"^{prefix}_CC=.*$",
        f"{prefix}_CC={','.join(cc_list)}",
        env_content,
        flags=re.MULTILINE
    )

    env_file.write_text(env_content)

    # Return updated recipient card
    settings = get_settings()
    recipients = settings.get_email_recipients(role)
    return template.render("admin/partials/recipient_card.html",
                         role=role, recipients=recipients)
```

### Example 3: Report Archive Browser with Date Navigation
```python
# Source: FastAPI static files pattern + directory listing
from datetime import datetime, timedelta
from pathlib import Path

@router.get("/admin/archive", response_class=HTMLResponse)
async def archive_browser(
    month: str = "",  # Format: YYYY-MM
    role: str = ""
):
    """Browse report archive by month and role."""
    reports_dir = Path("app/storage/reports")

    # Get all report dates
    all_dates = sorted(
        [d.name for d in reports_dir.iterdir() if d.is_dir()],
        reverse=True
    )

    # Group by month
    months = {}
    for date_str in all_dates:
        month_key = date_str[:7]  # YYYY-MM
        if month_key not in months:
            months[month_key] = []
        months[month_key].append(date_str)

    # Filter by selected month
    if month:
        dates = months.get(month, [])
    else:
        # Default to current month
        current_month = datetime.now().strftime("%Y-%m")
        dates = months.get(current_month, [])
        month = current_month

    # Get reports for each date
    archive = []
    for date_str in dates:
        date_dir = reports_dir / date_str
        reports = {}
        for report_file in date_dir.glob("*.html"):
            role_name = report_file.stem
            if not role or role == role_name:
                reports[role_name] = {
                    "path": f"/admin/archive/{date_str}/{role_name}",
                    "size": report_file.stat().st_size,
                    "modified": datetime.fromtimestamp(report_file.stat().st_mtime)
                }

        if reports:
            archive.append({
                "date": date_str,
                "reports": reports
            })

    return template.render("admin/archive.html",
                         archive=archive,
                         months=sorted(months.keys(), reverse=True),
                         selected_month=month,
                         selected_role=role)

@router.get("/admin/archive/{date}/{role}", response_class=HTMLResponse)
async def view_report(date: str, role: str):
    """View archived report."""
    # Validation (see Pitfall 6)
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(400, "Invalid date format")
    if role not in ['Brokers', 'Leadership', 'Compliance', 'Underwriting']:
        raise HTTPException(400, "Invalid role")

    reports_dir = Path("app/storage/reports").resolve()
    report_path = (reports_dir / date / f"{role}.html").resolve()

    if not str(report_path).startswith(str(reports_dir)):
        raise HTTPException(403, "Access denied")
    if not report_path.exists():
        raise HTTPException(404, "Report not found")

    return FileResponse(report_path, media_type="text/html")
```

### Example 4: Article Search with SQLite FTS5
```python
# Source: https://charlesleifer.com/blog/using-sqlite-full-text-search-with-python/
from sqlalchemy import text

class ArticleSearchService:
    """Service for full-text article search using SQLite FTS5."""

    @staticmethod
    def create_fts_table(db: Session):
        """Create FTS5 virtual table (run once in migration)."""
        db.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                article_id UNINDEXED,
                title,
                description,
                summary,
                content=news_articles,
                content_rowid=id,
                tokenize='porter unicode61'
            )
        """))

        # Triggers to keep FTS5 in sync
        db.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON news_articles BEGIN
              INSERT INTO articles_fts(rowid, article_id, title, description, summary)
              VALUES (new.id, new.id, new.title, new.description, new.summary);
            END;
        """))

        db.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON news_articles BEGIN
              UPDATE articles_fts SET title=new.title, description=new.description,
                     summary=new.summary WHERE rowid=old.id;
            END;
        """))

        db.execute(text("""
            CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON news_articles BEGIN
              DELETE FROM articles_fts WHERE rowid=old.id;
            END;
        """))
        db.commit()

    @staticmethod
    def search_articles(
        db: Session,
        query: str,
        role: str = None,
        date_from: str = None,
        date_to: str = None,
        limit: int = 50
    ):
        """Search articles with FTS5 and optional filters."""
        # Build FTS5 query with ranking
        sql = text("""
            SELECT a.*, bm25(fts.rowid) as rank
            FROM articles_fts fts
            JOIN news_articles a ON a.id = fts.article_id
            WHERE fts MATCH :query
            ORDER BY rank
            LIMIT :limit
        """)

        results = db.execute(sql, {"query": query, "limit": limit}).fetchall()

        # Convert to article objects
        articles = [
            db.query(NewsArticle).filter(NewsArticle.id == r.id).first()
            for r in results
        ]

        # Apply additional filters in Python (roles is JSON field)
        if role:
            articles = [a for a in articles if role in json.loads(a.roles or "[]")]

        if date_from:
            date_from_dt = datetime.fromisoformat(date_from)
            articles = [a for a in articles if a.published_at >= date_from_dt]

        if date_to:
            date_to_dt = datetime.fromisoformat(date_to)
            articles = [a for a in articles if a.published_at <= date_to_dt]

        return articles

@router.get("/admin/search", response_class=HTMLResponse)
async def search_articles(
    q: str = "",
    role: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1
):
    """Search articles interface."""
    db = SessionLocal()
    try:
        if q:
            search_service = ArticleSearchService()
            articles = search_service.search_articles(
                db, query=q, role=role or None,
                date_from=date_from or None,
                date_to=date_to or None,
                limit=50
            )
        else:
            articles = []

        return template.render("admin/partials/search_results.html",
                             articles=articles, query=q, role=role)
    finally:
        db.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| jQuery + AJAX | HTMX 2.0 | 2023 | Simpler code, no build step, better accessibility |
| Bootstrap 4 | Bootstrap 5 | 2021 | Dropped jQuery dependency, improved customization |
| SQLite FTS3 | SQLite FTS5 | 2014 | Better ranking (BM25), phrase queries, custom tokenizers |
| Manual CSRF tokens | fastapi-csrf-protect | 2022 | Automatic token handling, HTMX integration |
| Pydantic v1 | Pydantic v2 | 2023 | 5-50x faster validation, better error messages |

**Deprecated/outdated:**
- **Bootstrap 4:** Removed in 2021, requires jQuery which conflicts with modern practices
- **SQLite FTS3/FTS4:** Superseded by FTS5 with better ranking and Unicode support
- **Manual JSON API + client-side rendering:** HTMX hypermedia approach simpler for admin dashboards
- **Starlette's SessionMiddleware for auth:** Use FastAPI security utilities with JWT or OAuth2

## Open Questions

Things that couldn't be fully resolved:

1. **Recipient Storage: .env vs Database**
   - What we know: Current implementation stores recipients in .env file (config.py)
   - What's unclear: Whether to migrate to database table for dynamic admin UI updates
   - Recommendation: Keep .env for Phase 6 (simpler), add database table in future phase if needed

2. **Report Archive Storage Strategy**
   - What we know: Reports mentioned in context as app/storage/reports/{role}/{YYYY-MM-DD}.html
   - What's unclear: Actual storage pattern (role subfolder vs date subfolder)
   - Recommendation: Use date-first structure (reports/{YYYY-MM-DD}/{role}.html) for easier browsing

3. **Authentication for Admin Routes**
   - What we know: BrasilIntel has login/logout routes, session management
   - What's unclear: Whether MDInsights needs authentication or relies on network security
   - Recommendation: Start without auth (internal tool), add basic auth in future if needed

4. **CSRF Protection in Production**
   - What we know: fastapi-csrf-protect available, HTMX supports CSRF headers
   - What's unclear: Whether production deployment requires CSRF protection
   - Recommendation: Add CSRF protection for production, skip for development simplicity

## Sources

### Primary (HIGH confidence)
- HTMX Official Documentation - https://htmx.org/examples/ (Click to Edit, Edit Row, Bulk Update patterns)
- FastAPI Official Documentation - https://fastapi.tiangolo.com/tutorial/static-files/ (Static file serving)
- SQLite FTS5 Official Documentation - https://www.sqlite.org/fts5.html (Full-text search)
- BrasilIntel Reference Implementation - C:\BrasilIntel\app\templates\admin\ (Production patterns)
- Pydantic Error Handling - https://docs.pydantic.dev/latest/errors/errors/ (Validation)

### Secondary (MEDIUM confidence)
- [Building Real-Time Dashboards with FastAPI and HTMX](https://medium.com/codex/building-real-time-dashboards-with-fastapi-and-htmx-01ea458673cb) - WebSearch verified pattern
- [Complete Guide: Building Production-Ready Web Apps with FastAPI and HTMX](https://medium.com/@sylvesterranjithfrancis/complete-guide-building-production-ready-web-apps-with-fastapi-and-htmx-from-setup-to-deployment-3010b1c8ff5c) - WebSearch verified pattern
- [Using SQLite Full-Text Search with Python](https://charlesleifer.com/blog/using-sqlite-full-text-search-with-python/) - Charles Leifer (verified expert)
- [FastAPI CSRF Protection: How to Secure Your API](https://www.stackhawk.com/blog/csrf-protection-in-fastapi/) - Security best practices
- [CoreUI Bootstrap 5 Admin Template](https://coreui.io/product/free-bootstrap-admin-template/) - Responsive design patterns

### Tertiary (LOW confidence)
- [43 Free Bootstrap Admin Dashboard Templates 2026](https://colorlib.com/wp/free-bootstrap-admin-dashboard-templates/) - General UI inspiration
- [Django CRUD inside a table with HTMX](https://medium.com/@duytran2310/django-crud-inside-a-table-with-htmx-part-1-53dd8417c36a) - Pattern reference (Django, not FastAPI)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - BrasilIntel reference implementation uses exact same stack
- Architecture: HIGH - All patterns verified in BrasilIntel codebase or HTMX official docs
- Pitfalls: HIGH - Identified from BrasilIntel implementation and HTMX documentation
- Search implementation: MEDIUM - SQLite FTS5 well-documented but not tested in MDInsights yet
- CSRF protection: MEDIUM - Library available but implementation pattern needs verification

**Research date:** 2026-02-07
**Valid until:** 60 days (stable stack, slow-moving standards)
