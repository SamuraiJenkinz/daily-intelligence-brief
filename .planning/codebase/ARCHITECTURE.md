# Architecture

**Analysis Date:** 2026-02-26

## Pattern Overview

**Overall:** FastAPI service with a collect-classify-generate-deliver pipeline pattern, following a layered architecture with clear separation between HTTP routing, business services, and data models.

**Key Characteristics:**
- Command-query separation: Web API (admin) vs. CLI pipeline execution (scheduled tasks)
- Dependency injection via initialization parameters for testability
- Structured logging throughout for observability
- Graceful degradation with fallback mechanisms (e.g., Graph API fallback when enterprise email unavailable)
- Multi-source collection orchestration with deduplication and semantic similarity matching

## Layers

**HTTP API Layer:**
- Purpose: Expose admin dashboard and programmatic endpoints for manual pipeline triggering, source management, and report viewing
- Location: `app/routers/` (admin.py, pipeline.py)
- Contains: Route handlers, request/response schemas, templating for HTML admin UI
- Depends on: Service layer, database models, configuration
- Used by: Web browsers (admin UI), external systems (manual triggers)

**Service Layer:**
- Purpose: Encapsulate business logic for collection, classification, report generation, email delivery, and orchestration
- Location: `app/services/` (collector.py, classifier.py, reporter.py, emailer.py, enterprise_emailer.py, pipeline.py, and specialized modules)
- Contains: Core workflow logic, external API integrations, orchestration
- Depends on: Database models, ORM sessions, external SDKs (Apify, Azure OpenAI, Microsoft Graph)
- Used by: Route handlers (HTTP), CLI mode (scheduled tasks)

**Data Model Layer:**
- Purpose: Define database schema and ORM models with business-relevant properties
- Location: `app/models/` (news_article.py, source.py, run.py, factiva_config.py, equity_ticker.py, api_event.py)
- Contains: SQLAlchemy declarative models with relationships
- Depends on: SQLAlchemy, Python standard library
- Used by: Service layer queries, database persistence

**Data Validation & Schemas:**
- Purpose: Define request/response structures and validation rules separate from ORM models
- Location: `app/schemas/` (admin.py, classification.py, delivery.py, report.py)
- Contains: Pydantic models for API input validation and structured outputs from classification
- Depends on: Pydantic
- Used by: Route handlers (request validation), Service layer (structured outputs)

**Configuration & Infrastructure:**
- Purpose: Centralized settings management and database initialization
- Location: `app/config.py` (settings), `app/database.py` (SQLAlchemy setup), `app/logging_config.py` (structured logging)
- Contains: Environment variable loading, service configuration validation, connection pool setup
- Depends on: Pydantic-settings, Python-dotenv, SQLAlchemy
- Used by: All layers during initialization

**Authentication & Authorization:**
- Purpose: OAuth2 token management for MMC Core API and Microsoft Graph integration
- Location: `app/auth/token_manager.py` (JWT acquisition and refresh)
- Contains: Token caching, JWT refresh logic, credential validation
- Depends on: httpx, structlog
- Used by: Pipeline orchestrator, enterprise emailer

## Data Flow

**Collection Pipeline:**

1. PipelineOrchestrator.run_full_pipeline() initializes
2. Creates Run record with RUNNING status
3. ApifyCollector.collect_from_sources() queries Source table for enabled sources
4. For each source, instantiate appropriate scraper (RSSSource, ArtemisSource, etc.)
5. Execute scraper.get_articles(), collect raw NewsArticle objects
6. ArticleDeduplicator checks semantic similarity against existing articles (using sentence-transformers)
7. Store deduplicated articles in news_articles table with run_id foreign key
8. Update Run status to reflect progress

**Classification Pipeline:**

1. Query all unclassified articles (roles IS NULL) from news_articles table
2. Batch articles (default 10 per request) into RoleClassificationService
3. Send to Azure OpenAI GPT-4o with structured output schema enforcing ArticleClassification response
4. Parse structured response: roles (array), priority (enum), summary, sentiment, entities, impact_level, category, region, business_line
5. Update each article in database with classification results
6. Log classification metrics (total classified, role distribution, priority distribution)

**Report Generation:**

1. Query all classified articles from database
2. RoleReportService.prepare_articles() transforms NewsArticle ORM objects to dicts with parsed JSON fields
3. ReportAggregator.build_report_context() filters articles by role and priority, calculates metadata (entity counts, sector heatmap)
4. For each role (Brokers, Leadership, Compliance, Underwriting):
   - Filter articles to role membership
   - Sort by priority (Critical > High > Medium > Monitor)
   - Render Jinja2 template (role_brief.html) with context
   - Inline CSS using premailer for email compatibility
5. Archive generated HTML to data/archives/{date}_{role}.html

**Email Delivery:**

1. Check if enterprise email (MMC Core API) is configured
2. If configured and authorized: EnterpriseEmailClient sends via MMC email API (with JWT Bearer + X-Api-Key)
3. If not configured or auth fails: GraphEmailService sends via Microsoft Graph (fallback)
4. Each role gets separate email to its recipients (TO/CC/BCC from configuration)
5. Log ApiEvent record with delivery status and timestamp

**State Management:**

- Run: Tracks pipeline execution (id, status, started_at, completed_at, articles_collected, articles_classified)
- NewsArticle: Stores article content and multi-role classification (roles stored as JSON string)
- Source: Tracks enabled news sources (name, type, url, enabled flag)
- FactivaConfig: Stores Factiva collector configuration (industry codes, keywords, page size)
- EquityTicker: Stores company tickers for equity price enrichment
- ApiEvent: Logs enterprise API health (api_name, event_type, timestamp, reason) for monitoring

