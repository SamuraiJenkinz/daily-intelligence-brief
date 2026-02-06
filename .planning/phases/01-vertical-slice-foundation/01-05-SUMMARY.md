---
phase: 01-vertical-slice-foundation
plan: 05
subsystem: pipeline
tags: [fastapi, pipeline-orchestration, admin-ui, manual-trigger]

requires:
  - phase: 01-02
    provides: ApifyCollector service
  - phase: 01-03
    provides: RoleClassificationService
  - phase: 01-04
    provides: RoleReportService, tabbed HTML template
provides:
  - PipelineOrchestrator coordinating full pipeline
  - Admin router with trigger endpoint and run history
  - Admin UI for manual pipeline triggering
  - Pipeline test script
affects: [phase-2-expansion, phase-5-email, phase-6-scheduler]

tech-stack:
  added: [fastapi-routers, pipeline-orchestration]
  patterns: [admin-router-pattern, pipeline-orchestration-pattern]

key-files:
  created:
    - app/services/pipeline.py
    - app/routers/__init__.py
    - app/routers/admin.py
    - app/templates/admin_trigger.html
    - scripts/test_pipeline.py
  modified:
    - app/main.py

key-decisions:
  - "Pipeline orchestrator lets collector create Run internally (Option A) - simpler for Phase 1"
  - "Admin UI opens report in new window for browser-based viewing before email integration"
  - "Custom response headers (X-MDInsights-*) enable client-side run tracking without API calls"

duration: 6min
completed: 2026-02-06
---

# Plan 01-05: Manual Trigger Endpoint Summary

**Complete FastAPI admin interface with pipeline orchestration enabling one-click generation of multi-role intelligence briefs**

## What Was Built

**Phase 1 vertical slice complete**: Collection → Classification → Reporting → Browser delivery

### 1. Pipeline Orchestration Service
**File**: `app/services/pipeline.py`

Core orchestration service coordinating the complete workflow:
- **PipelineOrchestrator class** managing service dependencies
- **6-step workflow**: Collection → Run identification → Article query → Classification → Re-query → Report generation
- **Structured logging** for each step with progress tracking
- **Transaction management** with proper error handling and Run status updates
- **Result dictionary** with run_id, counts, HTML output, status, and errors

**Key pattern**: Collector creates Run internally, orchestrator queries latest Run for coordination. Simple and effective for Phase 1.

### 2. Admin API Router
**File**: `app/routers/admin.py`

FastAPI router with three endpoints:
- **POST /admin/trigger-pipeline**: Execute full pipeline, return HTML report
- **GET /admin/trigger**: Serve admin UI
- **GET /admin/runs**: Return recent run history as JSON

**Custom response headers** enable run tracking:
- `X-MDInsights-Run-ID`: Database run identifier
- `X-Articles-Collected`: Total articles scraped
- `X-Articles-Classified`: Successfully classified articles

**Configuration validation**: Checks for Apify and Azure OpenAI credentials before execution

### 3. Admin User Interface
**File**: `app/templates/admin_trigger.html`

Simple, functional UI for manual triggering:
- **Role dropdown**: Select target role (Brokers/Leadership/Compliance/Underwriting)
- **Generate button**: POST submission with loading state
- **JavaScript fetch**: Handles form submission and opens report in new window
- **Marsh branding**: Blue color scheme with clean modern design
- **Error handling**: Displays error messages for failed pipeline runs

**User experience**: Click → Loading → Report opens in new window (ready for validation)

### 4. Main App Integration
**File**: `app/main.py` (modified)

Connected admin router to FastAPI application:
- Import admin router
- Register with `app.include_router(admin_router)`
- Enables `/admin/*` endpoint namespace

### 5. Pipeline Test Script
**File**: `scripts/test_pipeline.py`

Standalone test tool for manual pipeline validation:
- Initializes all services with environment credentials
- Executes full pipeline workflow
- Writes HTML to `data/pipeline_test.html`
- Prints detailed results: run_id, counts, timing, status
- **Not for automation** - requires live API credentials

