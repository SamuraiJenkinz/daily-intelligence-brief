---
phase: 03
plan: 01
subsystem: data-layer
tags: [database, orm, schema, migration, sqlalchemy, pydantic]
requires: [02-06]
provides: [phase-3-data-foundation, entity-extraction-schema, categorical-classification]
affects: [03-02, 03-03, 03-04]
tech-stack:
  added: []
  patterns: [sqlalchemy-2.0-connections, nullable-columns-for-backward-compatibility]
key-files:
  created:
    - scripts/migrate_003_classification_fields.py
  modified:
    - app/models/news_article.py
    - app/schemas/classification.py
decisions:
  - id: phase-3-nullable-fields
    choice: All Phase 3 classification fields are nullable
    rationale: Backward compatibility with existing Phase 1/2 articles
  - id: impact-vs-priority-distinction
    choice: Separate impact_level (market magnitude) from priority (Marsh urgency)
    rationale: Different dimensions - systemic impact vs operational urgency
  - id: sqlalchemy-2.0-connection-pattern
    choice: Use "with engine.connect() as conn" instead of engine.execute()
    rationale: SQLAlchemy 2.0 removed engine.execute() method
  - id: entity-extraction-structure
    choice: JSON array in entities column with {name, type, context} objects
    rationale: Flexible storage for variable-length entity lists, queryable with JSON functions
  - id: categorical-literal-types
    choice: Strict Literal types for impact_level, category, region, business_line
    rationale: Azure OpenAI structured outputs require enum-like constraints
metrics:
  duration: 2.5 minutes
  tasks: 2
  commits: 2
  files: 3
completed: 2026-02-07
---

# Phase 3 Plan 01: Data Layer Expansion Summary

Phase 3 data foundation: database migration, ORM model, and Pydantic schema expansion for advanced classification with entity extraction and categorical types.

## Objective Achieved

Expanded the data layer for Phase 3 advanced classification by adding 5 new columns to the database (entities, impact_level, category, region, business_line), updating the NewsArticle ORM model, and expanding the ArticleClassification Pydantic schema with ExtractedEntity model and Literal type constraints.

The existing classifier (Phase 1) only stores roles, priority, summary, and sentiment. Phase 3 requires storing:
- **Entities**: Companies, people, and organizations mentioned in articles
- **Impact Level**: Market magnitude (Critical/High/Medium/Low) - distinct from priority urgency
- **Category**: Article classification (M&A/Regulatory/Loss Event/etc.)
- **Region**: Geographic scope (North America/Europe/Asia Pacific/etc.)
- **Business Line**: Insurance segment (Property/Casualty/Life & Health/etc.)

This plan creates the foundation that the classifier update (Plan 02) will write into.

## Tasks Completed

### Task 1: Database migration script and ORM model expansion
**Duration:** ~1 minute | **Commit:** 7ae1d2f

Created `scripts/migrate_003_classification_fields.py` with idempotent ALTER TABLE statements for 5 new nullable columns:
- `entities` (TEXT): JSON array of {name, type, context} objects
- `impact_level` (VARCHAR(20)): Critical/High/Medium/Low
- `category` (VARCHAR(50)): M&A/Regulatory/Loss Event/etc.
- `region` (VARCHAR(50)): North America/Europe/Asia Pacific/etc.
- `business_line` (VARCHAR(50)): Property/Casualty/Life & Health/etc.

Updated `app/models/news_article.py` NewsArticle ORM class with Phase 3 fields, all nullable for backward compatibility with existing articles.

**Key Pattern:** Migration uses SQLAlchemy 2.0 `with engine.connect() as conn` pattern instead of deprecated `engine.execute()` method. Each ALTER TABLE wrapped in try/except for idempotent execution (handles "duplicate column name" gracefully).

**Verification:**
```bash
python scripts/migrate_003_classification_fields.py  # All columns added
python -c "from app.models.news_article import NewsArticle; print([c.name for c in NewsArticle.__table__.columns])"
# Output: ['id', 'run_id', 'title', 'description', 'source_url', 'source_name', 'published_at',
#          'roles', 'priority', 'summary', 'sentiment',
#          'entities', 'impact_level', 'category', 'region', 'business_line', 'created_at']
```

