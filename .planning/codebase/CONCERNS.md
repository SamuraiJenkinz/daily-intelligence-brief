# Codebase Concerns

**Analysis Date:** 2026-02-26

## Tech Debt

**Complex monolithic router file:**
- Issue: `/app/routers/admin.py` is 1933 lines with 40+ endpoints handling sources, recipients, configuration, runs, and reports in a single file
- Files: `app/routers/admin.py`
- Impact: Difficult to maintain, high complexity for testing, mixed concerns (CRUD, templating, admin UI)
- Fix approach: Split into separate routers by domain (sources, recipients, config, runs, reports) using FastAPI's `APIRouter` with include_router pattern

**Large service files with multiple responsibilities:**
- Issue: `app/services/pipeline.py` (1150 lines) handles orchestration, error recovery, email delivery, enterprise auth, and fallback logic in one class
- Files: `app/services/pipeline.py`
- Impact: Hard to test individual workflows, difficult to understand error handling flows, tight coupling between concerns
- Fix approach: Refactor into separate service classes: PipelineOrchestrator, EmailDeliveryService, FallbackCoordinator with clear responsibility boundaries

**Query performance with .all() on large datasets:**
- Issue: Multiple calls to `.all()` without limits in pipeline execution (`app/services/pipeline.py:179, 256, 290, 352, 550`); loads entire tables into memory
- Files: `app/services/pipeline.py` (lines 179, 256, 290, 352, 550, 659, 762)
- Impact: Memory spikes with large article/ticker volumes; O(n) database hits; potential OOM crashes
- Fix approach: Use `.limit()` and batch processing; implement pagination for ticker mappings; add database indices on filter columns

**Admin UI state reconstruction:**
- Issue: Admin dashboard reconstructs complex state from database queries on each page load (enterprise API status, source counts, article counts, run history)
- Files: `app/routers/admin.py:53-130` (health check logic), templates in `app/templates/`
- Impact: High latency on dashboard loads; unnecessary database pressure; N+1 query patterns in some endpoints
- Fix approach: Implement response caching for stable metrics; use database views for aggregations; consider background job for dashboard data updates

## Known Bugs

**Async/Sync Context Management Issue:**
- Symptoms: `asyncio.run()` called from synchronous `run_full_pipeline()` when token_manager is available (`app/services/pipeline.py:122-131`)
- Files: `app/services/pipeline.py` (lines 122-131), `app/auth/token_manager.py`
- Trigger: Pipeline executed from synchronous context (FastAPI background task, direct call) attempts to acquire async JWT token
- Workaround: Pipeline correctly falls back to degraded auth when token acquisition fails
- Impact: Potential event loop conflicts in FastAPI's async context; token acquisition may fail silently

**Drift detection with insufficient baseline data:**
- Symptoms: `check_confidence_drift()` may run with zero or very few articles in baseline/recent windows, causing scipy stats to fail
- Files: `app/services/drift_monitor.py:68-130`
- Trigger: First week of operation, or if articles are sparse in time windows
- Workaround: Tests manually provide sufficient data; real-world sparse periods may silently fail
- Impact: Drift monitoring silently skipped on thin data; alerts not generated when needed

**Email fallback ordering ambiguity:**
- Symptoms: If MMC Core API fails, system falls back to Graph API; if Graph fails, no third fallback exists
- Files: `app/services/pipeline.py:1053-1140` (_send_with_fallback), `app/services/enterprise_emailer.py`
- Trigger: Both enterprise and Graph APIs unavailable simultaneously
- Workaround: Error is logged and recorded in api_events; manual intervention required
- Impact: Emails not delivered in complete outage scenario; recipients don't receive briefings