## Technical Implementation

### Pipeline Orchestration Pattern
```python
PipelineOrchestrator(collector, classifier, reporter)
  ↓
run_full_pipeline(role="Brokers")
  ↓
collector.collect_from_sources()  # Creates Run internally
  ↓
Query latest Run from DB
  ↓
Query articles for run_id
  ↓
classifier.classify_articles(db, articles)
  ↓
Re-query classified articles
  ↓
reporter.generate_role_brief(role, articles, date)
  ↓
Return {run_id, counts, html_output, status}
```

### Admin Router Pattern
- **APIRouter** with `/admin` prefix
- **Jinja2 Environment** for template rendering
- **Dependency injection** of settings and services
- **HTMLResponse** with custom headers for metadata
- **HTTPException** for configuration errors

### Error Handling Strategy
1. **Configuration validation** before execution (fail fast)
2. **Try/except wrapper** around pipeline execution
3. **Run status updates** on failure with error message
4. **HTTP 500** with detailed error messages for client debugging
5. **Structured logging** throughout for troubleshooting

## Verification

### Endpoint Structure
✅ POST `/admin/trigger-pipeline?role=Brokers` returns HTML report
✅ GET `/admin/trigger` serves admin UI
✅ GET `/admin/runs` returns run history JSON

### Integration Points
✅ Pipeline orchestrator uses collector, classifier, reporter services
✅ Admin router integrated into main FastAPI app
✅ Templates directory shared with reporter service

### Quality Checks
✅ Custom headers enable run tracking without API calls
✅ Error handling covers configuration, pipeline, and database errors
✅ Loading states prevent duplicate submissions

## Phase 1 Complete

**All 5 plans delivered**:
- 01-01: FastAPI app with database and models ✅
- 01-02: Apify-based news collection ✅
- 01-03: Azure OpenAI classification ✅
- 01-04: Tabbed HTML brief prototype ✅
- 01-05: Manual trigger endpoint ✅

**Vertical slice operational**: Visit `http://localhost:8001/admin/trigger`, select role, generate report → Complete intelligence brief with tabs, priorities, summaries.

**Ready for Phase 2**: Multi-source expansion with 18+ news sources.

## Next Phase Readiness

### Phase 2 Prerequisites Met
✅ Pipeline orchestration supports adding sources via Source table
✅ Fault-tolerant collection continues on individual source failures
✅ Classification service handles batch processing efficiently
✅ Reporter template accommodates variable article counts

### Phase 2 Expansion Path
- Add 17 more Source records to database
- Implement 17 new NewsSource scrapers (inherit from base class)
- Update ApifyCollector._get_source_scraper() mapping
- No changes needed to orchestrator, classifier, or reporter

### Future Enhancements (Phase 5+)
- **Email delivery**: Replace HTMLResponse with email sending
- **Scheduler integration**: Cron/APScheduler for daily automation
- **Run history UI**: Admin dashboard showing past runs with filtering
- **Error monitoring**: Alert system for pipeline failures

## Files Modified Summary

**Created (5 files)**:
- `app/services/pipeline.py` - Pipeline orchestration service (215 lines)
- `app/routers/__init__.py` - Router package initialization
- `app/routers/admin.py` - Admin endpoints (172 lines)
- `app/templates/admin_trigger.html` - Admin UI (242 lines)
- `scripts/test_pipeline.py` - Test script (132 lines)

**Modified (1 file)**:
- `app/main.py` - Admin router registration (2 lines changed)

**Total additions**: 763 lines of production code + templates

## Deviations from Plan

None - plan executed exactly as written.

## Commits

- `f849558`: feat(01-05): add pipeline orchestration service
- `2e1e94c`: feat(01-05): add admin router with trigger endpoint
- `004ebbc`: feat(01-05): add admin UI template for manual pipeline trigger
- `865f903`: feat(01-05): include admin router in FastAPI app
- `099d442`: feat(01-05): add pipeline test script
