---
phase: "01"
plan: "01-01"
plan-name: "project-scaffolding"
subsystem: "foundation"
tags: ["fastapi", "sqlalchemy", "pydantic", "azure-openai", "apify", "scaffolding"]

requires:
  - phases: []
  - capabilities: []

provides:
  - capabilities:
      - "FastAPI application with health check"
      - "SQLite database with multi-role article schema"
      - "Pydantic schemas for classification and reporting"
      - "Environment-based configuration"

affects:
  - phases: ["01-02", "01-03", "01-04", "01-05"]
  - note: "All Phase 1 plans depend on this scaffolding"

tech-stack:
  added:
    - "fastapi==0.115.0"
    - "sqlalchemy"
    - "pydantic==2.11.0"
    - "pydantic-settings"
    - "openai==2.16.0"
    - "azure-identity"
    - "apify-client"
    - "jinja2"
    - "premailer"
  patterns:
    - "SQLAlchemy ORM with declarative base"
    - "Pydantic Settings for environment configuration"
    - "FastAPI lifespan for database initialization"
    - "JSON column for multi-role arrays (SQLite workaround)"

key-files:
  created:
    - "app/main.py"
    - "app/database.py"
    - "app/config.py"
    - "app/models/news_article.py"
    - "app/models/source.py"
    - "app/models/run.py"
    - "app/models/__init__.py"
    - "app/schemas/classification.py"
    - "app/schemas/report.py"
    - "app/schemas/__init__.py"
    - ".env.example"
    - "requirements.txt"
    - ".gitignore"
  modified: []

decisions:
  - id: "ARCH-01-01-01"
    title: "Multi-role article schema with JSON array"
    rationale: "SQLite doesn't support native arrays, so using JSON text column for roles. Enables single article to belong to multiple roles (e.g., Brokers + Leadership)."
    alternatives: "Many-to-many relationship table, but adds complexity for Phase 1 vertical slice."
    impact: "Simple for Phase 1, may need migration to proper M2M in production."

  - id: "ARCH-01-01-02"
    title: "Port 8001 for MDInsights to avoid BrasilIntel conflict"
    rationale: "BrasilIntel runs on 8000, MDInsights on 8001 to allow parallel development."
    alternatives: "Dynamic port allocation, but harder for testing."
    impact: "Clear separation during development phase."

  - id: "ARCH-01-01-03"
    title: "Adapted BrasilIntel patterns for consistency"
    rationale: "Reuse proven patterns from BrasilIntel sister project for stability."
    alternatives: "Start from scratch, but higher risk."
    impact: "Faster development, known-good patterns."

metrics:
  duration: "3 minutes"
  completed: "2026-02-06"
  tasks-completed: 8
  tasks-total: 8
  commits: 8
  files-created: 13
  files-modified: 0
---

# Phase 01 Plan 01: Project Scaffolding Summary

**One-liner**: FastAPI foundation with multi-role article schema, Azure OpenAI + Apify integration, adapted from BrasilIntel patterns.

## Overview

Established complete FastAPI application scaffolding for MDInsights vertical slice, including:
- SQLite database with multi-role article schema (JSON array for role assignment)
- Pydantic schemas for Azure OpenAI structured outputs
- Environment-based configuration for Azure OpenAI, Microsoft Graph, Apify
- Health check endpoint validating all external service configurations

## What Was Built

### Application Structure
- **FastAPI app** with lifespan context manager for database initialization
- **Health check endpoint** (`/api/health`) validating:
  - Database connectivity
  - Data directory writability
  - Azure OpenAI configuration
  - Microsoft Graph configuration
  - Apify configuration
- Root redirect to `/docs` for API documentation

### Database Schema
- **NewsArticle model**: Multi-role article storage with JSON array for roles
  - Content fields: title, description, source_url, source_name, published_at
  - Classification fields: roles (JSON), priority, summary, sentiment
- **Source model**: News source configuration
  - Fields: name, url, source_type (apify|rss), actor_id, enabled
- **Run model**: Collection run tracking
  - Fields: started_at, completed_at, status, articles_collected, error_message

### Configuration
- **Pydantic Settings** with `.env` file loading
- Azure OpenAI: endpoint, api_key, deployment (gpt-4o), api_version
- Microsoft Graph: tenant_id, client_id, client_secret, sender_email
- Apify: token
- Application: debug, log_level, host (0.0.0.0), port (8001)
- Report: company_name (default "Marsh")

