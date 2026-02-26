# Codebase Structure

**Analysis Date:** 2026-02-26

## Directory Layout

```
/c/MDInsights/
├── app/                        # Python FastAPI application package
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, lifespan, health check, CLI entry point
│   ├── config.py               # Settings (pydantic-settings from .env)
│   ├── database.py             # SQLAlchemy engine, SessionLocal, Base
│   ├── logging_config.py       # Structured logging configuration
│   │
│   ├── auth/                   # Authentication & token management
│   │   ├── __init__.py
│   │   └── token_manager.py    # OAuth2 JWT token acquisition/caching (MMC Core API)
│   │
│   ├── models/                 # SQLAlchemy ORM models (database schema)
│   │   ├── __init__.py
│   │   ├── news_article.py     # NewsArticle model (titles, classification, roles)
│   │   ├── source.py           # Source model (news sources: RSS, Apify)
│   │   ├── run.py              # Run model (pipeline execution tracking)
│   │   ├── factiva_config.py   # FactivaConfig model (Factiva search params)
│   │   ├── equity_ticker.py    # EquityTicker model (company tickers)
│   │   └── api_event.py        # ApiEvent model (enterprise API health logging)
│   │
│   ├── schemas/                # Pydantic validation & response schemas
│   │   ├── __init__.py
│   │   ├── classification.py   # ArticleClassification (from Azure OpenAI)
│   │   ├── delivery.py         # EmailRecipients, delivery configuration
│   │   ├── report.py           # ExecutiveSummary, WhatToWatch, report structures
│   │   └── admin.py            # SourceCreate, SourceUpdate (admin CRUD)
│   │
│   ├── services/               # Business logic and integrations
│   │   ├── __init__.py
│   │   ├── pipeline.py         # PipelineOrchestrator (main collect→classify→report→email flow)
│   │   ├── collector.py        # ApifyCollector (orchestrates news source collection)
│   │   ├── classifier.py       # RoleClassificationService (Azure OpenAI integration)
│   │   ├── reporter.py         # RoleReportService (Jinja2 HTML generation)
│   │   ├── emailer.py          # GraphEmailService (Microsoft Graph email)
│   │   ├── enterprise_emailer.py # EnterpriseEmailClient (MMC Core API email, Phase 12)
│   │   ├── deduplicator.py     # ArticleDeduplicator (semantic similarity matching)
│   │   ├── aggregator.py       # ReportAggregator (article filtering & aggregation)
│   │   ├── health_monitor.py   # SourceHealthMonitor (tracks source success rates)
│   │   ├── drift_monitor.py    # DriftMonitor (statistical classification drift detection)
│   │   ├── backup_manager.py   # Database backup to Azure Blob Storage
│   │   ├── search.py           # ArticleSearchService (FTS5 full-text search)
│   │   │
│   │   └── sources/            # Concrete NewsSource implementations
│   │       ├── __init__.py
│   │       ├── base.py         # NewsSource abstract base class (interface)
│   │       ├── rss_source.py   # Generic RSS feed scraper
│   │       ├── artemis.py      # Artemis.bm catastrophe news scraper
│   │       ├── reinsurance_news.py
│   │       ├── insurance_journal.py
│   │       ├── business_insurance.py
│   │       └── lloyds_list.py
│   │
│   ├── collectors/             # Alternative collection strategies (Phase 10+)
│   │   ├── __init__.py
│   │   ├── factiva.py          # FactivaCollector (news via MMC Core API)
│   │   └── equity.py           # EquityPriceClient (stock prices via MMC Core API)
│   │
│   ├── routers/                # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── admin.py            # Admin dashboard & CRUD endpoints
│   │   └── pipeline.py         # Pipeline control endpoints (/api/pipeline/*)
│   │
│   └── templates/              # Jinja2 HTML templates
│       ├── admin/              # Admin dashboard UI templates
│       │   ├── dashboard.html  # System status page
│       │   ├── sources.html    # Source management
│       │   ├── recipients.html # Email recipient management
│       │   ├── archive.html    # Report archive browser
│       │   ├── search.html     # Article search interface
│       │   ├── trigger.html    # Manual pipeline trigger form
│       │   └── partials/       # Reusable template components
│       │       ├── header.html
│       │       ├── sidebar.html
│       │       └── footer.html
│       │
│       └── email/              # Email report templates
│           ├── role_brief.html # Main intelligence brief template (multi-role HTML)
│           └── (premailer inlines CSS for email rendering)
│
├── scripts/                    # Utility and deployment scripts
│   ├── test_auth.py            # Validate MMC Core API JWT token acquisition
│   └── (Windows Task Scheduler integration scripts)
│
├── deploy/                     # Deployment configuration
│   ├── setup_task.ps1          # PowerShell script to register Windows Task Scheduler tasks
│   └── (Task definitions for pipeline, backup, drift check, monitor)
│
├── data/                       # Runtime data (created on startup)
│   ├── mdinsights.db           # SQLite database (created on first run)
│   ├── logs/                   # Structured log files (rotating)
│   │   └── mdinsights_*.log
│   ├── backups/                # Database backups
│   │   └── mdinsights_YYYY-MM-DD_HHmmss.db
│   └── archives/               # Generated HTML reports
│       └── YYYY-MM-DD_Role.html
│
├── docs/                       # Project documentation
├── .planning/                  # GSD planning artifacts
│   ├── codebase/               # Codebase analysis documents
│   │   ├── ARCHITECTURE.md     # This file's sibling
│   │   └── STRUCTURE.md        # Directory & file layout guide
│   ├── phases/                 # Phase planning & execution docs
│   └── milestones/             # Milestone tracking
│
├── .env                        # Environment configuration (git-ignored)
├── .env.example                # Example env vars for setup
├── .gitignore                  # Git exclusions
├── README.md                   # User-facing project overview
├── PROJECT.md                  # Technical project specification
├── md-insights.yaml            # Optional YAML configuration
└── requirements.txt            # Python package dependencies (pip)
```