## Key Abstractions

**NewsSource (Abstract Base):**
- Purpose: Define common interface for all news source scrapers
- Examples: `app/services/sources/rss_source.py`, `app/services/sources/artemis.py`, `app/services/sources/business_insurance.py`
- Pattern: Template method pattern — subclasses override get_articles() with source-specific scraping logic
- Returns: List of dict objects with title, description, source_url, source_name, published_at

**ArticleClassification (Pydantic Schema):**
- Purpose: Enforce structured output schema from Azure OpenAI with guaranteed validation
- Example: `app/schemas/classification.py`
- Pattern: Dataclass-like structure with field validators for enum constraints
- Used by: Classifier receives as response_format, parser validates and stores in database

**EmailRecipients (Delivery Schema):**
- Purpose: Represent role-specific email lists with TO/CC/BCC separation
- Example: `app/schemas/delivery.py`
- Pattern: Configuration object parsed from comma-separated env vars
- Used by: Emailer when constructing Graph API or MMC API payloads

**ReportContext (Report Aggregation):**
- Purpose: Aggregate article data with metadata for template rendering
- Example: `app/services/aggregator.py`
- Pattern: Builder pattern for constructing complex report data structures
- Used by: RoleReportService when calling Jinja2 template.render()

## Entry Points

**HTTP Server:**
- Location: `app/main.py` lines 87-92 (FastAPI app creation)
- Triggers: `python -m app.main` (default) or via Uvicorn
- Responsibilities:
  - Register routers (admin, pipeline)
  - Define lifespan for startup/shutdown hooks
  - Initialize database tables
  - Seed default configuration rows

**Admin Router:**
- Location: `app/routers/admin.py`
- Triggers: HTTP requests to `/admin/*` endpoints
- Responsibilities:
  - Serve admin dashboard HTML
  - Source CRUD operations
  - Recipient management
  - Manual pipeline trigger
  - Report archive browsing
  - Search functionality

**Pipeline Router:**
- Location: `app/routers/pipeline.py`
- Triggers: HTTP requests to `/api/pipeline/*` endpoints
- Responsibilities:
  - Provide programmatic pipeline execution endpoint
  - Return run status and results as JSON

**CLI Pipeline Execution:**
- Location: `app/main.py` lines 301-369 (run-pipeline mode)
- Triggers: `python -m app.main run-pipeline` (called by Windows Task Scheduler)
- Responsibilities:
  - Initialize services (collector, classifier, reporter)
  - Initialize TokenManager for MMC auth
  - Execute PipelineOrchestrator.run_full_pipeline_with_email()
  - Send emails to role recipients
  - Archive HTML reports
  - Exit with success/failure code

**Health Check Endpoint:**
- Location: `app/main.py` lines 120-288 (`/api/health`)
- Triggers: HTTP GET requests from load balancer or monitoring systems
- Responsibilities:
  - Validate database connectivity
  - Check data directory writability
  - Verify external service configuration
  - Check backup freshness
  - Report logging directory status
  - Return overall status (healthy/degraded/unhealthy)

## Error Handling

**Strategy:** Layered validation with graceful degradation and comprehensive logging

**Patterns:**

- **Soft Failures (Degraded Status):** Enterprise APIs missing → use fallback (Graph API if MMC unavailable, RSS if Factiva unavailable)
- **Hard Failures (Pipeline Abort):** Classification service unreachable → retry with exponential backoff, then fail run
- **Validation Errors:** Request validation via Pydantic → return 422 with field-level error details
- **Unhandled Exceptions:** Global exception handler logs full context, returns generic 500 response
- **Database Transaction Rollback:** All service methods wrap database operations in try-except, rollback on error
- **Retry Logic:** Tenacity library with exponential backoff for network operations (Apify, OpenAI, Graph API, MMC API)

**Global Exception Handler:**
- Location: `app/main.py` lines 99-117
- Logs method, path, exception, and full traceback
- Returns JSON 500 to prevent information leakage

**Retry Decorator Usage:**
- Collector (Apify calls): 3 retries with exponential backoff
- Classifier (Azure OpenAI): 3 retries with exponential backoff
- Emailer (Graph API, MMC API): 3 retries with exponential backoff

## Cross-Cutting Concerns

**Logging:** Structured logging via structlog library with context binding
- Patterns: logger.bind(service="collector").info("collection_started", run_id=123)
- Configuration: `app/logging_config.py` sets level from env (default INFO), outputs to rotating files in data/logs/
- Integration: All services use structlog.get_logger(__name__) for module-specific context

**Validation:** Multi-layer validation strategy
- Request: Pydantic models in schemas/ validate HTTP input
- Output: ArticleClassification enforces Azure OpenAI response shape
- Configuration: Settings dataclass validates all env vars at startup via is_*_configured() checks
- Database: ORM constraints (nullable, foreign keys) prevent invalid state

**Authentication:**
- OAuth2 JWT: TokenManager acquires and caches tokens from MMC Core API (Phase 9)
- Daemon Auth: GraphEmailService uses ClientSecretCredential for Graph API (Phase 5)
- API Key: Direct X-Api-Key headers for Factiva (Phase 10) and Equity API (Phase 11)
- Token Caching: TokenManager stores token in memory with refresh before expiry

**Resilience:**
- Fallback Pattern: MMC unavailable → use Graph API; Factiva unavailable → use Apify/RSS only
- Deduplication: ArticleDeduplicator prevents duplicate articles across runs using semantic similarity
- Health Monitoring: SourceHealthMonitor tracks source success rates
- Drift Detection: DriftMonitor uses statistical tests (KS test, chi-square) to detect classification behavior changes

---

*Architecture analysis: 2026-02-26*
