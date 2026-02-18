# Phase 9: OAuth2 Token Management - Research

**Researched:** 2026-02-18
**Source:** PDF API documentation on disk + existing codebase patterns

## Standard Stack

### Authentication Flow (from PDF docs)

The MMC Core API platform uses **Apigee** as its API gateway. Authentication varies by API:

| API | Auth Method | Headers Required |
|-----|-------------|------------------|
| Email (`/coreapi/email/v1`) | JWT Bearer + X-Api-Key | `Authorization: Bearer {token}`, `X-Api-Key: {apiKey}` |
| Data (`/coreapi/data/v1`) | JWT Bearer + X-Api-Key | `Authorization: Bearer {token}`, `X-Api-Key: {apiKey}` |
| Recent News / Factiva (`/coreapi/recent-news/v1`) | X-Api-Key only | `X-Api-Key: {apiKey}` |
| Equity Price (`/coreapi/equity-prices/v1`) | X-Api-Key only | `X-Api-Key: {apiKey}` |

**JWT is only needed for Email delivery (Phase 12).** Factiva and Equity use X-Api-Key independently.

### OAuth2 Client Credentials Grant

From `dataaip.pdf` and `emailref.pdf`, the auth flow is:

1. App registered in Apigee via YAML in `coreapi-infrastructure` repo
2. App must have `coreapi-access-management` proxy enabled
3. Client credentials grant: POST to Access Management API token endpoint
4. Returns JWT with expiry
5. JWT used as Bearer token alongside X-Api-Key

**Token endpoint** (inferred from Apigee standard pattern):
- Staging: `https://mmc-dallas-int-non-prod-ingress.mgti.mmc.com/coreapi/access-management/v1/token`
- The exact path may be `/oauth/token` or `/v1/token` — validate during implementation

**Request format** (standard OAuth2 client_credentials):
```
POST /coreapi/access-management/v1/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id={id}&client_secret={secret}
```

**Response format** (standard OAuth2):
```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Libraries to Use (matching existing codebase)

| Library | Purpose | Already in project |
|---------|---------|-------------------|
| `httpx` | HTTP client for token endpoint | Yes (`emailer.py`) |
| `structlog` | Structured JSON logging | Yes (all services) |
| `tenacity` | Retry with exponential backoff | Yes (`emailer.py`) |
| `pydantic-settings` | Config from env vars | Yes (`config.py`) |
| `sqlalchemy` | ORM for api_events table | Yes (`database.py`) |

**No new dependencies required.** The existing stack covers everything needed.

## Architecture Patterns

### Existing Service Pattern (from `emailer.py`)

```python
class GraphEmailService:
    def __init__(self):
        settings = get_settings()
        if not settings.is_graph_configured():
            logger.warning("not configured")
            self.credential = None
        else:
            self.credential = ClientSecretCredential(...)
```

**Pattern to follow for TokenManager:**
- Class-based service
- `__init__` reads config via `get_settings()`
- Validation method (`is_*_configured()`) on Settings
- Graceful handling when not configured
- `structlog.get_logger(__name__)` at module level

### Existing Config Pattern (from `config.py`)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", ...)

    # Group: credential fields with defaults
    microsoft_tenant_id: str = ""

    def is_graph_configured(self) -> bool:
        return bool(self.microsoft_tenant_id and ...)
```

**New fields to add:**
```python
# MMC Core API (Enterprise API proxy)
mmc_api_base_url: str = ""         # e.g. https://mmc-dallas-int-non-prod-ingress.mgti.mmc.com
mmc_api_client_id: str = ""        # Apigee app client_id
mmc_api_client_secret: str = ""    # Apigee app client_secret
mmc_api_key: str = ""              # X-Api-Key for the app
```

### Existing Model Pattern (from `run.py`)

```python
class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(RunStatus), ...)
    error_message = Column(Text, nullable=True)
```

**New model for `api_events`:**
- Same pattern: SQLAlchemy declarative, Enum for event types
- Designed to hold auth events now, extend for news/equity/email events in Phases 10-12
- Phase 13 reads this table for dashboard display

### Existing Pipeline Pattern (from `pipeline.py`)

```python
class PipelineOrchestrator:
    def __init__(self, collector, classifier, reporter):
        # Services injected via constructor

    def run_full_pipeline(self) -> Dict:
        # Step-by-step with structured logging per step
        # Try/except at top level with Run status update
```

**Integration point for Phase 9:** Token manager will be consumed by the pipeline in Plan 09-02. The pipeline needs a way to check auth status and set the degraded-auth flag.

### Existing Logging Pattern

```python
logger = structlog.get_logger(__name__)
logger.info("event_name", key1=val1, key2=val2)
logger.error("event_name", error=error_msg, exc_info=True)
```

**Auth events to log:**
- `token_acquired` — success with `expires_in` (never log the token itself)
- `token_refreshed` — proactive refresh before expiry
- `token_acquisition_failed` — with error context, sanitized
- `token_refresh_failed` — with error context

