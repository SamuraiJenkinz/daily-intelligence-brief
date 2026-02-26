---
phase: 14-factivacollector-port
plan: 01
subsystem: data-collection
tags: [factiva, database, migration, orm, configuration]
requires: [10-factiva-news-collection]
provides: [date_range_hours-column, phase14-foundation]
affects: [14-02-port-collector]
decisions:
  - "default-date-range-48h"
  - "preserve-existing-config"
  - "corrected-seed-data-i82"
tech-stack:
  added: []
  patterns: [startup-migration, backward-compatible-schema]
key-files:
  created: []
  modified:
    - app/models/factiva_config.py
    - app/main.py
metrics:
  duration: "3m 8s"
  completed: 2026-02-26
---

# Phase 14 Plan 01: Add date_range_hours Column Summary

**One-liner:** Added date_range_hours Integer column (default 48h) to FactivaConfig with idempotent startup migration and corrected seed data.

**What was delivered:**

1. FactivaConfig model extended with date_range_hours column (Integer, NOT NULL, default 48)
2. Startup migration that adds the column to existing factiva_config tables without data loss
3. Corrected seed data: i82 industry code (not i82,i832) and comma-separated keywords (insurance,reinsurance)
4. Updated model docstrings, class documentation, and __repr__ method

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add date_range_hours column to FactivaConfig model | bb2b311 | app/models/factiva_config.py |
| 2 | Update startup migration and seed data in main.py | 85664f3 | app/main.py |

**Total commits:** 2 (atomic per-task commits)

## Decisions Made

### default-date-range-48h
**Context:** BrasilIntel FactivaCollector uses configurable date_range_hours (default 48h) vs. MDInsights' fixed 24h window.

**Decision:** Use 48-hour default to match BrasilIntel's proven approach.

**Rationale:**
- BrasilIntel's 48h window has been validated in production for Brazilian insurer intelligence
- Longer lookback reduces risk of missing articles during weekend/holiday gaps
- Admin-configurable via factiva_config table, so can be adjusted per deployment

**Alternatives considered:**
- 24h (current MDInsights approach) — rejected as too narrow for weekend coverage
- 72h — rejected as potentially redundant with daily collection schedule

**Impact:** Plan 14-02 collector will use this value for date range calculations

### preserve-existing-config
**Context:** Existing deployments may have admin-customized industry_codes and keywords in factiva_config table.

**Decision:** Migration adds column but preserves existing row data. Seed INSERT corrections only apply to fresh databases.

**Rationale:**
- Respects production admin configuration decisions
- Avoids overwriting validated production settings with research-based defaults
- Backward compatible with Phase 10 deployments

**Implementation:**
- ALTER TABLE with DEFAULT 48 gives existing rows the new column
- Seed INSERT uses corrected values (i82, insurance,reinsurance) for new installations
- Migration is idempotent (safe to run multiple times)

**Impact:** Existing deployments retain their admin-configured values; fresh installs get corrected defaults

### corrected-seed-data-i82
**Context:** Phase 14 research found i82 is validated Dow Jones industry code for insurance; i832 is unvalidated (open question 2).

**Decision:** Seed data uses 'i82' only (not 'i82,i832').

**Rationale:**
- i82 is validated in Dow Jones taxonomy documentation
- i832 is inferred but not confirmed — better to use validated codes only
- Admin can add i832 later if validation confirms it's useful

**Evidence:** Phase 14 research document (RESEARCH.md open question 2)

**Impact:** Fresh databases target validated insurance industry code; existing databases unchanged

## Technical Implementation

### Model Changes (app/models/factiva_config.py)

**Added column:**
```python
date_range_hours = Column(
    Integer,
    nullable=False,
    default=48,
    comment="Lookback window in hours for Factiva search date range (default 48)"
)
```

**Documentation updates:**
- Module docstring: "Created in Phase 10" → "Created in Phase 10, extended in Phase 14"
- Class docstring: Added date_range_hours to admin-configurable fields list
- __repr__ method: Includes date_range_hours in output

### Migration Logic (app/main.py)