### Task 2: Expand Pydantic classification schema with entity extraction and categorical types
**Duration:** ~1 minute | **Commit:** eafbea3

Expanded `app/schemas/classification.py` with Phase 3 types and fields while preserving all existing structure:

**New Types:**
- `ExtractedEntity` Pydantic model: name (str), type (Literal["company", "person", "organization"]), context (str)
- `ImpactLevelType = Literal["Critical", "High", "Medium", "Low"]`
- `CategoryType = Literal["M&A", "Regulatory", "Loss Event", "Financial Results", "Market Trends", "Product Launch", "Executive Change", "Other"]`
- `RegionType = Literal["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa", "Global"]`
- `BusinessLineType = Literal["Property", "Casualty", "Life & Health", "Reinsurance", "Specialty", "Multiple Lines", "Other"]`

**New Fields in ArticleClassification:**
- `entities: List[ExtractedEntity]` - 3-10 most relevant entities with default_factory=list
- `impact_level: ImpactLevelType` - Market impact magnitude
- `category: CategoryType` - Primary article theme
- `region: RegionType` - Geographic scope
- `business_line: BusinessLineType` - Insurance segment affected

**Field Descriptions:** All fields include detailed descriptions for Azure OpenAI structured output guidance (e.g., "Market impact: Critical ($1B+/systemic), High ($100M-$1B), Medium ($10M-$100M), Low (<$10M/routine)").

**Verification:**
```bash
python -c "from app.schemas.classification import ArticleClassification, ExtractedEntity; schema = ArticleClassification.model_json_schema(); print(sorted(schema['properties'].keys()))"
# Output: ['business_line', 'category', 'entities', 'impact_level', 'priority', 'region', 'roles', 'sentiment', 'summary']

python -c "from app.schemas.classification import ArticleClassification; a = ArticleClassification(roles=['Brokers'], priority='High', summary='test', sentiment='neutral', entities=[], impact_level='Medium', category='Other', region='Global', business_line='Other'); print(a.model_dump())"
# Output: Validation OK with all 9 fields
```

## Implementation Details

### Database Schema
```sql
-- Migration adds 5 nullable columns to news_articles table
ALTER TABLE news_articles ADD COLUMN entities TEXT;
ALTER TABLE news_articles ADD COLUMN impact_level VARCHAR(20);
ALTER TABLE news_articles ADD COLUMN category VARCHAR(50);
ALTER TABLE news_articles ADD COLUMN region VARCHAR(50);
ALTER TABLE news_articles ADD COLUMN business_line VARCHAR(50);
```

### Entity Extraction Schema
```python
class ExtractedEntity(BaseModel):
    name: str  # Normalized official form (e.g., "Marsh McLennan" not "Marsh")
    type: Literal["company", "person", "organization"]
    context: str  # Brief role in article (1 sentence)

# Example entity JSON stored in database:
# [
#   {"name": "Marsh McLennan", "type": "company", "context": "Major broker adapting to new compliance rules"},
#   {"name": "SEC", "type": "organization", "context": "Regulatory body issuing new guidance"}
# ]
```

### Impact Level vs Priority Distinction
**Important Architectural Decision:**

- **priority** (Phase 1): Urgency for Marsh - how quickly they need to act (Critical/High/Medium/Monitor)
- **impact_level** (Phase 3): Market magnitude - financial/systemic impact scale (Critical/High/Medium/Low)

These are intentionally separate dimensions. A routine M&A announcement might have Low priority (Monitor) but High impact_level ($500M deal). A compliance deadline might have Critical priority but Medium impact_level.

## Decisions Made

### 1. All Phase 3 fields nullable for backward compatibility
**Context:** Existing Phase 1/2 articles in database have NULL values for new fields.

**Decision:** All 5 new columns created with `nullable=True` in both migration and ORM model.

**Impact:** Existing articles load without validation errors. Classifier update (Plan 02) will populate these fields going forward.

### 2. Separate impact_level from priority
**Context:** Phase 1 priority field represents Marsh operational urgency.

**Decision:** Add new impact_level field for market magnitude, keep priority unchanged.

**Rationale:** Different dimensions - systemic impact vs operational urgency. Examples:
- Routine M&A: Low priority, High impact ($500M deal)
- Compliance deadline: Critical priority, Medium impact