## Don't Hand-Roll

1. **Don't build a custom HTTP client** — use `httpx` (already a dependency)
2. **Don't build custom retry logic** — use `tenacity` (already a dependency)
3. **Don't build a config system** — extend existing `pydantic-settings` config
4. **Don't build a logging framework** — use existing `structlog` setup
5. **Don't store tokens in files/DB** — in-memory cache with TTL is sufficient (pipeline is a batch process, tokens only needed during the run)
6. **Don't implement token introspection/revocation** — not needed for client_credentials grant in a batch pipeline

## Common Pitfalls

### 1. Token Expiry Race Condition
**Problem:** Requesting a token, then using it 59 minutes later when it's about to expire.
**Prevention:** Refresh proactively with a safety margin (e.g., refresh when <5 minutes remain). Check `expires_in` from the token response, subtract a margin, and refresh before that threshold.

### 2. Logging Secrets
**Problem:** Accidentally logging `client_secret` or `access_token` in structured logs.
**Prevention:** Never pass token/secret values to logger. Log only: event type, timestamp, expires_in, error messages (sanitized), token endpoint URL.

### 3. Blocking the Pipeline on Auth Failure
**Problem:** JWT failure halts the entire pipeline, including Factiva and Equity which don't need JWT.
**Prevention:** The degraded-auth flag pattern from CONTEXT.md — JWT failure sets a flag, pipeline continues. Only Email delivery (Phase 12) checks this flag. Factiva (Phase 10) and Equity (Phase 11) use X-Api-Key independently.

### 4. Hardcoding the Token Endpoint
**Problem:** Token endpoint URL changes between environments (staging vs production).
**Prevention:** Base URL is already configurable via `mmc_api_base_url` env var. Token path appended at runtime. Swap the base URL between environments.

### 5. Not Validating Env Vars at Startup
**Problem:** Pipeline runs for 10 minutes collecting articles, then fails when it tries to get a token because `MMC_API_CLIENT_ID` is empty.
**Prevention:** Fail-fast validation on startup — check all required env vars exist and are non-empty. Log which vars are missing. This is a CONTEXT.md decision.

### 6. Retry Storm on Invalid Credentials
**Problem:** Retrying token acquisition with invalid credentials wastes time and may trigger rate limiting.
**Prevention:** Only retry on transient errors (network, 5xx). Don't retry on 401/403 (invalid credentials) — these won't succeed on retry.

## Code Examples

### Token Manager Structure

```python
# app/auth/token_manager.py
import time
from dataclasses import dataclass
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type

from app.config import get_settings

logger = structlog.get_logger(__name__)

@dataclass
class TokenInfo:
    access_token: str
    expires_at: float  # time.time() when token expires
    token_type: str = "Bearer"

class TokenManager:
    REFRESH_MARGIN_SECONDS = 300  # Refresh 5 min before expiry

    def __init__(self):
        settings = get_settings()
        self._token: TokenInfo | None = None
        self._base_url = settings.mmc_api_base_url
        self._client_id = settings.mmc_api_client_id
        self._client_secret = settings.mmc_api_client_secret

    def is_configured(self) -> bool:
        return bool(self._base_url and self._client_id and self._client_secret)

    @property
    def is_token_valid(self) -> bool:
        if not self._token:
            return False
        return time.time() < (self._token.expires_at - self.REFRESH_MARGIN_SECONDS)

    async def get_token(self) -> str | None:
        if self.is_token_valid:
            return self._token.access_token
        return await self._acquire_token()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def _acquire_token(self) -> str | None:
        # POST to token endpoint with client_credentials grant
        ...
```

### API Events Model Structure

```python
# app/models/api_event.py
class ApiEventType(str, enum.Enum):
    TOKEN_ACQUIRED = "token_acquired"
    TOKEN_REFRESHED = "token_refreshed"
    TOKEN_FAILED = "token_failed"
    # Phases 10-12 add: NEWS_FETCHED, EQUITY_FETCHED, EMAIL_SENT, etc.

class ApiEvent(Base):
    __tablename__ = "api_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(Enum(ApiEventType), nullable=False)
    api_name = Column(String(50), nullable=False)  # "access-management", "email", etc.
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, nullable=False)
    detail = Column(Text, nullable=True)  # JSON-encoded context, never secrets
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=True)
```

## Open Questions

1. **Exact token endpoint path**: The PDFs reference Access Management API but don't specify the exact `/token` path. Try `/coreapi/access-management/v1/token` first; the implementation should make this configurable so it can be adjusted without code changes.

2. **Token expiry duration**: Standard OAuth2 returns `expires_in` in seconds. Typical Apigee default is 3600s (1 hour). The code should use the value from the response, not hardcode it.

3. **Rate limiting on token endpoint**: Apigee may rate-limit token requests. The retry logic with exponential backoff handles this, but we should log rate-limit responses (429) distinctly.

---

*Phase: 09-oauth2-token-management*
*Researched: 2026-02-18*