**Timezone inconsistency:**
- Symptoms: `datetime.utcnow()` used in most places but some endpoints may use local time; drift monitor uses `datetime.utcnow()`
- Files: `app/services/drift_monitor.py:86`, `app/services/backup_manager.py:73`, `app/routers/admin.py:200`
- Trigger: Deployment in non-UTC timezone; scheduled jobs at different times than intended
- Workaround: All timestamps stored as UTC; conversion happens at display time in templates
- Impact: Potential off-by-N-hours scheduling issues; backup retention calculations affected

## Security Considerations

**JWT token logging exposure:**
- Risk: Token value could be accidentally logged if exception includes full token response
- Files: `app/auth/token_manager.py:1-20` (security contract documented), `app/services/enterprise_emailer.py:18-24`
- Current mitigation: Code explicitly avoids logging token values; only event types logged; good documentation of security contract
- Recommendations: Add log filter that redacts bearer tokens from all logs; periodic audit of structlog calls to verify compliance; add secrets scanning to CI/CD

**API credentials in environment variables:**
- Risk: `.env` file contains plain-text secrets (Azure OpenAI key, Apify token, MMC API key, client secret)
- Files: `.env` (not committed), `.env.example` lists all required vars
- Current mitigation: `.env` is in `.gitignore`; documented in config.py
- Recommendations: Implement secrets manager integration (AWS Secrets Manager, Azure Key Vault) in production; rotate credentials on schedule; audit access to .env files

**Insufficient input validation on HTML/email payloads:**
- Risk: User-supplied article data (from news sources) is rendered in HTML reports without full sanitization
- Files: `app/services/reporter.py:99-250` (article preparation), `app/templates/` (Jinja2 templates use autoescape=True)
- Current mitigation: Jinja2 autoescape=True prevents XSS in template context; article titles/descriptions from trusted news APIs
- Recommendations: Validate article content against whitelist; escape entity names in JSON fields; add CSP headers if reports delivered via HTTP

**Fallback source data quality:**
- Risk: When Factiva unavailable, system falls back to Apify/RSS sources with less quality control
- Files: `app/services/pipeline.py:35-41` (INSURANCE_FALLBACK_SOURCES list), `app/services/collector.py`
- Current mitigation: Limited set of known sources used; health monitoring detects fallback state
- Recommendations: Add data quality metrics for fallback sources; implement additional deduplication for RSS sources; alert on extended Factiva outages

**Admin endpoints without authentication:**
- Risk: Admin panel (sources, recipients, config, runs) has no authentication/authorization checks
- Files: `app/routers/admin.py` (all endpoints)
- Current mitigation: Assumed to be deployed behind corporate auth layer; endpoints render HTML (low risk if exposed)
- Recommendations: Add FastAPI security dependency for OIDC/OAuth; implement role-based access control (RBAC); add rate limiting to prevent enumeration

## Performance Bottlenecks

**Sentence transformer model loading latency:**
- Problem: Deduplicator loads 80MB+ model on first use; blocks pipeline execution for 10-30 seconds
- Files: `app/services/deduplicator.py:69-74` (lazy loading), `app/services/pipeline.py:183-192` (first dedup call)
- Cause: Lazy loading in hot path; no pre-warming or async loading
- Improvement path: Pre-load model at startup; run in background thread; cache embeddings; use smaller model for production (distilbert)

**Azure OpenAI batch classification latency:**
- Problem: Classify articles one-by-one or in small batches; each call incurs API roundtrip and token overhead
- Files: `app/services/classifier.py`, `app/services/pipeline.py:256-264` (batch processing loop)
- Cause: Articles sent individually or in small groups; no batching optimization for API throughput
- Improvement path: Implement larger batch windows (10-20 articles); use async concurrent requests; implement circuit breaker for rate limits

**Email sending sequential:**
- Problem: Emails sent to multiple recipients/roles sequentially; blocks pipeline completion
- Files: `app/services/pipeline.py:600-650` (loop through recipients), `app/services/reporter.py:350-400` (report generation per role)
- Cause: Email loops are synchronous; network I/O blocks execution
- Improvement path: Generate all role reports in parallel; send emails concurrently with asyncio.gather(); implement connection pooling for email service

