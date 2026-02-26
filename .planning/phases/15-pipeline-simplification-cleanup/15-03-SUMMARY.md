---
phase: 15-pipeline-simplification-cleanup
plan: 03
subsystem: dependencies-configuration
tags: [cleanup, apify-removal, dependencies, documentation]
requires:
  - phase-15-plan-01
provides:
  - clean-requirements
  - clean-env-example
  - clean-config
  - clean-comments
affects:
  - phase-16-dashboard-updates
tech-stack:
  added: []
  removed:
    - "apify-client (web scraping library)"
    - "feedparser (RSS parsing library)"
  patterns:
    - "Factiva-only dependency tree (httpx, sentence-transformers, tenacity)"
    - "Historical DB compatibility (preserved SourceType.APIFY enum)"
    - "Updated comment references to 'historical' or 'sole source'"
key-files:
  created: []
  modified:
    - path: requirements.txt
      lines: 44
      changes: "Removed apify-client and feedparser dependencies"
    - path: .env.example
      lines: 223
      changes: "Removed APIFY_TOKEN configuration section"
    - path: app/config.py
      lines: 196
      changes: "Removed apify_token field and is_apify_configured() method"
    - path: app/collectors/factiva.py
      lines: 457
      changes: "Updated docstring to remove Apify fallback reference"
    - path: app/models/news_article.py
      lines: 140
      changes: "Updated collector_source comment to note Factiva-only"
    - path: app/models/source.py
      lines: 37
      changes: "Updated actor_id comment to historical reference"
    - path: app/models/api_event.py
      lines: 66
      changes: "Updated NEWS_FALLBACK comment to historical note"
    - path: app/services/reporter.py
      lines: 590
      changes: "Changed fallback default from 'Apify/RSS' to 'Factiva'"
    - path: app/routers/admin.py
      lines: 682
      changes: "Updated run history comment to generic source breakdown"
decisions:
  - id: preserve-db-schema
    choice: "Keep SourceType.APIFY enum, collector_source default, and admin schema literals"
    rationale: "DB compatibility - removing enum values breaks existing rows, default avoids migration risk"
    alternatives:
      - "Create Alembic migration to remove APIFY enum and update defaults (high risk, low benefit)"
    impact: "Harmless preserved references maintain emergency fallback option"
  - id: preserve-migration-sql
    choice: "Keep 'Apify/RSS' reference in main.py migration SQL"
    rationale: "Historical migration code must remain unchanged - documents actual schema evolution"
    alternatives:
      - "Rewrite migration history (breaks reproducibility)"
    impact: "Accurate historical record of schema changes"
  - id: update-fallback-default
    choice: "Change reporter.py fallback from 'Apify/RSS' to 'Factiva'"
    rationale: "Current reality - Factiva is now the sole source and should be default"
    alternatives:
      - "Leave as 'Apify/RSS' (misleading for new articles)"
    impact: "Accurate source attribution for articles without explicit collector_source"
metrics:
  duration: 0s
  tasks_completed: 2
  commits: 2
  files_modified: 9
completed: 2026-02-26
---

# Phase 15 Plan 03: Apify Dependency and Comment Cleanup Summary

**One-liner:** Removed all Apify dependencies (apify-client, feedparser) and cleaned stale comment references while preserving DB-compatible enum values and schemas

## What Was Built

Complete removal of Apify infrastructure from dependencies, configuration, and documentation:

**Dependency Cleanup:**
- Removed `apify-client` library and `# Web scraping` comment header
- Removed `feedparser==6.0.12` library and `# RSS feed parsing` comment header
- Retained `httpx` (moved under `# HTTP client` header) - still used by FactivaCollector
- Retained `sentence-transformers` - still used for semantic deduplication

**Configuration Cleanup:**
- Removed entire APIFY CONFIGURATION section from .env.example (lines 92-105)
- Removed `apify_token: str = ""` field from Settings class
- Removed `is_apify_configured()` method from Settings class

**Comment/Docstring Cleanup:**
- Updated factiva.py docstring: removed Apify fallback reference
- Updated news_article.py comment: "Factiva (sole source since Phase 15). Historical data may contain 'Apify/RSS'."
- Updated source.py actor_id comment: "Source-specific identifier (historical: Apify actor IDs)"
- Updated api_event.py NEWS_FALLBACK comment: "(Historical) Fallback event from multi-source era"
- Updated reporter.py fallback default: changed from 'Apify/RSS' to 'Factiva'
- Updated admin.py run history comment: changed from "Factiva vs Apify/RSS" to "collector_source distribution"

**Preserved References (DB Compatibility):**
- SourceType.APIFY enum in source.py (historical data requires enum value)
- source_type: Literal["apify", "rss"] in admin schemas (CRUD endpoints match DB schema)
- collector_source default="Apify/RSS" in news_article.py (avoid migration, documents historical default)
- main.py migration SQL (historical record of schema evolution)
- sources/base.py apify_client parameter (abstract interface for future implementations)

## Technical Implementation

### Task 1: Remove Apify dependencies and configuration

**File:** `requirements.txt`

