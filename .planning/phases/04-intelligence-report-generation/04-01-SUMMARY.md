---
phase: 04-intelligence-report-generation
plan: 01
subsystem: reporter
tags: [reporter, filtering, priority-ranking, schemas, unified-brief]

requires:
  - phase: 03
    reason: "Phase 3 classification fields (entities, impact_level, category, region, business_line)"

provides:
  - capability: "Role-based article filtering with priority ranking"
  - capability: "Unified brief generation (all roles in one HTML)"
  - capability: "Edition statistics tracking"
  - schema: "EditionStats and updated ReportContext for Phase 4"

affects:
  - phase: 04
    plans: ["02", "03", "04", "05", "06"]
    reason: "Foundation for all Phase 4 plans - provides filtering/sorting and schema structure"

tech-stack:
  added: []
  patterns:
    - "Static method for stateless filtering/sorting logic"
    - "Edition statistics computed from article collection"
    - "Pydantic schemas with Optional fields for progressive enhancement"

key-files:
  created: []
  modified:
    - path: "app/schemas/report.py"
      loc: 99
      description: "Added EditionStats schema and updated ReportContext for unified brief"
    - path: "app/services/reporter.py"
      loc: 186
      description: "Added role filtering, priority ranking, and updated reporter signature"
    - path: "app/services/pipeline.py"
      loc: 216
      description: "Updated pipeline to call reporter with new signature (no target_role)"

decisions:
  - what: "Use static method for filter_articles_by_role"
    why: "Stateless filtering logic that doesn't depend on instance state"
    alternatives: ["Instance method", "Standalone function"]
    chosen: "Static method for discoverability and namespacing"

  - what: "Compute edition_stats in generate_role_brief"
    why: "Reporter service has access to all articles, can compute stats efficiently"
    alternatives: ["Compute in pipeline", "Separate stats service"]
    chosen: "Reporter service owns stats computation for the brief"

  - what: "Remove target_role parameter from generate_role_brief"
    why: "Unified brief contains all roles via tabs, no need to specify target"
    alternatives: ["Keep parameter for backwards compatibility", "Add unified_mode flag"]
    chosen: "Remove parameter - simplifies API and matches Phase 4 unified brief design"

metrics:
  duration: "4 minutes"
  completed: "2026-02-07"
  commits: 2
  files_changed: 3
  tests_added: 0
  tests_passing: true
---

# Phase 04 Plan 01: Role Filtering and Priority Ranking Summary

**One-liner:** Implemented role-based article filtering with priority ranking (Critical→Monitor) and updated reporter signature for unified brief generation with edition stats tracking.

## What Was Done

### Task 1: Add Pydantic Schemas for Report Generation
- Created `EditionStats` schema with `source_count`, `article_count`, `entity_count`, `signal_count` fields
- Updated `ReportContext` schema:
  - Removed `target_role` field (unified brief, not per-role)
  - Changed `articles` to `List[dict]` (prepared dicts, not ORM objects)
  - Added optional fields for Phase 4 components: `executive_summaries`, `sector_heatmap`, `entity_tracker`, `what_to_watch`, `market_pulse`

**Commit:** `1ed0c5a` - feat(04-01): add EditionStats schema and update ReportContext for Phase 4

### Task 2: Implement Role Filtering, Priority Ranking, and Updated Reporter Signature
- Added `PRIORITY_ORDER` module-level dict: `{"Critical": 0, "High": 1, "Medium": 2, "Monitor": 3}`
- Implemented `filter_articles_by_role(articles, role)` static method:
  - Filters articles where `role in article['roles']`
  - Sorts by priority using PRIORITY_ORDER (unknown priorities get value 4)
- Updated `_prepare_articles` to include all 14 Phase 3 fields:
  - Added: `entities` (parsed from JSON), `impact_level`, `category`, `region`, `business_line`
  - Kept existing: `id`, `title`, `description`, `source_url`, `source_name`, `published_at`, `roles`, `priority`, `summary`, `sentiment`
