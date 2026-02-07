---
phase: 03-advanced-classification-pipeline
plan: 02
subsystem: classification
tags: [azure-openai, gpt-4o, structured-outputs, entity-extraction, classification]
requires: ["03-01-data-layer-expansion"]
provides: ["enhanced-classifier-prompt", "phase-3-field-storage"]
affects: ["03-03-classification-testing", "04-01-report-template-update"]
tech-stack:
  added: []
  patterns: ["comprehensive-prompt-design", "pydantic-v2-model-dump", "multi-dimensional-classification"]
key-files:
  created: []
  modified: ["app/services/classifier.py"]
decisions:
  - decision: "Expanded CLASSIFICATION_PROMPT with 5 new guidance sections"
    rationale: "Single comprehensive prompt delivers all 9 classification dimensions in one GPT-4o call"
    alternatives: ["Multi-pass classification (5 separate calls)", "Separate prompts per dimension"]
    impact: "Efficient single-call classification, consistent cross-dimensional analysis"
  - decision: "Use model_dump() for entities serialization"
    rationale: "Pydantic v2 compatibility - dict() deprecated in v2"
    alternatives: ["Use deprecated dict() method"]
    impact: "Future-proof Pydantic v2 compatibility"
  - decision: "Log impact_level, category, entity_count in classify_article"
    rationale: "Enable real-time monitoring of Phase 3 classification quality"
    alternatives: ["Minimal logging", "Full classification logging"]
    impact: "Balanced observability without verbose logs"
metrics:
  duration: "1.7 minutes"
  completed: "2026-02-07"
---

# Phase 3 Plan 02: Classifier Prompt Expansion Summary

Expanded classifier service prompt and field storage for Phase 3 multi-dimensional classification.

**One-liner:** Comprehensive 9-dimension classification prompt with entity extraction, impact assessment, and categorical tagging in single GPT-4o call.

## What Was Accomplished

### Core Deliverables

**1. Expanded CLASSIFICATION_PROMPT (5379 chars)**

Added 5 new guidance sections to existing working prompt:
- **Entity Extraction Guidelines**: Extract 3-10 relevant entities (companies, people, organizations) with type and context
- **Impact Level Assessment**: Market magnitude independent of Marsh urgency (Critical/High/Medium/Low)
- **Category Assignment**: Primary theme classification (M&A, Regulatory, Loss Event, Financial Results, Market Trends, Product Launch, Executive Change, Other)
- **Region Assignment**: Primary geographic focus (North America, Europe, Asia Pacific, Latin America, Middle East & Africa, Global)
- **Business Line Assignment**: Primary insurance segment (Property, Casualty, Life & Health, Reinsurance, Specialty, Multiple Lines, Other)

**2. Phase 3 Field Storage in classify_articles**

Updated field storage to persist all new dimensions:
```python
article.entities = json.dumps([e.model_dump() for e in classification.entities])
article.impact_level = classification.impact_level
article.category = classification.category
article.region = classification.region
article.business_line = classification.business_line
```

**3. Enhanced Logging**

Added impact_level, category, entity_count to classify_article logging for real-time quality monitoring.

### Key Technical Patterns

**Comprehensive Prompt Design**
- Appended new sections after existing working content
- Preserved proven role definitions, multi-role guidance, priority/sentiment sections
- Clear examples and decision criteria for each new dimension
- Single coherent prompt delivering 9 dimensions in one API call

**Pydantic v2 Compatibility**
- Used model_dump() for entities serialization (Pydantic v2 method)
- Avoided deprecated dict() method from Pydantic v1
- Future-proof serialization pattern for all Pydantic models

**Conservative Field Storage**
- Entities stored as JSON array of {name, type, context} objects
- Other fields stored as simple strings matching Literal types
- Backward compatible with existing Phase 1/2 articles (nullable columns)

## Deviations from Plan

None - plan executed exactly as written. All tasks completed without modifications.

## Testing Notes

**Verification Performed:**
1. ✅ Import verification - no syntax errors
2. ✅ Prompt sections present - all 5 new sections confirmed
3. ✅ Field storage verification - all 5 fields stored with model_dump()
4. ✅ Prompt length verification - 5379 chars (reasonable for GPT-4o context)

**Production Testing Required (03-03):**
- End-to-end classification with real articles
- Verify structured outputs populate all new fields
- Validate entity extraction quality and relevance
- Assess category/region/business line classification accuracy
- Confirm impact_level vs priority distinction is clear to model

## Architecture Impact

**Modified Components:**
- `app/services/classifier.py`: Expanded prompt + field storage

**Dependencies Updated:**
- None (uses existing ArticleClassification schema from 03-01)

**Integration Points:**
- Pipeline orchestrator: No changes required (same classify_articles signature)
- Report template: Will consume new fields in Plan 03-03
- Article model: Already updated in 03-01 with new columns

## Known Issues / Tech Debt

**None identified.**

All changes follow established patterns:
- Prompt expansion maintains existing structure
- Field storage uses proven JSON serialization pattern
- Error handling preserved (skip-on-error, batch commits)
- Logging follows existing structlog patterns

## Next Phase Readiness

**Blockers for Phase 4:** None

**Phase 3 Completion Status:**
- Plan 01: ✅ Data layer expansion complete
- Plan 02: ✅ Classifier prompt expansion complete
- Plan 03: ⏳ Classification testing (next)
- Plan 04: ⏳ Impact assessment validation
- Plan 05: ⏳ Category filtering integration

**Ready for 03-03:** Yes - classifier now generates all Phase 3 fields, ready for production testing and quality validation.

## Performance Notes

**Execution Metrics:**
- Total duration: 1.7 minutes
- Tasks completed: 2/2
- Commits: 2 atomic commits

**Resource Usage:**
- Prompt expansion: +2824 chars to CLASSIFICATION_PROMPT
- Code changes: +61 lines (11 field storage, 50 prompt guidance)
- Zero breaking changes to existing API contracts

**Production Considerations:**
- Single GPT-4o call per article (no increase from Phase 1/2)
- Slightly longer prompt (5379 vs 2555 chars) - minimal token impact
- Entity extraction adds variable-length output (3-10 entities per article)
- Estimated token increase: ~200-500 tokens per classification call

## Commits

- `0f06899`: feat(03-02): expand CLASSIFICATION_PROMPT with Phase 3 guidance
- `d57f5d0`: feat(03-02): store Phase 3 classification fields in NewsArticle

## Files Modified

**app/services/classifier.py**: Expanded CLASSIFICATION_PROMPT with 5 new guidance sections, updated classify_articles to store entities (JSON), impact_level, category, region, business_line, enhanced logging with impact_level/category/entity_count.
