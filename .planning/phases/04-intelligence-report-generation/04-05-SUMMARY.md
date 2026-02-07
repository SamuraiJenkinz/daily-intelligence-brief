# Phase 04 Plan 05: What to Watch Forward-Looking Analysis Summary

## One-Liner
AI-generated forward-looking analysis with 4-6 actionable items, timeframes, and impact roles

## Overview

**Phase:** 04-intelligence-report-generation
**Plan:** 05
**Status:** ✅ COMPLETE
**Duration:** 1.5 minutes
**Wave:** 2 (autonomous)
**Dependencies:** 04-01 (role filtering, edition stats, reporter foundation)

## What Was Built

### WhatToWatch Pydantic Schemas
- **WhatToWatchItem**: Single forward-looking item with title, description, timeframe, impact_roles
- **WhatToWatch**: Container with list of 4-6 items
- Schema enforces structured AI output for consistency

### _generate_what_to_watch Method
- **Filtering logic**: Critical/High priority OR Market Trends category
- **AI prompt**: Strategic intelligence analyst identifying market signals
- **Focus areas**: M&A timelines, regulatory deadlines, renewal cycles, emerging risks
- **Structured output**: Azure OpenAI beta.chat.completions.parse with WhatToWatch schema
- **Temperature**: 0.5 (balance consistency with creativity)
- **Context**: Top 15 relevant articles with category and region metadata

### Graceful Degradation
1. **Empty articles**: Returns WhatToWatch(items=[])
2. **Unconfigured Azure OpenAI**: Returns empty fallback
3. **Generation error**: Logs warning, returns empty fallback
4. Template rendering works with empty items list

### Integration
- Method called in generate_role_brief after executive summaries
- WhatToWatch converted to dict via model_dump()
- Passed to template context as 'what_to_watch' key
- Template rendering deferred to Plan 07

## Technical Implementation

### Files Modified
- `app/schemas/report.py`: Added WhatToWatchItem and WhatToWatch schemas
- `app/services/reporter.py`: Added _generate_what_to_watch method, wired into generate_role_brief

### Key Patterns
- **Import update**: Added WhatToWatch to reporter imports
- **Article filtering**: Dual criteria (priority OR category)
- **Prompt engineering**: Specific focus areas with WHEN and WHO requirements
- **Error handling**: Try/except with fallback to empty items
- **Template context**: what_to_watch_dict passed alongside executive_summaries_dict

## Commits

| Task | Commit | Message | Files |
|------|--------|---------|-------|
| 1 | be9ab96 | feat(04-05): add What to Watch forward-looking analysis | app/schemas/report.py, app/services/reporter.py |

## Success Criteria Met

- ✅ WhatToWatchItem has title, description, timeframe, impact_roles fields
- ✅ WhatToWatch has items list with default_factory
- ✅ _generate_what_to_watch filters to Critical/High/Market Trends articles
- ✅ Graceful fallback for empty articles or unconfigured AI
- ✅ What to watch data passed to template context as dict
- ✅ Verification: Schema import OK, method produces empty fallback

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

```bash
# Schema verification
python -c "from app.schemas.report import WhatToWatch, WhatToWatchItem; w = WhatToWatch(items=[]); print('Schema OK')"
# Output: Schema OK

# Method verification (empty articles, unconfigured Azure)
python -c "from app.services.reporter import RoleReportService; r = RoleReportService(); w = r._generate_what_to_watch([], None); print('Items:', len(w.items))"
# Output: azure_openai_not_configured_for_what_to_watch warning, Items: 0
```

## Next Phase Readiness

**Blockers:** None

**Dependencies Satisfied:**
- Plan 04-06: Market Pulse indicators (next in Wave 2)
- Plan 04-07: Template rendering of what_to_watch data

**Known Issues:** None

## Performance Notes

- **Duration**: 1.5 minutes (schema + method + verification)
- **Commits**: 1 atomic commit
- **Token efficiency**: Reused existing Azure OpenAI client pattern from Plans 04-01 and 04-02
- **Code reuse**: Similar structure to _generate_executive_summary (prompt + structured output + fallback)

## Lessons Learned

1. **Dual filtering criteria**: Priority OR category provides better article coverage than AND logic
2. **Top 15 articles**: Balances rich context with token budget constraints
3. **Temperature 0.5**: Higher than classification (0.3) or summaries (0.4) to encourage forward-looking creativity
4. **Empty fallback**: Template can render gracefully with empty items list (no special handling needed)
5. **Prompt specificity**: WHEN and WHO requirements ensure actionable output, not generic trends

## Context for Future Sessions

**What this enables:**
- REPT-06 requirement: Forward-looking "What to Watch" section with timeframes
- Cross-role strategic analysis complementing per-role executive summaries
- Actionable intelligence for proactive planning (M&A due diligence, regulatory timelines, renewal prep)

**Integration points:**
- Plan 04-07: Template rendering of {{ what_to_watch.items }} with timeframes and impact_roles
- Future enhancement: Track signals over time to identify recurring themes
- Future enhancement: Link signals to specific articles for deep-dive analysis

**Pattern established:**
- Filtered article analysis → AI generation with structured output → fallback handling → template context
- Reusable pattern for other cross-role analysis sections (market pulse, entity tracker)