**Database query N+1 patterns:**
- Problem: Some admin endpoints execute query per source/run without batching
- Files: `app/routers/admin.py:206-215` (source_counts loop), dashboard aggregation queries
- Cause: Lack of query optimization; no use of SQLAlchemy eager loading
- Improvement path: Use `joinedload()` for relationships; aggregate at database layer; add query result caching

## Fragile Areas

**Jinja2 template error handling:**
- Files: `app/routers/admin.py:43-50` (template loading), `app/services/reporter.py:45-49` (template environment)
- Why fragile: FileSystemLoader fails silently if templates directory missing; no validation of template syntax at startup
- Safe modification: Add template validation in lifespan handler; validate all template files parse correctly before server starts
- Test coverage: No tests for template rendering failures; missing edge cases for malformed template data

**JSON field serialization/deserialization:**
- Files: `app/models/news_article.py` (roles, entities stored as TEXT), `app/services/classifier.py:307` (json.JSONDecodeError)
- Why fragile: Roles/entities stored as JSON strings in TEXT columns; deserialization scattered across codebase without consistent error handling
- Safe modification: Create JSONSchema validation helpers; centralize JSON field handling in model layer; add migration for invalid JSON values
- Test coverage: No tests for corrupt JSON in database; missing edge cases for partial JSON arrays

**Token refresh race condition:**
- Files: `app/auth/token_manager.py:95-117` (is_token_valid check), `app/services/pipeline.py:122-131` (token acquisition)
- Why fragile: Non-atomic check-then-act on token validity; two concurrent calls may both trigger refresh
- Safe modification: Use lock/semaphore around token state; implement atomic compare-and-swap; add jitter to refresh timing
- Test coverage: No concurrent access tests; missing race condition scenarios

**Migration without rollback:**
- Files: `app/main.py:49-79` (ALTER TABLE in startup)
- Why fragile: DDL changes don't rollback if subsequent operations fail; no version tracking
- Safe modification: Implement proper migration system (Alembic); separate migration from startup logic; add pre-migration backup
- Test coverage: No tests for migration failure scenarios; missing data integrity checks

## Scaling Limits

**Single database (SQLite):**
- Current capacity: ~5M articles at 1KB average = 5GB database; pipeline runs at ~1000 articles/hour
- Limit: SQLite scales to ~1GB reliably; concurrent writes block readers; no horizontal scaling
- Scaling path: Migrate to PostgreSQL for production; add read replicas; implement connection pooling with pgBouncer

**Sentence transformer GPU memory:**
- Current capacity: Model uses ~500MB VRAM; inference queue depth <50 articles
- Limit: OOM if batch size increases or model upgraded; no GPU auto-switching fallback
- Scaling path: Run deduplicator in separate process/container; implement batch queue with backpressure; add CPU fallback mode

**Email concurrency limits:**
- Current capacity: Sequential sends; ~10-15 emails per run (4 roles + ~2 distribution lists)
- Limit: Graph API has rate limits (429 responses); Enterprise API quota unknown; fallback exhaustion
- Scaling path: Implement email queue with backoff; add priority queue for critical alerts; implement async bulk send operations

**Memory usage with large article volumes:**
- Current capacity: Loads full article sets into memory for deduplication; ~1000 articles = 50-100MB
- Limit: OOM if article count exceeds available RAM; no streaming/chunking approach
- Scaling path: Process articles in batches; use lazy evaluation; implement memory-mapped deduplication

## Dependencies at Risk

**sentence-transformers (≥5.0.0):**
- Risk: Major version bump; dependency chain is deep (pytorch, transformers, scipy); model download on first use adds 30+ seconds
- Impact: Startup time increases; deployment complexity; potential GPU/CPU conflicts
- Migration plan: Evaluate smaller models (all-distilroberta-v1); implement model caching strategy; consider alternative semantic similarity (spacy, gensim)

