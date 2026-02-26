# Coding Conventions

**Analysis Date:** 2026-02-26

## Naming Patterns

**Files:**
- Snake case with `.py` extension
- Module files match their primary class or function names: `classifier.py`, `collector.py`, `pipeline.py`
- Test scripts prefixed with `test_`: `test_collection.py`, `test_classification.py`
- Package directories: lowercase, plural for collections (`services/`, `models/`, `routers/`, `schemas/`)

**Functions and Methods:**
- Snake case for all functions and methods: `collect_from_sources()`, `classify_article()`, `get_settings()`
- Private methods prefixed with single underscore: `_parse_recipient_list()`
- Factory/getter functions: `get_email_recipients()`, `get_settings()`
- Command-like methods: `collect_from_sources()`, `classify_articles()`, `check_source_health()`

**Variables:**
- Snake case: `run_id`, `article_count`, `unclassified_articles`
- Boolean flags prefixed with `is_` or `has_`: `is_configured()`, `is_apify_configured()`
- Loop variables: Simple single letters or descriptive names: `idx`, `article`, `source`
- Constants: UPPER_CASE with underscores: `CLASSIFICATION_PROMPT`, `DATABASE_URL`

**Classes:**
- PascalCase: `NewsArticle`, `RoleClassificationService`, `ApifyCollector`, `SourceHealthMonitor`
- Model classes inherit from `Base` (SQLAlchemy): `class NewsArticle(Base)`
- Schema classes inherit from `BaseModel` (Pydantic): `class ArticleClassification(BaseModel)`
- Service classes end with "Service": `RoleClassificationService`, `RoleReportService`
- Collector classes end with "Collector": `ApifyCollector`

## Code Style

**Formatting:**
- No explicit linter/formatter config found
- Line length appears unconstrained (examples up to 100+ characters)
- Indentation: 4 spaces (standard Python)
- Imports: Follow PEP 8 style with grouped sections (stdlib, third-party, local)

**Linting:**
- No `.flake8`, `.pylintrc`, or `pyproject.toml` config found
- Code follows general PEP 8 conventions implicitly
- Unused imports marked with `# noqa: F401` when intentionally kept (e.g., model registration): See `app/main.py:18-20`

**Import Organization:**
- Group 1: Standard library imports (`logging`, `os`, `sys`, `json`)
- Group 2: Third-party imports (`fastapi`, `sqlalchemy`, `pydantic`, `structlog`)
- Group 3: Local app imports (`from app.config`, `from app.models`)
- Blank lines between groups

Example from `app/main.py`:
```python
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Request

from app.database import Base, engine, SessionLocal
from app.models import news_article, source  # noqa: F401
```

## Error Handling

**Pattern: Try-Except with Logging:**
- All exceptions logged with structured logging before raising or handling
- Exceptions caught at appropriate boundaries (service layer, route handlers)
- Global exception handler in `app/main.py:99-117` catches unhandled exceptions and logs with full context

Example from `app/services/classifier.py:209-215`:
```python
except Exception as e:
    self.logger.error(
        "classification_failed",
        title=title[:50],
        error=str(e)
    )
    raise
```

**Pattern: Graceful Degradation:**
- Features fail gracefully with fallback mechanisms
- Partial success is acceptable (e.g., classifier skips failed articles to continue batch processing)
- Admin endpoints return comprehensive health checks with degraded/warning statuses rather than hard failures

Example from `app/main.py:170-181`:
```python
if settings.is_azure_openai_configured():
    checks["external_services"]["azure_openai"] = {"status": "configured"}
else:
    checks["external_services"]["azure_openai"] = {"status": "warning"}
    if overall_status == "healthy":
        overall_status = "degraded"
```

**Pattern: Validation Before Operation:**
- Settings checked before use: `settings.is_apify_configured()`, `settings.is_mmc_auth_configured()`
- Database records validated before processing: `if article.roles is not None: continue`
- Configuration methods check all required fields: `is_mmc_email_configured()` checks JWT auth + API key + sender email

## Logging

**Framework:** `structlog` with JSON output

**Structured Logging Pattern:**
- All loggers initialized via `structlog.get_logger(__name__)` or `.bind()`
- Log events use structured key-value pairs, not formatted strings
- First argument is event name (snake_case, descriptive): `"classification_failed"`, `"article_classified"`, `"collection_started"`
- Additional context passed as keyword arguments

Example from `app/services/classifier.py:196-205`:
```python
self.logger.info(
    "article_classified",
    title=title[:50],
    roles=classification.roles,
    priority=classification.priority,
    sentiment=classification.sentiment,
    impact_level=classification.impact_level,
    category=classification.category,
    entity_count=len(classification.entities)
)
```

**Log Levels:**
- `.info()` for operational events: startup, completion, state changes
- `.debug()` for detailed processing: skipped articles, batch progress
- `.warning()` for issues that don't stop execution: missing config, degraded services, empty results
- `.error()` for exceptions and failures: logged before raising

**Truncation Pattern:**
- Long text values truncated to 50 chars: `title=title[:50]`
- Prevents log bloat while maintaining debuggability

## Comments