## Directory Purposes

**app/**
- Purpose: Main Python package containing the FastAPI application
- Contains: ORM models, schemas, services, routes, templates, configuration
- Key files: main.py (app creation), config.py (settings), database.py (ORM setup)

**app/auth/**
- Purpose: Authentication and credential management for external APIs
- Contains: OAuth2 JWT token manager for MMC Core API (Phase 9+)
- Key files: token_manager.py (token acquisition and refresh)

**app/models/**
- Purpose: SQLAlchemy ORM model definitions representing database tables
- Contains: NewsArticle, Run, Source, FactivaConfig, EquityTicker, ApiEvent models
- Key files: news_article.py (main article storage with classification), run.py (pipeline tracking)

**app/schemas/**
- Purpose: Pydantic validation schemas separate from ORM models
- Contains: Request/response structures, output schemas for API handlers
- Key files: classification.py (Azure OpenAI output schema), delivery.py (email configuration)

**app/services/**
- Purpose: Business logic, external integrations, and orchestration
- Contains: Collector, Classifier, Reporter, Emailer, Pipeline orchestrator, specialized services
- Key files: pipeline.py (main orchestration), collector.py (news collection), classifier.py (AI classification)

**app/services/sources/**
- Purpose: Concrete implementations of NewsSource abstract interface
- Contains: RSS, Artemis, Reinsurance News, Insurance Journal, Business Insurance, Lloyd's List scrapers
- Key files: base.py (abstract interface), rss_source.py (generic RSS), artemis.py (catastrophe news)

**app/collectors/**
- Purpose: Alternative collection strategies beyond Apify/RSS
- Contains: Factiva collector (Phase 10), Equity price client (Phase 11)
- Key files: factiva.py (news via MMC API), equity.py (stock prices via MMC API)

**app/routers/**
- Purpose: FastAPI route handlers mapping HTTP endpoints to service operations
- Contains: Admin dashboard routes, pipeline API routes, source/recipient CRUD
- Key files: admin.py (dashboard & management), pipeline.py (programmatic execution)

**app/templates/**
- Purpose: Jinja2 HTML templates for admin UI and email reports
- Contains: Dashboard pages, CRUD forms, email report templates
- Key files: admin/dashboard.html (system overview), email/role_brief.html (intelligence report)

**data/**
- Purpose: Runtime directory for database, logs, backups, and generated reports
- Contains: SQLite database, structured logs, backup files, archived HTML reports
- Special: Created on first app startup via lifespan handler

**scripts/**
- Purpose: Utility scripts for testing and deployment
- Contains: Auth validation, Task Scheduler integration
- Key files: test_auth.py (MMC Core API token validation)

**deploy/**
- Purpose: Deployment configuration and setup automation
- Contains: PowerShell scripts for Windows Task Scheduler
- Key files: setup_task.ps1 (registers pipeline, backup, drift detection tasks)

**docs/**
- Purpose: Project documentation (user guides, API docs, architecture notes)
- Contains: README.md, PROJECT.md, technical specifications

**.planning/**
- Purpose: GSD (Get Stuff Done) planning artifacts for structured development
- Contains: Phase planning, milestone tracking, codebase analysis documents
- Key files: phases/ (execution plans), codebase/ (ARCHITECTURE.md, STRUCTURE.md)

## Key File Locations

**Entry Points:**

- `app/main.py` (lines 87-92): FastAPI app creation and router registration
- `app/main.py` (lines 301-369): CLI pipeline execution (`python -m app.main run-pipeline`)
- `app/routers/admin.py`: Admin dashboard HTTP entry point
- `app/routers/pipeline.py`: Programmatic pipeline control API
- `app/main.py` (lines 120-288): `/api/health` health check endpoint

**Configuration:**

- `app/config.py`: All environment variable loading and validation (Settings dataclass)
- `.env`: Runtime environment variables (git-ignored)
- `.env.example`: Example environment variables for setup

**Core Logic:**

- `app/services/pipeline.py`: Main orchestration (collect → classify → report → email)
- `app/services/collector.py`: News collection from enabled sources
- `app/services/classifier.py`: Azure OpenAI article classification with structured output
- `app/services/reporter.py`: Jinja2 HTML report generation with CSS inlining

**Testing:**

- No test/ directory present; tests should be added at root level
- `scripts/test_auth.py`: Auth validation for MMC Core API (functional test)

**Database & Persistence:**

- `app/database.py`: SQLAlchemy engine and session factory
- `app/models/`: All ORM model definitions
- `data/mdinsights.db`: SQLite database (created on startup)
- `data/backups/`: Database backup files

**Email & Delivery:**

- `app/services/emailer.py`: Microsoft Graph API email service
- `app/services/enterprise_emailer.py`: MMC Core API email service (fallback from Graph)
- `app/templates/email/role_brief.html`: Email report template

**Admin UI:**

- `app/templates/admin/`: All admin dashboard HTML templates
- `app/routers/admin.py`: Routes serving admin pages
- `app/schemas/admin.py`: Admin request/response schemas

## Naming Conventions

**Files:**

- Service files: lowercase with underscores (`classifier.py`, `token_manager.py`)
- Model files: lowercase with underscores (`news_article.py`, `api_event.py`)
- Router files: lowercase with underscores (`admin.py`, `pipeline.py`)
- Template files: lowercase with underscores, `.html` extension (`role_brief.html`, `dashboard.html`)

**Directories:**

- Package directories: lowercase, plural where appropriate (`models/`, `services/`, `schemas/`, `routers/`)
- Special directories: lowercase (`auth/`, `collectors/`, `templates/`, `data/`, `deploy/`, `scripts/`)
- Template subdirectories: function-based (`admin/`, `email/`)
- Template partials: in `partials/` subdirectory

**Classes:**

- Model classes: PascalCase (`NewsArticle`, `Run`, `Source`, `FactivaConfig`)
- Service classes: PascalCase, Service suffix (`ApifyCollector`, `RoleClassificationService`, `RoleReportService`)
- Schema/Pydantic classes: PascalCase (`ArticleClassification`, `EmailRecipients`, `ExecutiveSummary`)

**Functions & Methods:**

- Private/internal: leading underscore (`_prepare_articles`, `_get_enterprise_api_status`)
- Public methods: snake_case (`collect_from_sources`, `run_full_pipeline`, `send_email`)
- Handler functions: no prefix (`health_check`, `trigger_pipeline`)

**Constants:**

- Global configuration: UPPERCASE_WITH_UNDERSCORES (`PRIORITY_ORDER`, `INSURANCE_FALLBACK_SOURCES`, `CLASSIFICATION_PROMPT`)
- Stored in main.py or relevant service module

## Where to Add New Code

**New Feature:**
- Primary code: `app/services/{feature_name}.py` (service class implementing logic)
- Tests: Create `tests/services/test_{feature_name}.py` (pytest)
- Models if needed: `app/models/{entity_name}.py` (SQLAlchemy model)
- Schemas if needed: `app/schemas/{feature_name}.py` (Pydantic validation)
- Routes if API endpoint needed: Add endpoint to `app/routers/admin.py` or create `app/routers/{feature_name}.py`
- Templates if UI needed: `app/templates/admin/{feature_name}.html` (Jinja2)

**New Collection Source:**
- Implementation: `app/services/sources/{source_name}.py`
- Inherit from NewsSource abstract base in `app/services/sources/base.py`
- Implement `get_articles()` method returning list of dict
- Register in Source database table via admin UI or manual seeding

**New Integration (External API):**
- Service wrapper: `app/services/{integration_name}.py` or `app/collectors/{integration_name}.py`
- Authentication: Add credentials to `app/config.py` (Settings class)
- Health check: Add ApiEvent logging in `app/models/api_event.py`
- Error handling: Add graceful fallback in pipeline (e.g., Factiva → Apify fallback)

**Database Migration:**
- Schema change: Modify ORM model in `app/models/{model_name}.py`
- Migration logic: Add to `app/main.py` lifespan handler (see Phase 10 migration pattern lines 49-76)
- Data seeding: Add to lifespan or administrative endpoint

**Utilities & Helpers:**
- Shared helpers: `app/services/{domain}_{helper}.py` (e.g., `deduplicator.py`, `health_monitor.py`)
- Configuration helpers: Methods in `app/config.py` (Settings class) like `is_azure_openai_configured()`
- Logging setup: Extend `app/logging_config.py`

## Special Directories

**data/**
- Purpose: Runtime directory for volatile and persistent data
- Generated: Yes (created on startup via lifespan handler)
- Committed: No (excluded in .gitignore)
- Contains: SQLite database, logs, backups, HTML archives
- Initialization: `os.makedirs("data", exist_ok=True)` in main.py lifespan (line 45)

**.planning/**
- Purpose: GSD orchestration and planning artifacts
- Generated: No (manually created and version-controlled)
- Committed: Yes (part of repository for planning continuity)
- Contains: Phase execution plans, codebase analysis documents, milestone tracking
- Used by: GSD `/gsd:plan-phase` and `/gsd:execute-phase` commands

**app/templates/**
- Purpose: Jinja2 templates for rendering admin UI and email reports
- Generated: No (manually authored)
- Committed: Yes (part of application code)
- Contains: HTML templates with Bootstrap styling, CSS for email, Jinja2 filters
- Initialization: Loaded via Environment(FileSystemLoader(...)) in routers and services

---

*Structure analysis: 2026-02-26*
