---
phase: 06-admin-dashboard
plan: 01
subsystem: admin-ui
tags: [bootstrap, htmx, jinja2, dashboard, navigation]

requires:
  phases: [05]
  services: [FastAPI, SQLAlchemy]
provides:
  templates: [base.html, dashboard.html]
  routes: [GET /admin]
  features: [admin-navigation, system-overview]
affects:
  phases: [06-02, 06-03, 06-04, 06-05]
  note: "All subsequent admin pages extend base.html"

tech-stack:
  added:
    frontend: [Bootstrap 5.3.3, HTMX 2.0.4, Bootstrap Icons 1.11.3]
    templating: [Jinja2]
  patterns: [master-template, responsive-sidebar, CDN-only]

key-files:
  created:
    - app/templates/admin/base.html
    - app/templates/admin/dashboard.html
  modified:
    - app/routers/admin.py
    - app/main.py

decisions:
  - id: bootstrap-version
    choice: Bootstrap 5.3.3
    rationale: Latest stable version with modern features and good browser support
  - id: htmx-version
    choice: HTMX 2.0.4
    rationale: Latest version for progressive enhancement and dynamic content loading
  - id: cdn-only
    choice: All CSS/JS from CDN
    rationale: No build step required, faster development, good caching
  - id: sidebar-width
    choice: 250px fixed width
    rationale: Standard admin sidebar width, good balance of nav space and content area
  - id: responsive-breakpoint
    choice: 768px (Bootstrap md)
    rationale: Standard tablet breakpoint, sidebar collapses on mobile
  - id: root-redirect
    choice: Redirect / to /admin (not /docs)
    rationale: Admin dashboard is primary interface, API docs accessible via navbar link

metrics:
  duration: 15 minutes
  completed: 2026-02-08
  commits: 2
  files_created: 2
  files_modified: 2
---

# Phase 6 Plan 01: Admin Dashboard Foundation Summary

**One-liner:** Bootstrap 5 + HTMX base template with responsive sidebar and dashboard landing page showing system status (sources, articles, runs)

## Objective

Create the foundational admin dashboard infrastructure that all Phase 6 plans build upon: a responsive Bootstrap 5 + HTMX base template with sidebar navigation, and a landing page displaying system status summary.

## Implementation

### Task 1: Base Template (591964f)

Created `app/templates/admin/base.html` as the master layout for all admin pages:

**CDN Dependencies:**
- Bootstrap 5.3.3 CSS/JS from jsdelivr
- Bootstrap Icons 1.11.3 from jsdelivr
- HTMX 2.0.4 from unpkg

**Layout Structure:**
- Fixed top navbar (--marsh-blue: #00263e background)
  - Brand: "MDInsights Admin" with speedometer icon
  - Right-aligned link to /docs (API Docs)
  - Mobile hamburger menu toggle
- Fixed left sidebar (250px width, white background)
  - Dashboard link (bi-speedometer2)
  - Sources link (bi-globe)
  - Recipients link (bi-people)
  - Archive link (bi-archive)
  - Search link (bi-search)
  - Manual Trigger link (bi-play-circle)
  - Active state highlighting via Jinja2 block
- Main content area with proper margins for navbar and sidebar
- Mobile responsive: sidebar collapses < 768px with overlay

**Jinja2 Blocks:**
- `{% block title %}` for page-specific titles
- `{% block active_nav %}` for sidebar active state
- `{% block content %}` for page content
- `{% block extra_head %}` for page-specific CSS
- `{% block extra_scripts %}` for page-specific JS

**Marsh Branding:**
- CSS custom properties: --marsh-blue (#00263e), --marsh-light-blue (#0077c8)
- Color scheme applied to navbar, sidebar active states, and card headers

### Task 2: Dashboard Landing Page (08c3dd4)

Created `app/templates/admin/dashboard.html` and refactored admin router:

**Dashboard Template:**
- Extends base.html with active_nav="dashboard"
- 4 summary cards in Bootstrap grid (col-md-3):
  1. **Active Sources**: Count of enabled sources (green check icon)
  2. **Total Sources**: Count of all sources (globe icon)
  3. **Articles Today**: Count of articles from today (newspaper icon)
  4. **Last Run**: Status badge and timestamp (clock icon)
- Recent Runs table (last 10 runs):
  - Columns: ID, Status, Started, Completed, Articles Collected, Articles Classified, Error
  - Bootstrap table-striped table-hover classes
  - Status badges: success (green), failed (red), running (blue)

**Admin Router Refactoring:**
- Added `from sqlalchemy import func` for SQL date function
- Imported Source and NewsArticle models for queries
- Added GET /admin route:
  - Queries total sources and enabled sources (Source.enabled == True)
  - Queries articles from today using func.date(NewsArticle.published_at)
  - Queries last run and last 10 runs ordered by ID desc
  - Formats datetimes as strings for template rendering
  - Returns dashboard.html via Jinja2

**Main.py Updates:**
- Changed root / redirect from /docs to /admin
- Admin dashboard now the default landing page
- API docs still accessible via navbar link

**Existing Routes Preserved:**
- GET /admin/trigger continues to serve admin_trigger.html
- POST /admin/trigger-pipeline continues to execute pipeline
- GET /admin/runs continues to return JSON array

## Testing

All verification criteria passed:

1. ✅ `python -c "from app.routers.admin import router"` imports successfully
2. ✅ Server starts without errors on port 8001
3. ✅ GET /admin returns 200 with Bootstrap 5 styling and sidebar nav
4. ✅ GET /admin/trigger returns 200 (existing trigger UI)
5. ✅ GET /admin/runs returns 200 JSON array
6. ✅ GET / redirects to /admin (307 redirect)
7. ✅ Dashboard shows all 6 sidebar links
8. ✅ Dashboard shows 4 summary cards
9. ✅ Dashboard shows Recent Runs table

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Phase 6 Progress:** 1/5 plans complete (06-01 ✅, 06-02-06-05 pending)

**Immediate Dependencies:**
- 06-02 (Source Management): Will extend base.html, use sidebar nav
- 06-03 (Archive Browser): Will extend base.html, use sidebar nav
- 06-04 (Semantic Search): Will extend base.html, use sidebar nav
- 06-05 (Recipient Management): Will extend base.html, use sidebar nav

**Readiness Status:** ✅ Ready

All subsequent Phase 6 plans can now build upon the established admin dashboard foundation. The base template provides consistent navigation, branding, and responsive layout for all admin pages.

**Technical Foundation:**
- ✅ Bootstrap 5 + HTMX stack operational
- ✅ Jinja2 template inheritance working
- ✅ Admin router pattern established
- ✅ Database queries functional
- ✅ Responsive mobile layout tested

**No blockers.** Phase 6 can proceed with source management, archive, search, and recipient pages.
