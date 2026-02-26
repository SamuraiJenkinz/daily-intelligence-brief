# Testing Patterns

**Analysis Date:** 2026-02-26

## Test Framework

**Runner:**
- pytest (implied by `.pytest_cache/` directory)
- Manual test scripts in `scripts/` directory (not pytest-based)

**Assertion Library:**
- Python built-ins: assertions, conditionals, exception handling
- No dedicated assertion library (tests use print statements and manual validation)

**Run Commands:**
```bash
python scripts/test_collection.py       # Test news collection
python scripts/test_classification.py   # Test article classification
python scripts/test_auth.py             # Test authentication
python scripts/test_advanced_classification.py  # Advanced classification tests
python scripts/test_pipeline.py         # Full pipeline test
python scripts/test_report.py           # Report generation test
```

## Test File Organization

**Location:**
- Test scripts in `scripts/` directory (separate from source)
- Not co-located with source files
- Manual test files, not automated pytest suite

**Naming:**
- Pattern: `test_*.py` for all test scripts
- Descriptive names matching feature: `test_collection.py`, `test_classifier.py`

**Structure:**
```
scripts/
├── test_collection.py      # ApifyCollector validation
├── test_classification.py  # RoleClassificationService validation
├── test_auth.py           # TokenManager JWT validation
└── test_pipeline.py       # End-to-end pipeline test
```

## Test Structure

**Suite Organization:**

Tests follow a manual CLI-based pattern rather than pytest fixtures. Each test script is standalone and executable.

Example from `scripts/test_collection.py`:
```python
#!/usr/bin/env python3
"""
Test collection script for MDInsights.

Tests the ApifyCollector service without running the full pipeline.
Validates that articles are properly scraped and stored in the database.

Usage:
    python scripts/test_collection.py

Requirements:
    - .env file with APIFY_TOKEN configured
    - Database seeded with test sources (run seed_sources.py first)
"""

def test_collection():
    """Test news collection from enabled sources."""
    # Load settings
    settings = get_settings()

    # Verify configuration
    if not settings.is_apify_configured():
        print("\n❌ Error: APIFY_TOKEN not configured in .env")
        sys.exit(1)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    try:
        # Setup
        collector = ApifyCollector(settings.apify_token)

        # Execute
        article_count = collector.collect_from_sources()

        # Validate
        db = SessionLocal()
        latest_run = db.query(Run).order_by(Run.id.desc()).first()

        # Assert state
        if latest_run:
            print(f"\n✅ Validation passed: All classification fields are NULL")

    except Exception as e:
        logger.error("test_collection_failed", error=str(e))
        sys.exit(1)

    finally:
        db.close()

if __name__ == "__main__":
    test_collection()
```

**Patterns:**
- Single test function per file, named `test_<feature>()`
- Setup phase: Load configuration, create instances
- Execution phase: Call service methods
- Validation phase: Query database, check state, print results
- Error handling phase: Catch exceptions, log with structlog, exit with status code

## Mocking

**Framework:** No mocking framework detected (tests are integration-focused)

**Pattern: Dependency Configuration:**
Tests don't mock external services; instead they:
1. Load real configuration from `.env`
2. Check if service is configured: `if not settings.is_apify_configured()`
3. Skip test or fail explicitly if requirements not met
4. Use real service instances with real credentials

Example from `scripts/test_classification.py:39-44`:
```python
if not settings.is_azure_openai_configured():
    print("❌ Azure OpenAI not configured. Please set environment variables:")
    print("   - AZURE_OPENAI_ENDPOINT")
    print("   - AZURE_OPENAI_API_KEY")
    print("   - AZURE_OPENAI_DEPLOYMENT")
    return
```

**What to Mock:**
- No explicit mocking in codebase (tests are integration tests)
- External services called with real credentials when available
- Database uses real SQLite instance (`data/mdinsights.db`)

**What NOT to Mock:**
- Database operations (tests validate actual DB state)
- External service calls (tests verify real API integration)
- Configuration loading (tests use real `.env` file)

## Fixtures and Factories

**Test Data:**
No fixture framework found. Test data patterns:

1. **Database Seeding:**
   - Tests assume pre-populated database (sources, runs, articles)
   - Separate seed scripts: `scripts/seed_sources.py` (inferred from test docs)
   - Manual data setup: `INSERT OR IGNORE INTO factiva_config ...` in `app/main.py:68-72`

2. **Configuration:**
   - Tests load from real `.env` file
   - Default fallback values in `Settings` class: `database_url: str = "sqlite:///./data/mdinsights.db"`

**Location:**
- No dedicated fixtures directory
- Configuration provided via `.env` file
- Database initialized in test via `Base.metadata.create_all(bind=engine)`

Example from `scripts/test_collection.py:44-45`:
```python
# Ensure tables exist
Base.metadata.create_all(bind=engine)
```

## Coverage

**Requirements:** No enforced coverage targets detected

**View Coverage:**
- No coverage configuration found
- Manual test scripts provide indirect coverage by testing service layers

## Test Types

**Unit Tests:**
- No isolated unit tests found
- Code uses real dependencies (database, API clients)
- Service methods tested with real external service calls