- Changed `generate_role_brief` signature:
  - Removed `target_role` parameter
  - Computes `edition_stats` from articles (source_count, article_count)
  - Builds context dict with prepared articles and edition_stats
- Updated `generate_all_role_briefs` to return single HTML string (unified brief)
- Updated `pipeline.py` to call reporter with new signature (removed `role` parameter)

**Commit:** `8948b60` - feat(04-01): implement role filtering, priority ranking, and unified brief signature

## Technical Implementation

### Role Filtering and Priority Ranking
```python
# Priority order for sorting
PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Monitor": 3}

@staticmethod
def filter_articles_by_role(articles: List[dict], role: str) -> List[dict]:
    # Filter by role membership
    role_articles = [a for a in articles if role in a.get('roles', [])]
    # Sort by priority (Critical first, Monitor last)
    role_articles.sort(key=lambda a: PRIORITY_ORDER.get(a.get('priority'), 4))
    return role_articles
```

### Edition Statistics
```python
# Compute edition stats from article collection
source_count = len(set(a.source_name for a in articles if a.source_name))
article_count = len(articles)

edition_stats = {
    'source_count': source_count,
    'article_count': article_count,
    'entity_count': 0,  # Filled later by aggregator (Plan 04)
    'signal_count': 0   # Filled later by what-to-watch (Plan 05)
}
```

### Article Preparation (All 14 Fields)
```python
article_dict = {
    # Phase 1 fields
    'id': article.id,
    'title': article.title,
    'description': article.description,
    'source_url': article.source_url,
    'source_name': article.source_name,
    'published_at': article.published_at,
    'roles': json.loads(article.roles) if article.roles else [],
    'priority': article.priority,
    'summary': article.summary,
    'sentiment': article.sentiment,
    # Phase 3 fields
    'entities': json.loads(article.entities) if isinstance(article.entities, str) else article.entities or [],
    'impact_level': article.impact_level,
    'category': article.category,
    'region': article.region,
    'business_line': article.business_line,
}
```

## Verification Results

1. ✅ `EditionStats` and `ReportContext` schemas importable without error
2. ✅ `RoleReportService`, `PRIORITY_ORDER` import successfully
3. ✅ `PipelineOrchestrator` imports without error
4. ✅ `filter_articles_by_role` correctly filters and sorts articles by priority:
   - Test input: 3 Brokers articles (Medium, Critical, Monitor)
   - Expected output: [Critical, Medium, Monitor]
   - Actual output: [Critical, Medium, Monitor] ✅

## Success Criteria Met

- ✅ EditionStats schema exists with source_count, article_count fields
- ✅ ReportContext updated with optional fields for Phase 4 components
- ✅ Reporter filters articles by role and sorts by priority
- ✅ _prepare_articles includes all 14 article fields (Phase 1 + Phase 3)
- ✅ Pipeline calls reporter with new signature (no target_role)
- ✅ No regressions in existing imports

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Phase 4 Plan 02 (Executive Summaries) is ready:**
- ✅ Reporter service has filter_articles_by_role for role-specific summaries
- ✅ EditionStats schema in place for summary metadata
- ✅ ReportContext has executive_summaries field ready for AI-generated summaries
- ✅ All Phase 3 classification fields available for summary generation

**Phase 4 Plans 03-06 are ready:**
- ✅ Foundation filtering/sorting logic in place
- ✅ Schema structure extensible via optional fields
- ✅ Edition stats tracking mechanism established

**Blockers:** None

**Dependencies:** Phase 4 Plan 02 requires Azure OpenAI client integration (not added yet, per plan instructions)

## Files Modified

| File | Changes | LOC |
|------|---------|-----|
| app/schemas/report.py | Added EditionStats, updated ReportContext | 99 |
| app/services/reporter.py | Added filtering/sorting, updated signature, edition stats | 186 |
| app/services/pipeline.py | Updated reporter call to match new signature | 216 |

## Commits

| Hash | Message |
|------|---------|
| 1ed0c5a | feat(04-01): add EditionStats schema and update ReportContext for Phase 4 |
| 8948b60 | feat(04-01): implement role filtering, priority ranking, and unified brief signature |