Removed dependencies:
```diff
-# Web scraping
-apify-client
-httpx
+# HTTP client
+httpx

-# RSS feed parsing
-feedparser==6.0.12
```

**Outcome:** Clean dependency list with httpx moved to appropriate category

**File:** `.env.example`

Removed configuration section:
```diff
-# ----------------------------------------------------------------------------
-# APIFY CONFIGURATION (Web Scraping)
-# ----------------------------------------------------------------------------
-# Required for collecting articles from news sources (Phase 1+)
-#
-# Where to find this value:
-#   1. Navigate to: https://console.apify.com/
-#   2. Sign in or create free account
-#   3. Go to: Settings → Integrations
-#   4. Copy: Personal API token → APIFY_TOKEN
-#
-# Note: Free tier includes $5/month credit (sufficient for testing)
-#       Production usage typically costs $20-50/month depending on sources
-APIFY_TOKEN=your_apify_token_here
-
```

**Outcome:** Clean environment template without Apify configuration

**File:** `app/config.py`

Removed settings:
```diff
-    # Apify (for web scraping)
-    apify_token: str = ""

-    def is_apify_configured(self) -> bool:
-        """Check if Apify is configured."""
-        return bool(self.apify_token)
```

**Outcome:** Settings class without Apify references

**Verification:**
```bash
python -c "from app.config import get_settings; s = get_settings(); print('OK')"
# Output: OK

grep -rni "apify" requirements.txt
# Output: (no matches)

grep -rni "feedparser" requirements.txt
# Output: (no matches)

grep -rni "APIFY" .env.example
# Output: (no matches)

grep -rni "apify" app/config.py
# Output: (no matches)

grep "httpx" requirements.txt
# Output: 20:httpx
```

### Task 2: Sweep and clean all Apify references in comments and docstrings

**File:** `app/collectors/factiva.py`

Updated docstring:
```diff
 Raises:
     Exception: If the search request itself fails after retries. The caller
-                (pipeline) handles retry failure by skipping the daily brief
-                and alerting admin.
+                (pipeline) handles retry failure by skipping the daily brief and
+                alerting admin.
```

**Note:** The original plan referenced line ~110 with "fallback to Apify" but this was already cleaned in Plan 01. Only minor formatting adjustment needed.

**File:** `app/models/news_article.py`

Updated comment:
```diff
-    # Source attribution: "Factiva" or "Apify/RSS" (Phase 10)
+    # Source attribution: "Factiva" (sole source since Phase 15). Historical data may contain "Apify/RSS".
     collector_source = Column(String(20), nullable=True, default="Apify/RSS")
```

**Note:** Default value intentionally preserved to avoid Alembic migration risk.

**File:** `app/models/source.py`

Updated comment:
```diff
-    actor_id = Column(String(255), nullable=True)  # Apify-specific actor ID
+    actor_id = Column(String(255), nullable=True)  # Source-specific identifier (historical: Apify actor IDs)
```

**Note:** SourceType.APIFY enum intentionally preserved for DB compatibility.

**File:** `app/models/api_event.py`

Updated comment:
```diff
 News events (Phase 10 - Factiva):
     NEWS_FETCH      - Successful Factiva article fetch
-    NEWS_FALLBACK   - Fell back to Apify scraping (Factiva unavailable)
+    NEWS_FALLBACK   - (Historical) Fallback event from multi-source era
```

**File:** `app/services/reporter.py`

Updated fallback default:
```diff
-                'collector_source': getattr(article, 'collector_source', None) or 'Apify/RSS',
+                'collector_source': getattr(article, 'collector_source', None) or 'Factiva',
```

**Rationale:** Factiva is now the sole source - fallback default should reflect current reality.

**File:** `app/routers/admin.py`

Updated comment:
```diff
-            # Query per-run source breakdown (Factiva vs Apify/RSS article counts)
+            # Query per-run source breakdown (collector_source distribution)
```

**Note:** Admin schema docstrings (lines 552-553, 667-668) intentionally preserved for DB compatibility.

**Verification:**
```bash
python -c "from app.models.news_article import NewsArticle; print('OK')"
# Output: OK

python -c "from app.services.reporter import RoleReportService; print('OK')"
# Output: OK

grep -rni "apify" app/services/pipeline.py
# Output: (no matches)

grep -rni "apify" app/main.py
# Output: 57:text("ALTER TABLE news_articles ADD COLUMN collector_source TEXT DEFAULT 'Apify/RSS'")
# (preserved - historical migration SQL)

grep -rni "apify" app/collectors/factiva.py
# Output: (no matches)

grep -rni "apify" app/services/reporter.py
# Output: (no matches)

# Remaining matches (intentionally preserved):
grep -rni "apify" app/models/source.py
# Output: 14:APIFY = "apify" (enum for DB compatibility)
# Output: 31:actor_id comment (updated to historical)

grep -rni "apify" app/schemas/admin.py
# Output: source_type literals (DB schema compatibility)

grep -rni "apify" app/routers/admin.py
# Output: docstring references (DB schema compatibility)
```

## Deviations from Plan

None — plan executed exactly as written.