**Column migration:**
```python
# Phase 14: add date_range_hours column to factiva_config
result = session.execute(text("PRAGMA table_info(factiva_config)"))
fc_columns = [row[1] for row in result.fetchall()]
if "date_range_hours" not in fc_columns:
    session.execute(
        text("ALTER TABLE factiva_config ADD COLUMN date_range_hours INTEGER DEFAULT 48 NOT NULL")
    )
    session.commit()
    logger.info("startup_migration: added date_range_hours column to factiva_config")
else:
    logger.info("startup_migration: date_range_hours column already exists")
```

**Seed data correction:**
```python
session.execute(text(
    "INSERT OR IGNORE INTO factiva_config "
    "(id, industry_codes, company_codes, keywords, page_size, date_range_hours, enabled) "
    "VALUES (1, 'i82', 'MM', 'insurance,reinsurance', 25, 48, 1)"
))
```

**Key properties:**
- Idempotent: Uses PRAGMA table_info check before ALTER TABLE
- Backward compatible: DEFAULT 48 gives existing rows the new column
- Data preserving: Existing row id=1 keeps admin-configured values
- Non-blocking: Migration failure logged but doesn't prevent startup

## Verification Results

All verification checks passed:

1. ✅ FactivaConfig model imports without error
2. ✅ date_range_hours column exists in model (Integer, NOT NULL, default 48)
3. ✅ Startup migration adds column to existing databases
4. ✅ Seed data uses 'i82' industry code (verified in main.py)
5. ✅ Seed data uses 'insurance,reinsurance' comma-separated keywords (verified in main.py)
6. ✅ Existing factiva_config rows preserved (1 row exists with date_range_hours=48)

**Manual testing:**
- Migration ran successfully on existing database
- Existing row received date_range_hours=48 via ALTER TABLE DEFAULT
- Migration is idempotent (second run logs "column already exists")
- Model imports and column definitions are correct

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**For Plan 14-02 (Port FactivaCollector):**
- ✅ date_range_hours column exists in model and database
- ✅ Default value (48h) available for collector to read
- ✅ Seed data corrected for fresh installations
- ✅ Migration is production-safe (idempotent, backward-compatible)

**Blockers:** None

**Dependencies satisfied:**
- FactivaConfig model ready with date_range_hours column
- Startup migration ensures column exists on app startup
- Collector can read `config.date_range_hours` in Plan 14-02

## Files Modified

### app/models/factiva_config.py
- Added date_range_hours Integer column (nullable=False, default=48)
- Updated module docstring: Phase 10 → Phase 10/14
- Updated class docstring: added date_range_hours to admin fields
- Updated __repr__ to include date_range_hours

### app/main.py
- Renamed startup migration comment: Phase 10 → Phase 10/14
- Added date_range_hours column migration (idempotent, before seed INSERT)
- Updated seed INSERT: added date_range_hours=48
- Corrected seed INSERT: i82 industry code (not i82,i832)
- Corrected seed INSERT: comma-separated keywords (insurance,reinsurance)

## Quality Metrics

**Code Quality:**
- All changes follow existing patterns (startup migration, ORM column definitions)
- Documentation updated comprehensively (module, class, method docstrings)
- Type hints maintained (Integer for date_range_hours)

**Migration Safety:**
- Idempotent: Safe to run multiple times
- Backward compatible: Existing data preserved
- Non-destructive: ALTER TABLE with DEFAULT (no data loss)
- Non-blocking: Migration failure doesn't prevent app startup

**Test Coverage:**
- Manual verification script confirms:
  - Column exists in model
  - Column exists in database
  - Default value applied to existing rows
  - Migration is idempotent
  - Seed data corrected

## Lessons Learned

**What went well:**
- Atomic per-task commits provide clear rollback points
- Idempotent migration pattern from Phase 10 easily extended for Phase 14
- Research-driven seed data corrections improve production readiness

**Process observations:**
- Startup migration approach (vs. Alembic) trades schema versioning for simplicity
- PRAGMA table_info check pattern is reliable for SQLite column detection
- ALTER TABLE DEFAULT clause cleanly handles existing rows

**Future considerations:**
- As schema grows, consider Alembic for more complex migrations
- Document validated vs. inferred industry codes in admin UI tooltips
- Track seed data provenance (research findings) in model docstrings