**openai (==2.16.0):**
- Risk: Pinned version may have breaking changes in Azure OpenAI API; no async support for structured outputs in older versions
- Impact: Token manager and classifier may fail if API schema changes; limited support for new features
- Migration plan: Keep within minor version; add feature detection for API capabilities; implement fallback for structured output failures

**tenacity (retry library):**
- Risk: Used for token acquisition and email sending; improper exception handling may cause infinite retries
- Impact: Slow failure detection; resource exhaustion in retry loops
- Migration plan: Audit all retry configurations; add explicit max retry bounds; implement circuit breaker pattern

**scipy.stats:**
- Risk: Used for drift detection; distribution changes in new versions may break statistical tests
- Impact: Drift detection results non-comparable across versions; false positives/negatives
- Migration plan: Pin scipy version; add statistical test baseline snapshots; validate test results with known data

## Missing Critical Features

**Database backup verification:**
- Problem: Backups created but no automated restore testing; BitRot may occur silently
- Blocks: RTO/RPO guarantees for disaster recovery
- Recommendation: Implement automated backup restore tests; run weekly integrity checks; monitor backup sizes for anomalies

**Audit logging:**
- Problem: Admin changes (sources, recipients, config) not logged; no change history or approval workflow
- Blocks: Compliance requirements; root cause analysis for unexpected behavior
- Recommendation: Add audit table; log all admin API mutations with timestamp and user context; implement approval workflow

**Configuration hot-reload:**
- Problem: Changes to sources, recipients, Factiva config require pipeline restart
- Blocks: Zero-downtime updates; dynamic configuration management
- Recommendation: Implement config change webhooks; support reload without restart; add feature flags for gradual rollout

**Alerting & monitoring:**
- Problem: Health checks exist but no alerting system for failures; operators must manually monitor
- Blocks: Proactive incident response; SLA compliance; on-call automation
- Recommendation: Integrate with monitoring system (Prometheus metrics, CloudWatch); implement alerts for API failures, data quality, SLA breaches

## Test Coverage Gaps

**Pipeline orchestration end-to-end:**
- What's not tested: Full collection → classification → reporting → email workflow with actual Apify/Azure API calls
- Files: `scripts/test_pipeline.py` (exists but may have gaps), `app/services/pipeline.py`
- Risk: Critical path broken without detection; integration bugs only surface in production
- Priority: High - Consider adding integration tests with mocked external services; add golden data sets

**Error recovery scenarios:**
- What's not tested: Factiva → fallback transitions, email fallback (enterprise → Graph), token refresh race conditions
- Files: `app/services/pipeline.py:1053-1140`, `app/auth/token_manager.py`
- Risk: Errors silently fail; fallback chains don't work as expected; user sessions not notified of issues
- Priority: High - Add tests for each fallback scenario; verify error messages in api_events

**Concurrent requests to admin panel:**
- What's not tested: Multiple simultaneous config updates (sources, recipients); race conditions in database writes
- Files: `app/routers/admin.py` (all write endpoints)
- Risk: Data corruption in concurrent scenarios; config inconsistency
- Priority: Medium - Add concurrent update tests; implement optimistic locking if needed

**JSON field deserialization edge cases:**
- What's not tested: Corrupt JSON in database; null/missing roles/entities; unexpected JSON types
- Files: `app/models/news_article.py`, `app/services/pipeline.py:307` (json.JSONDecodeError handling)
- Risk: Pipeline crashes on malformed data; repair requires manual database editing
- Priority: Medium - Add tests for invalid JSON; implement defensive deserialization with defaults

**Email template rendering failures:**
- What's not tested: Missing template files, template syntax errors, special characters in article data
- Files: `app/templates/`, `app/services/reporter.py:99-250`
- Risk: Reports fail to generate silently; users don't receive briefings without notification
- Priority: Medium - Add template validation tests; implement fallback text-only delivery

---

*Concerns audit: 2026-02-26*