**Integration Tests:**
All test scripts are integration tests:
- `test_collection.py`: ApifyCollector + Source models + Database + Run tracking
- `test_classification.py`: RoleClassificationService + Azure OpenAI + Database + NewsArticle models
- `test_auth.py`: TokenManager + MMC Core API + OAuth2 flows

Example from `scripts/test_classification.py:28-110`:
```python
def test_classification():
    """
    Test classification on a small batch of unclassified articles.

    Queries database for unclassified articles from latest run,
    runs classification, and validates multi-role assignment.
    """
    # Load settings (real Azure OpenAI config)
    settings = get_settings()

    # Validate configuration
    if not settings.is_azure_openai_configured():
        print("❌ Azure OpenAI not configured...")
        return

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # Create real database session
    db = SessionLocal()

    try:
        # Query unclassified articles from real database
        unclassified_articles = (
            db.query(NewsArticle)
            .filter(NewsArticle.roles.is_(None))
            .order_by(desc(NewsArticle.created_at))
            .limit(5)
            .all()
        )

        # Real service instantiation with real credentials
        classifier = RoleClassificationService(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version
        )

        # Execute with real external API call
        for article in unclassified_articles:
            classification = classifier.classify_article(
                title=article.title,
                description=article.description,
                source=article.source_name
            )
```

**E2E Tests:**
- `test_pipeline.py`: Full pipeline from collection through email delivery
- Manual execution: `python app/main.py run-pipeline`
- Windows Task Scheduler integration for scheduled E2E tests

Example (pipeline execution):
```bash
python app/main.py run-pipeline      # Collect → Classify → Generate Reports → Email
```

## Common Patterns

**Async Testing:**
Not applicable (tests are synchronous, service layers handle async when needed)

**Error Testing:**
Pattern: Check for configuration before attempting operations

Example from `scripts/test_collection.py:39-42`:
```python
if not settings.is_apify_configured():
    print("\n❌ Error: APIFY_TOKEN not configured in .env")
    print("   Please add your Apify token to .env file")
    sys.exit(1)
```

**State Validation:**
Tests validate database state after operations

Example from `scripts/test_collection.py:93-101`:
```python
# Verify classification fields are NULL
classified_count = db.query(NewsArticle).filter(
    NewsArticle.run_id == latest_run.id,
    NewsArticle.roles.isnot(None)
).count()

if classified_count > 0:
    print(f"\n⚠️  Warning: {classified_count} articles already classified (expected all NULL)")
else:
    print(f"\n✅ Validation passed: All classification fields are NULL (as expected)")
```

**Progress Tracking:**
Tests print detailed output for human inspection

Example from `scripts/test_collection.py:83-90`:
```python
if articles:
    print(f"\n📝 Sample Articles (showing first 5):")
    for i, article in enumerate(articles, 1):
        print(f"\n   {i}. {article.title[:80]}...")
        print(f"      Source: {article.source_name}")
        print(f"      URL: {article.source_url}")
        print(f"      Published: {article.published_at}")
```

**Database Session Management:**
All test scripts follow consistent session pattern

Example pattern:
```python
db = SessionLocal()
try:
    # Perform operations
    results = db.query(Model).filter(...).all()

    # Validate
    assert_conditions(results)
finally:
    db.close()
```

## Service-Specific Testing Patterns

**ApifyCollector Testing:**
1. Verify `apify_token` is configured
2. Create `ApifyCollector` with real token
3. Call `collect_from_sources()` method
4. Validate `Run` record created in database
5. Check `NewsArticle` records have proper fields (no classification yet)
6. Summary statistics: total articles, runs, and database state

**RoleClassificationService Testing:**
1. Verify Azure OpenAI configured
2. Load unclassified articles from database
3. Create `RoleClassificationService` with real credentials
4. Call `classify_article()` for batch (5 articles)
5. Validate multi-role assignment (articles have roles, priority, sentiment)
6. Check Phase 3 fields populated (entities, impact_level, category, region, business_line)

**TokenManager (Auth) Testing:**
1. Load MMC Core API credentials
2. Attempt JWT token acquisition from staging endpoint
3. Validate token format and expiration
4. Test token refresh flow

**Pipeline Integration Testing:**
1. Full collection from all enabled sources
2. Classification of all collected articles
3. Report generation for each role
4. Email delivery validation (with Graph API or enterprise email)
5. Log file validation and archival

## Quality Practices

**Manual Testing Approach:**
- No automated test suite (pytest not configured for source code)
- Manual test scripts validate critical paths
- Integration tests check real service interactions

**Configuration-Driven Testing:**
- Tests check prerequisites before execution: `is_apify_configured()`, `is_azure_openai_configured()`
- Graceful skip if configuration missing (print message and return/exit)

**Validation Checkpoints:**
- Database state checks after each major operation
- Sample record inspection (first 5 articles, latest run)
- Statistics summary (total counts, status breakdown)
- Error field checking for anomalies

**Retry Logic Testing:**
Service layers use `@retry` decorator from `tenacity` for resilience:
- `retry_if_exception_type()` for specific exceptions
- `wait_random_exponential()` for backoff strategy
- `stop_after_attempt(3)` for attempt limits

Example from `app/services/classifier.py:150-156`:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, APITimeoutError, APIConnectionError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def classify_article(self, title: str, description: str, source: str) -> ArticleClassification:
```

---

*Testing analysis: 2026-02-26*