**When to Comment:**
- Class docstrings (every class has one explaining purpose and behavior)
- Method docstrings (every public method has one with Args, Returns, Raises sections)
- Complex logic blocks (e.g., migration logic in `app/main.py:49-79`)
- Non-obvious decisions or workarounds

Example from `app/database.py:13-14`:
```python
# SQLite requires check_same_thread=False for FastAPI's async context
# This is safe because SQLAlchemy handles connection pooling properly
```

**JSDoc/TSDoc:**
- Python uses docstrings (triple quotes)
- Format: Description, then Args, Returns, Raises sections
- Pydantic models use `Field()` with `description` parameter for schema documentation

Example from `app/config.py:143-155`:
```python
def _parse_recipient_list(self, recipients_str: str) -> list[str]:
    """
    Parse comma-separated recipient string into list.

    Args:
        recipients_str: Comma-separated email addresses

    Returns:
        List of email addresses with whitespace stripped
    """
```

## Function Design

**Size:** Functions typically 20-50 lines; complex operations split into helper methods
- Collector methods: 50-100 lines (orchestration)
- Service classification methods: 30-80 lines (retry logic + processing)
- Route handlers: 30-60 lines (request handling + response formatting)

**Parameters:**
- Type hints required for all function parameters and returns
- Self-documenting parameter names: `title`, `description`, `source`, `endpoint`, `api_key`
- Optional parameters use defaults: `api_version: str = "2024-08-01-preview"`
- Large configuration objects passed as class initialization: `RoleClassificationService(endpoint, api_key, deployment, api_version)`

**Return Values:**
- Explicit return types always specified: `-> int`, `-> dict`, `-> ArticleClassification`
- Void operations typically `-> None` or implicit
- Tuple returns when multiple values needed: Not commonly used; prefer dict or Pydantic model

Example from `app/services/classifier.py:157-207`:
```python
def classify_article(self, title: str, description: str, source: str) -> ArticleClassification:
    """
    Classify a single article using Azure OpenAI structured outputs.

    Args:
        title: Article title
        description: Article description/summary
        source: Source name

    Returns:
        ArticleClassification object with guaranteed schema compliance

    Raises:
        Exception: If classification fails (for retry logic)
    """
```

## Module Design

**Exports:**
- Classes exported explicitly (no wildcard imports in codebase)
- Service classes represent primary exports: `ApifyCollector`, `RoleClassificationService`
- Models imported directly from model files: `from app.models.news_article import NewsArticle`
- Schemas imported from schema files: `from app.schemas.classification import ArticleClassification`

**Barrel Files:**
- Package `__init__.py` files typically empty or import key classes
- Examples: `app/models/__init__.py`, `app/routers/__init__.py` are minimal
- Models registered via direct import in `main.py` for SQLAlchemy: `from app.models import news_article, source  # noqa: F401`

**Organization Pattern:**
- Models layer: ORM classes in `app/models/`
- Schemas layer: Pydantic validation schemas in `app/schemas/`
- Services layer: Business logic in `app/services/`
- Routers layer: FastAPI endpoints in `app/routers/`
- Configuration: `app/config.py` (Settings), `app/database.py` (DB), `app/logging_config.py` (Logging)

## Type Hints

**Style:**
- Comprehensive type hints throughout codebase
- Union types for optional: `title: str = None` or preferred `title: str | None`
- List types: `List[NewsArticle]` (imported from typing)
- Literal types for enums: `Literal["Critical", "High", "Medium", "Monitor"]`
- Pydantic Field() with description for structured schema validation

Example from `app/schemas/classification.py:47-52`:
```python
roles: List[RoleType] = Field(
    description="List of roles this article is relevant to. Can be multiple roles per article."
)
priority: PriorityType = Field(
    description="Priority level: Critical (immediate action), High (urgent attention), ..."
)
```

## Dependency Injection & Configuration

**Pattern: Cached Settings Singleton:**
- Settings managed via `pydantic-settings.BaseSettings`
- Singleton cached with `@lru_cache()` in `get_settings()` function
- All services receive configuration at instantiation: `RoleClassificationService(endpoint, api_key, deployment)`

Example from `app/config.py:188-195`:
```python
@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure only one Settings object is created.
    """
    return Settings()
```

**Pattern: Database Sessions:**
- SQLAlchemy sessions passed explicitly to service methods
- Sessions managed by route handlers (FastAPI context)
- Pattern: Create session → use in service → close in finally block

Example from `app/routers/pipeline.py:39-56`:
```python
db = SessionLocal()
try:
    results = health_monitor.check_all_sources(db)
finally:
    db.close()
```

## Validation

**Pydantic Models:**
- All API schemas use Pydantic `BaseModel`
- Field validation via Pydantic validators and `Field(description=...)`
- Literal types enforce enum-like validation at schema level

**Settings Validation:**
- Configuration methods check required fields: `is_azure_openai_configured()` checks endpoint AND api_key AND deployment
- Helper methods like `_parse_recipient_list()` handle data transformation safely

**Database Validation:**
- SQLAlchemy models define nullable columns explicitly: `Column(String, nullable=True)` vs `Column(String, nullable=False)`
- Relationships defined with `relationship()` and `back_populates` for bidirectional access

---

*Convention analysis: 2026-02-26*