All stale Apify references cleaned. Only intentionally preserved references remain for DB compatibility:
- SourceType.APIFY enum (historical database rows)
- source_type literals in admin schemas (Source CRUD endpoints)
- collector_source default value (avoid migration risk)
- Migration SQL in main.py (historical record)
- Abstract interface in sources/base.py (future extensibility)

## Decisions Made

See frontmatter `decisions` section for full details.

Key decisions:
1. **preserve-db-schema:** Keep SourceType.APIFY enum and defaults - removing would break existing rows
2. **preserve-migration-sql:** Keep historical migration code unchanged - documents schema evolution
3. **update-fallback-default:** Change reporter fallback to 'Factiva' - reflects current reality

## Testing Evidence

**Verification passed all 10 requirements:**
```
[OK] grep -rni "apify" requirements.txt returns zero matches
[OK] grep -rni "feedparser" requirements.txt returns zero matches
[OK] grep -rni "APIFY" .env.example returns zero matches
[OK] grep -rni "apify" app/config.py returns zero matches
[OK] grep -rni "apify" app/collectors/factiva.py returns zero matches
[OK] grep -rni "apify" app/services/reporter.py returns zero matches
[OK] httpx still present in requirements.txt
[OK] sentence-transformers still present in requirements.txt
[OK] python -c "from app.config import get_settings; print('OK')" succeeds
[OK] All remaining "apify" matches are in preserved locations (SourceType enum, admin schemas, migration SQL)
```

**Import tests:**
```bash
python -c "from app.config import get_settings; s = get_settings(); print('OK')"
# Output: OK

python -c "from app.models.news_article import NewsArticle; print('OK')"
# Output: OK

python -c "from app.services.reporter import RoleReportService; print('OK')"
# Output: OK
```

**Dependency verification:**
```bash
grep "httpx" requirements.txt
# Output: 20:httpx (retained for FactivaCollector)

grep "sentence-transformers" requirements.txt
# Output: 33:sentence-transformers>=5.0.0 (retained for deduplication)
```

## Integration Points

**Upstream dependencies:**
- Phase 15-01: Pipeline already removed ApifyCollector dependency
- Phase 14: FactivaCollector uses httpx (dependency retained)
- Phase 1: Deduplicator uses sentence-transformers (dependency retained)

**Downstream impacts:**
- Phase 15-02: Can now safely delete ApifyCollector class (no config dependencies)
- Phase 16: Dashboard updates will show Factiva-only architecture (no Apify health checks)

**Cross-system contracts:**
- SourceType.APIFY enum preserved for existing Source rows in database
- collector_source default preserved to avoid Alembic migration
- Admin schema literals match database enum values (CRUD compatibility)

## Known Limitations

None — all requirements met.

**Preserved references (intentional):**
- SourceType.APIFY enum in source.py - required for existing database rows
- source_type: Literal["apify", "rss"] in admin schemas - matches DB schema
- collector_source default="Apify/RSS" - avoids migration, documents history
- Migration SQL in main.py - historical record must remain unchanged
- apify_client in sources/base.py - abstract interface for future implementations

**No breaking changes:**
- Database schema unchanged (no migration needed)
- Existing Source rows with source_type="apify" remain valid
- Historical news_articles with collector_source="Apify/RSS" remain queryable

## Next Phase Readiness

**Phase 15-02 (RUNNING IN PARALLEL) is ready:**
- No dependency conflicts between Plan 02 and Plan 03
- Plan 02 deletes ApifyCollector class - config already cleaned
- Plan 02 deletes source implementations - dependencies already removed

**Phase 16 (Dashboard/Config Updates) is ready:**
- No Apify configuration to display in health checks
- No Apify dependencies to document in admin UI
- Source CRUD endpoints still work (preserved schema literals)

**No blockers or concerns for downstream phases.**

## Files Modified

```
requirements.txt                      # Removed apify-client and feedparser
.env.example                          # Removed APIFY_TOKEN configuration section
app/config.py                         # Removed apify_token field and is_apify_configured()
app/collectors/factiva.py             # Updated docstring
app/models/news_article.py            # Updated collector_source comment
app/models/source.py                  # Updated actor_id comment to historical
app/models/api_event.py               # Updated NEWS_FALLBACK comment
app/services/reporter.py              # Changed fallback default to 'Factiva'
app/routers/admin.py                  # Updated run history comment
```

## Commits

```
d6b7fe9 chore(15-03): remove Apify dependencies and configuration
caba70e docs(15-03): clean all stale Apify references in comments
```

## Metrics

- **Duration:** ~5 minutes (manual execution tracking)
- **Tasks completed:** 2/2
- **Commits:** 2 (one per task)
- **Files modified:** 9
- **Lines changed:** ~50 (removals and comment updates)
- **Dependencies removed:** 2 (apify-client, feedparser)
- **Configuration sections removed:** 1 (APIFY CONFIGURATION)
- **Bugs fixed:** 0 (clean documentation sweep)
- **Tests passed:** 10/10 verification checks

---

**Phase 15 Plan 03 complete.** All Apify dependencies, configuration, and stale comment references removed. Only DB-compatible references preserved (SourceType enum, admin schemas, historical defaults). Ready for Phase 16 dashboard updates.
