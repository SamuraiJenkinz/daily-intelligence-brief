# Technology Stack

**Analysis Date:** 2026-02-26

## Languages

**Primary:**
- Python 3.9+ - Backend API, news collection, classification pipeline, database migrations

**Secondary:**
- HTML/CSS/JavaScript - Admin dashboard UI with HTMX and Bootstrap

## Runtime

**Environment:**
- Python runtime environment with venv virtual environment
- Windows 10+ (for Task Scheduler automation)

**Package Manager:**
- pip (Python package manager)
- Lockfile: `requirements.txt` (pinned versions)

## Frameworks

**Core:**
- FastAPI 0.115.0 - REST API framework, async request handling
- Uvicorn - ASGI web server (standard extras for production)

**ORM & Database:**
- SQLAlchemy - Database ORM for SQLite operations
- SQLite - Embedded relational database at `./data/mdinsights.db`

**API & HTTP:**
- httpx - Async HTTP client for external API calls (Apify, Factiva, Graph, equity prices)
- Apify Client - Web scraping SDK for multi-source article collection

**AI & Computation:**
- OpenAI SDK 2.16.0 - Azure OpenAI GPT-4o API client (classification, summarization)
- sentence-transformers ≥5.0.0 - Semantic embeddings for article deduplication
- scipy - Statistical analysis for drift detection (KS test, chi-square)

**Email & HTML:**
- Jinja2 - HTML template engine for role-specific brief generation
- Premailer - CSS inlining for email-safe HTML (Graph API, MMC email endpoints)

**Authentication & Identity:**
- azure-identity - Azure AD authentication (ClientSecretCredential for Graph API daemon mode)

**Data & Configuration:**
- pydantic 2.11.0 - Data validation and parsing
- pydantic-settings - Environment variable loading and validation
- python-dotenv - .env file parsing for local development
- python-multipart - Multipart form data handling for admin uploads

**Structured Logging:**
- structlog - Structured, JSON-compatible logging for pipeline observability

**Resilience & Retry:**
- tenacity - Exponential backoff retry logic for external API calls (Apify, Graph, Factiva, equity, email)
- feedparser 6.0.12 - RSS/Atom feed parsing for content sources

## Key Dependencies

**Critical:**
- fastapi==0.115.0 - Request routing, async context management, API responses
- sqlalchemy - Database persistence, ORM models for articles, sources, runs, API events
- openai==2.16.0 - GPT-4o classification via Azure OpenAI (Phase 4+)
- apify-client - Web scraping orchestration from 18+ news sources (Phase 1+)
- httpx - Async HTTP for external integrations (required for concurrent requests)

**Infrastructure:**
- uvicorn[standard] - Production ASGI server with WebSocket, SSL, and multiple workers
- pydantic-settings - Centralized credential management from environment variables
- python-dotenv - Local development environment configuration

**Azure/Microsoft Integration:**
- azure-identity - OAuth2 daemon app authentication for Graph API and MMC Core API JWT
- azure-core - Shared Azure SDK utilities
- azure-storage-blob - Blob service client for database backups to Azure

**News Collection & Processing:**
- sentence-transformers - Semantic similarity for deduplication (vs Levenshtein distance)
- feedparser - RSS feed parsing from sources like Lloyd's List
- scipy - Statistical drift detection for classification quality monitoring

**Email & Formatting:**
- jinja2 - HTML template rendering for role-specific briefs
- premailer - CSS inlining to ensure email client compatibility

## Configuration

**Environment:**
- `.env` file with 40+ configuration variables (see `.env.example`)
- Loaded via `app.config.py` using pydantic-settings at runtime
- Environment variables override defaults, no config files required

**Build:**
- No build system (pure Python, single-file configs)
- Database auto-initialization via `Base.metadata.create_all()` in FastAPI lifespan handler
- Startup migrations in `app.main.py` for schema changes (e.g., collector_source column)

**Key Config Files:**
- `app/config.py` - Centralized Settings class with 40+ env vars and validation methods
- `.env.example` - Template with all required and optional configurations with inline documentation
- `requirements.txt` - Frozen dependency versions for production reproducibility

## Platform Requirements

**Development:**
- Python 3.9+ with venv
- Windows 10+ (for Task Scheduler integration)
- Virtual environment: `python -m venv venv`

**Production:**
- Windows Server 2016+ (for Task Scheduler automation)
- Python 3.9+ runtime
- SQLite database file system access at `./data/mdinsights.db`
- Optional: Azure Storage account for backup uploads (when `AZURE_STORAGE_CONNECTION_STRING` is set)

**Deployment:**
- Windows Task Scheduler tasks configured via `deploy/setup_task.ps1`
- Four scheduled jobs: pipeline (06:00), backup (07:00), drift check (Monday 08:00), monitor (09:00)
- Local execution of `python -m app.main run-pipeline` or `python -m app.main run-backup`

**Server Binding:**
- Default: `0.0.0.0:8001` (all interfaces, port 8001)
- Configurable via `HOST` and `PORT` environment variables
- Debug mode via `DEBUG=true` environment variable

---

*Stack analysis: 2026-02-26*