**Impact:** More nuanced classification enables better filtering and prioritization.

### 3. SQLAlchemy 2.0 connection pattern
**Context:** Project uses SQLAlchemy 2.0, which removed `engine.execute()` method.

**Decision:** Use `with engine.connect() as conn: conn.execute(text(...)); conn.commit()` pattern.

**Impact:** Migration script compatible with SQLAlchemy 2.0, each ALTER TABLE wrapped in try/except for idempotent execution.

### 4. JSON array for entity storage
**Context:** Articles can mention variable number of entities (3-10 per article).

**Decision:** Store entities as JSON TEXT column with array of {name, type, context} objects.

**Alternatives Considered:**
- Separate entities table with M2M relationship: More normalized but adds complexity
- Fixed number of entity columns: Inflexible, wastes space

**Rationale:** Simple for Phase 3 MVP, queryable with SQLite JSON functions if needed, can migrate to normalized table later if query patterns require.

**Impact:** Flexible storage, minimal schema complexity, adequate for current scale (20 sources × 20 articles/day = 400 articles/day).

### 5. Strict Literal types for categorical fields
**Context:** Azure OpenAI structured outputs require schema constraints for reliable classification.

**Decision:** Define Literal types with fixed enum values for impact_level, category, region, business_line.

**Rationale:** Ensures consistent classification output from AI, enables reliable filtering in UI, prevents typos/variations.

**Impact:** ArticleClassification schema enforces valid values, Azure OpenAI must choose from provided options.

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All verification checks passed:

1. Migration script runs idempotently (safe to run multiple times)
2. NewsArticle ORM model has all 5 Phase 3 columns
3. ArticleClassification Pydantic schema has entities, impact_level, category, region, business_line fields
4. ArticleClassification validates with all 9 fields (4 existing + 5 new)
5. ExtractedEntity model properly nested in schema definition

## Next Phase Readiness

**Unblocks:**
- Plan 02: Classifier update can now write Phase 3 fields to database
- Plan 03: Entity extraction service can populate entities field
- Plan 04: Categorical filtering UI can query new fields

**Dependencies for Next Plans:**
- Plan 02 requires Azure OpenAI structured output update to populate new fields
- Plan 03 requires entity extraction prompt engineering and validation
- Plan 04 requires reporter template updates to render entities and categorical filters

**Concerns:**
- Entity normalization strategy not yet defined (e.g., "Marsh" vs "Marsh McLennan" vs "MMC")
- Category taxonomy may need refinement based on real article distribution
- Region/business_line assignment logic for multi-region/multi-line stories needs clarification

## Performance Notes

- **Execution Time:** 2.5 minutes (1 min Task 1, 1 min Task 2, 0.5 min verification)
- **Migration Performance:** Instant for SQLite ALTER TABLE (no data type conversions)
- **Schema Validation:** No performance impact (Pydantic validation at API boundary only)

## Files Modified

**Created:**
- `scripts/migrate_003_classification_fields.py` (64 lines) - Database migration for Phase 3 columns

**Modified:**
- `app/models/news_article.py` (+5 columns, docstring update) - ORM model expansion
- `app/schemas/classification.py` (+50 lines) - Pydantic schema expansion with ExtractedEntity and 5 new fields

## Technical Debt

None introduced. Clean migration pattern established for future schema expansions.

## Lessons Learned

1. **Windows console Unicode issue:** Migration script initially used Unicode checkmarks/crosses that failed on Windows console (cp1252 encoding). Fixed with ASCII `[OK]`/`[ERROR]` markers.

2. **SQLAlchemy 2.0 pattern:** Confirmed project uses SQLAlchemy 2.0 - migration pattern documented for future schema changes.

3. **Nullable columns essential:** Backward compatibility with existing articles critical - all Phase 3 fields must be nullable.

4. **Pydantic default_factory:** `entities` field uses `default_factory=list` to avoid mutable default argument issues.

## Related Documentation

- Plan: `.planning/phases/03-advanced-classification-pipeline/03-01-PLAN.md`
- Database: `data/mdinsights.db` (SQLite)
- Migration Pattern: `scripts/migrate_003_classification_fields.py`
- ORM Reference: `app/models/news_article.py`
- Schema Reference: `app/schemas/classification.py`
