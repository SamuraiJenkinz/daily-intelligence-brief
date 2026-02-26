# External Integrations

**Analysis Date:** 2026-02-26

## APIs & External Services

**News Collection:**
- **Apify** - Web scraping platform for multi-source article collection
  - SDK/Client: `apify-client` Python package
  - Auth: `APIFY_TOKEN` (personal API token from Apify console)
  - Usage: `app/services/collector.py` - ApifyCollector orchestrates scraping from 18+ sources
  - Sources: NewsNow, ReinsuranceNews, InsuranceJournal, BusinessInsurance, Artemis, LloydsList, RSS feeds
  - Free tier: $5/month credit (sufficient for testing), production usage $20-50/month

- **Factiva (via MMC Core API)** - Dow Jones Factiva news access (Phase 10+)
  - SDK/Client: httpx async HTTP client (custom wrapper)
  - Auth: X-Api-Key header only
  - Endpoint: `{MMC_API_BASE_URL}/coreapi/recent-news/v1/search` and `/article/{id}`
  - Config: `app/config.py` - `is_mmc_api_key_configured()`
  - Implementation: `app/collectors/factiva.py` - FactivaCollector class
  - Query params: industry codes (i82, i832), company codes (MM), keywords (insurance reinsurance)
  - Pagination: 25 articles per page (configurable), max 100 articles per run
  - Records: `app/models/api_event.py` - ApiEventType.NEWS_FETCH tracked per fetch

- **RSS Feeds** - Direct feed parsing from multiple sources
  - SDK/Client: `feedparser` 6.0.12 Python package
  - Implementation: `app/services/sources/sources.py` - RSSSource class
  - Sources: Lloyd's List, industry-specific RSS endpoints
  - No authentication required (public feeds)

**AI & Language Models:**
- **Azure OpenAI** - GPT-4o for article classification and summarization
  - SDK/Client: `openai` 2.16.0 Python package (AzureOpenAI client)
  - Auth: Azure API key + endpoint URL + deployment name
  - Endpoint: `{AZURE_OPENAI_ENDPOINT}` (must end with trailing slash)
  - Config: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION=2024-08-01-preview`
  - Usage: `app/services/classifier.py` - ClassificationService with structured outputs
  - Purpose: Classification by role (Brokers, Leadership, Compliance, Underwriting), priority, sentiment, entities, impact level, business line, region
  - Output format: JSON schema-enforced (ArticleClassification pydantic model)
  - Retry: tenacity with exponential backoff (3 attempts, max 10s wait)

## Data Storage

**Databases:**
- **SQLite** - Primary persistent storage
  - Connection: `sqlite:///./data/mdinsights.db` (configurable via `DATABASE_URL`)
  - Client: SQLAlchemy ORM
  - Models: `app/models/` - NewsArticle, Source, Run, RunStatus, ApiEvent, FactivaConfig, EquityTicker
  - Auto-initialization: Creates tables on FastAPI startup via `Base.metadata.create_all(bind=engine)`
  - Async: Check_same_thread=False for FastAPI async context

**File Storage:**
- **Local filesystem** - Database backups stored locally at `data/backups/`
- **Azure Blob Storage** - Optional backup upload destination
  - Service: Azure Storage Account Blob Service
  - Connection: `AZURE_STORAGE_CONNECTION_STRING` (optional)
  - Container: `AZURE_STORAGE_CONTAINER` (default: mdinsights-backups)
  - Client: `azure.storage.blob.BlobServiceClient`
  - Implementation: `app/services/backup_manager.py` - DatabaseBackupManager class
  - Retention: `BACKUP_RETENTION_DAYS` (default 30 days, old backups auto-deleted)
  - Backup file format: SQLite database dump (`.backup()` API, safe online backup)

**Caching:**
- None implemented at application level
- Session-level connection pooling via SQLAlchemy (check_same_thread=False for SQLite)

## Authentication & Identity

**Auth Provider:**
- **Azure Active Directory (Entra ID)** - OAuth2 daemon app authentication
  - Method: ClientSecretCredential (service-to-service, no user interaction)
  - Tenant ID: `MICROSOFT_TENANT_ID` (Directory ID from Azure AD)
  - Client ID: `MICROSOFT_CLIENT_ID` (Application ID from app registration)
  - Client Secret: `MICROSOFT_CLIENT_SECRET` (app secret, expires 24 months)
  - Scopes: `https://graph.microsoft.com/.default` for Graph API access
  - Implementation: `app/services/emailer.py` - GraphEmailService class
  - SDK: `azure-identity` - ClientSecretCredential provider

- **MMC Core API OAuth2** - JWT Bearer token acquisition (Phase 9+)
  - Method: OAuth2 Client Credentials Flow (JWT)
  - Token Endpoint: `{MMC_API_BASE_URL}/coreapi/access-management/v1/token`
  - Client ID: `MMC_API_CLIENT_ID`
  - Client Secret: `MMC_API_CLIENT_SECRET`
  - Token usage: Bearer {jwt} header for email and potentially other MMC endpoints
  - Implementation: `app/auth/mmc_auth.py` - MMCAuthManager class (Phase 9+)
  - Refresh: Token cached with automatic expiry refresh
  - Validation: `app/config.py` - `is_mmc_auth_configured()` method

## Monitoring & Observability

**Error Tracking:**
- Not detected - errors logged to structlog only