### Schemas
- **ArticleClassification**: roles (List[RoleType]), priority, summary, sentiment
- **RoleType**: Literal["Brokers", "Leadership", "Compliance", "Underwriting"]
- **PriorityType**: Literal["Critical", "High", "Medium", "Monitor"]
- **SentimentType**: Literal["positive", "negative", "neutral"]
- **ReportContext**: target_role, articles, report_date, company_name

## Task Completion

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | FastAPI application structure | bddf9ac | ✓ Complete |
| 2 | Database setup | eca5fd6 | ✓ Complete |
| 3 | Settings configuration | 1ccedad | ✓ Complete |
| 4 | Database schema (multi-role) | aee0b5c | ✓ Complete |
| 5 | Pydantic schemas | b9aaac1 | ✓ Complete |
| 6 | Environment template | 290426e | ✓ Complete |
| 7 | Python dependencies | 436c6c4 | ✓ Complete |
| 8 | .gitignore and data directory | 9420419 | ✓ Complete |

**All tasks completed successfully** (8/8)

## Verification Results

✓ FastAPI app starts successfully
✓ Health check endpoint returns structured status
✓ SQLite database created at `data/mdinsights.db`
✓ Environment variables loaded from .env
✓ `from app.models import NewsArticle, Source, Run` imports successfully
✓ `from app.schemas.classification import ArticleClassification` imports successfully
✓ No import errors or missing dependencies

## Deviations from Plan

None - plan executed exactly as written.

## Technical Decisions

### Multi-Role Article Schema
Chose JSON text column for `roles` field instead of many-to-many relationship table:
- **Rationale**: SQLite doesn't support native arrays; JSON text is simplest for Phase 1
- **Trade-off**: Less queryable than M2M table, but sufficient for vertical slice
- **Future**: May migrate to proper M2M relationship in production

### Port 8001 Selection
MDInsights runs on port 8001 (vs BrasilIntel on 8000):
- **Rationale**: Allows parallel development and testing of both systems
- **Trade-off**: Must document port assignment in deployment
- **Future**: Production will use standard ports or reverse proxy

### Pattern Adaptation
Adapted proven patterns from BrasilIntel sister project:
- **Rationale**: Reuse stable database, configuration, and health check patterns
- **Trade-off**: Some unnecessary complexity for simpler MDInsights use case
- **Future**: Simplify after Phase 1 validation

## Dependencies

### Required By This Plan
- Nothing (first plan in project)

### Provided For Next Plans
- **01-02**: Database schema for articles (Run, NewsArticle models)
- **01-03**: Settings configuration for Azure OpenAI client
- **01-04**: Pydantic schemas for classification
- **01-05**: FastAPI app structure for admin router

## Key Files Reference

**Application Core**:
- `app/main.py` - FastAPI app with health check
- `app/database.py` - SQLAlchemy engine and session
- `app/config.py` - Pydantic Settings

**Models**:
- `app/models/news_article.py` - Multi-role article schema
- `app/models/source.py` - News source configuration
- `app/models/run.py` - Collection run tracking

**Schemas**:
- `app/schemas/classification.py` - ArticleClassification, RoleType, PriorityType, SentimentType
- `app/schemas/report.py` - ReportContext

**Configuration**:
- `.env.example` - Environment template
- `requirements.txt` - Python dependencies
- `.gitignore` - Git ignore rules

## Next Phase Readiness

**Ready for 01-02** (Apify Integration):
- ✓ Database schema for articles exists
- ✓ Run model for tracking collection exists
- ✓ Settings configuration for Apify token ready

**Blockers**:
- Requires Apify account and token configuration in `.env`

**Ready for 01-03** (Azure OpenAI Client):
- ✓ Settings configuration for Azure OpenAI exists
- ✓ Pydantic schemas for structured outputs ready

**Blockers**:
- Requires Azure AD app registration and OpenAI deployment

**Ready for 01-04** (Classification Service):
- ✓ ArticleClassification schema ready
- ✓ NewsArticle model with classification fields ready

**Ready for 01-05** (Admin Interface):
- ✓ FastAPI app structure ready for router registration
- ✓ Database models ready for CRUD operations

## Lessons Learned

1. **Pattern reuse is valuable**: Adapting BrasilIntel patterns saved significant time and reduced risk
2. **JSON columns are pragmatic**: For SQLite and simple use cases, JSON text columns are sufficient
3. **Port conflicts matter**: Explicit port assignment (8001) prevents development friction
4. **Health checks should be comprehensive**: Including external service configuration validation catches setup issues early