**Logs:**
- **structlog** - Structured, JSON-compatible logging
- Output: Console and file (via Windows Task Scheduler redirection to `data/logs/`)
- Format: Structured JSON with context binding (service, run_id, etc.)
- Level: Configurable via `LOG_LEVEL` environment variable (default: INFO)
- Implementation: `app/logging_config.py` - configure_logging() function

**Health Monitoring:**
- `app/services/health_monitor.py` - HealthMonitor class with async health checks
- Checks: Database connectivity, Azure OpenAI availability, Apify token, Microsoft Graph API, Backup manager status
- Endpoint: `/admin/health` - JSON response with component statuses

## CI/CD & Deployment

**Hosting:**
- Windows Server (local or on-premises)
- No cloud container deployment (Task Scheduler based)

**CI Pipeline:**
- None detected - manual deployment via git pull

**Execution Model:**
- Windows Task Scheduler with 4 scheduled jobs (configured by `deploy/setup_task.ps1`)
  - **Pipeline** (06:00 daily) - `python -m app.main run-pipeline`
  - **Backup** (07:00 daily) - `python -m app.main run-backup`
  - **Drift Check** (Monday 08:00) - `python -m app.main run-drift-check`
  - **Monitor** (09:00 daily) - `python -m app.main run-monitor`
- Web server: Manual execution via `python -m app.main` (FastAPI + Uvicorn on port 8001)

## Environment Configuration

**Required env vars (for full functionality):**
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI resource URL
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_DEPLOYMENT` - GPT-4o deployment name
- `APIFY_TOKEN` - Apify web scraping token
- `MICROSOFT_TENANT_ID` - Azure AD tenant ID
- `MICROSOFT_CLIENT_ID` - Azure AD app client ID
- `MICROSOFT_CLIENT_SECRET` - Azure AD app secret
- `SENDER_EMAIL` - Microsoft 365 mailbox for Graph API email sending
- `MMC_API_BASE_URL` - MMC Core API gateway URL
- `MMC_API_CLIENT_ID` - MMC OAuth2 client ID
- `MMC_API_CLIENT_SECRET` - MMC OAuth2 client secret
- `MMC_API_KEY` - MMC Core API X-Api-Key header
- `MMC_SENDER_EMAIL` - Enterprise email mailbox (for MMC email endpoint)

**Optional env vars:**
- `DATABASE_URL` - SQLite database path (default: sqlite:///./data/mdinsights.db)
- `DATA_DIR` - Data directory for backups and logs (default: ./data)
- `AZURE_STORAGE_CONNECTION_STRING` - Azure Blob Storage connection (for backup uploads)
- `AZURE_STORAGE_CONTAINER` - Blob container name (default: mdinsights-backups)
- `BACKUP_RETENTION_DAYS` - Backup retention period (default: 30)
- `DEBUG` - Enable debug mode (default: false)
- `LOG_LEVEL` - Logging verbosity (default: INFO)
- `HOST` - Server bind address (default: 0.0.0.0)
- `PORT` - Server port (default: 8001)
- `COMPANY_NAME` - Company name for report headers (default: Marsh)
- Email recipients (per role): `REPORT_RECIPIENTS_BROKERS`, `REPORT_RECIPIENTS_LEADERSHIP`, `REPORT_RECIPIENTS_COMPLIANCE`, `REPORT_RECIPIENTS_UNDERWRITING` + _CC and _BCC variants
- `ADMIN_EMAIL` - System admin email for failure alerts

**Secrets location:**
- `.env` file (local file, never committed to git)
- Template: `.env.example` with inline documentation
- Load method: pydantic-settings at `app/config.py` with LRU cache singleton

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- **Email delivery** - Microsoft Graph API
  - Endpoint: `https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail`
  - Method: POST with Bearer token authorization
  - Body: JSON message payload with recipients, subject, HTML body
  - Status code: 202 Accepted on success
  - Retry: 3 attempts with exponential backoff

- **Email delivery (MMC Enterprise)** - MMC Core API (Phase 12+)
  - Endpoint: `{MMC_API_BASE_URL}/coreapi/email/v1`
  - Method: POST with Bearer JWT + X-Api-Key headers
  - Body: JSON with recipients, subject, HTML body, sender impersonation
  - Status code: 200/202 on success
  - Retry: 2 attempts with random exponential backoff (rejects 401/403 without retry)
  - Implementation: `app/services/enterprise_emailer.py` - EnterpriseEmailClient class

- **MMC Core API integration** - Multiple endpoints (Phase 10, 11, 12)
  - Factiva Search: GET `/coreapi/recent-news/v1/search` + X-Api-Key
  - Article Fetch: GET `/coreapi/recent-news/v1/article/{id}` + X-Api-Key
  - Equity Price: GET `/coreapi/equity-price/v1/price?ticker={}&exchange={}` + X-Api-Key
  - Email Send: POST `/coreapi/email/v1` + Bearer JWT + X-Api-Key
  - Token Endpoint: POST `/coreapi/access-management/v1/token` (OAuth2)

## API Event Tracking

**Event Recording:**
- `app/models/api_event.py` - ApiEvent model records all external API interactions
- Event types: NEWS_FETCH (Factiva), EQUITY_FETCH (equity prices), EMAIL_SENT, EMAIL_FALLBACK (Graph API fallback), DRIFT_CHECK
- Captured data: event_type, status_code (HTTP), timestamp, run_id, details/error_message
- Accessible: `/admin/api-events` endpoint shows recent API call history
- Purpose: Dashboard visibility into integration health and API quota usage

---

*Integration audit: 2026-02-26*
