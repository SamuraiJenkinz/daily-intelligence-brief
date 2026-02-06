---
phase: 01-vertical-slice-foundation
plan: 03
subsystem: classification
tags: [azure-openai, gpt-4o, structured-outputs, role-classification, pydantic]

requires:
  - phase: 01-01
    provides: ArticleClassification Pydantic schema, Azure OpenAI config, NewsArticle model
  - phase: 01-02
    provides: Raw articles in database with NULL classification fields
provides:
  - RoleClassificationService with structured output parsing
  - Batch classification workflow with progress tracking and error recovery
  - Classification test script with multi-role validation
  - Run model with classification metrics (articles_classified, classification_errors)
affects: [01-04-reporter, 01-05-pipeline]

tech-stack:
  added: [azure-openai-structured-outputs, openai-sdk-beta-parse]
  patterns: [classification-service-pattern, batch-processing-with-error-recovery, multi-role-assignment]

key-files:
  created:
    - app/services/classifier.py
    - scripts/test_classification.py
  modified:
    - app/models/run.py

key-decisions:
  - "Used Azure OpenAI structured outputs (beta.chat.completions.parse) for guaranteed schema compliance"
  - "Temperature 0.3 for consistent classification results based on research recommendations"
  - "Multi-role assignment as default strategy with generous role assignment guidance in prompt"
  - "Batch commit every 10 articles for progress tracking and error recovery"
  - "Skip failed articles instead of blocking entire batch to ensure resilience"

duration: 2min
completed: 2026-02-06
---

# Plan 01-03: Basic AI Classification Summary

**Azure OpenAI GPT-4o classification with structured outputs and multi-role support**

## What Was Built

Implemented complete Azure OpenAI classification service using GPT-4o with structured output parsing to assign role tags, priority, summary, and sentiment to scraped articles. The system guarantees schema compliance and supports multi-role assignment for maximum audience reach.

### Core Components

**1. RoleClassificationService** (`app/services/classifier.py`)
- Azure OpenAI client initialization with structured output support
- `classify_article()` method using `beta.chat.completions.parse()` with ArticleClassification schema
- Temperature 0.3 for consistent classification results
- Comprehensive error handling with exceptions for retry logic
- structlog integration for observability

**2. Classification Prompt System**
- CLASSIFICATION_PROMPT constant with detailed role definitions and examples
- **Critical multi-role guidance**: "Most significant articles apply to multiple roles. Be generous with role assignment."
- Role definitions with concrete examples:
  - **Brokers**: Competitor intel, market positioning, pricing trends, capacity shifts, broker M&A
  - **Leadership**: Major M&A, financial results, strategic shifts, industry forecasts, exec changes
  - **Compliance**: Regulatory changes, legal developments, coverage gaps, policy reforms, sanctions
  - **Underwriting**: Cat losses, combined ratios, reserve adequacy, rate movements, risk trends
- Multi-role examples (M&A → Brokers + Leadership, regulatory → Compliance + Leadership + Underwriting)
- Priority guidance (Critical/High/Medium/Monitor) and sentiment guidance (positive/negative/neutral)

**3. Batch Classification Workflow**
- `classify_articles()` method processing lists of NewsArticle objects
- Batch commits every 10 articles for progress tracking and error recovery
- Skip failed articles to prevent blocking entire batch
- structlog progress logging (e.g., "Classified 5/20 articles")
- Returns count of successfully classified articles

**4. Classification Test Script** (`scripts/test_classification.py`)
- Standalone test script for classification validation
- Queries unclassified articles from latest run (limit 5 for cost control)
- Creates RoleClassificationService and runs classification
- Validates multi-role assignment target (40-60% expected)
- Displays classification results with metrics and validation

**5. Run Model Metrics**
- Added `articles_classified` field (int, default 0) to Run model
- Added `classification_errors` field (int, default 0) to Run model
- Enables health check observability and progress tracking

## Technical Implementation

### Azure OpenAI Structured Outputs

Used OpenAI SDK beta feature `beta.chat.completions.parse()` with Pydantic schema as `response_format`:

```python
completion = self.client.beta.chat.completions.parse(
    model=self.deployment,
    messages=[
        {"role": "system", "content": CLASSIFICATION_PROMPT},
        {"role": "user", "content": user_message}
    ],
    response_format=ArticleClassification,
    temperature=0.3
)
classification = completion.choices[0].message.parsed
```

**Benefits:**
- Guaranteed schema compliance (no JSON parsing failures)
- Type-safe classification results
- Automatic validation against Pydantic schema
- Consistent output format for downstream processing

### Multi-Role Assignment Strategy

Emphasized generous multi-role assignment in prompt to maximize audience reach:
- Most significant articles apply to 2+ roles (target: 40-60%)
- Provided multi-role examples in classification prompt
- Better to over-include than miss an audience

### Error Recovery

Implemented resilient batch processing:
- Try/except per article to skip classification failures
- Continue processing remaining articles on error
- Log failures with article ID and error details
- Commit in batches of 10 for progress tracking
- No cascade failures from single article issues

### Database Integration

Stores classification results as JSON in NewsArticle model:
```python
article.roles = json.dumps(classification.roles)  # ["Brokers", "Leadership"]
article.priority = classification.priority
article.summary = classification.summary
article.sentiment = classification.sentiment
```

## Verification

Created test script that:
1. Queries unclassified articles from database (limit 5)
2. Runs classification via RoleClassificationService
3. Displays classification results (roles, priority, sentiment, summary)
4. Validates multi-role assignment percentage (40-60% target)

**Note**: Test script not executed (requires live Azure OpenAI API key). Ready for manual testing with `python scripts/test_classification.py`.

## Dependencies

**Upstream (requires):**
- 01-01: ArticleClassification Pydantic schema, Azure OpenAI config in Settings, NewsArticle ORM model
- 01-02: Raw articles in database with NULL classification fields

**Downstream (affects):**
- 01-04: Reporter service needs classified articles with roles JSON for template rendering
- 01-05: Manual pipeline orchestrates collection → classification → reporting sequence

## Integration Points

- **app/config.py**: Azure OpenAI credentials (endpoint, api_key, deployment, api_version)
- **app/schemas/classification.py**: ArticleClassification schema with RoleType/PriorityType/SentimentType literals
- **app/models/news_article.py**: roles (Text/JSON), priority (String), summary (Text), sentiment (String) fields
- **app/models/run.py**: articles_classified, classification_errors metrics
- **app/database.py**: SessionLocal for database access

## File Structure

```
app/
├── services/
│   ├── __init__.py
│   ├── collector.py (existing)
│   └── classifier.py (new - 221 lines)
├── models/
│   └── run.py (modified - added 2 fields)
scripts/
└── test_classification.py (new - 151 lines)
```

## Deviations from Plan

None - plan executed exactly as written.

## Quality Metrics

- **Code**: 372 new lines across 2 files, 4 lines modified in 1 file
- **Type Safety**: Full type hints with Pydantic schema validation
- **Error Handling**: Comprehensive try/except with error logging and batch resilience
- **Observability**: structlog integration for classification progress and error tracking
- **Testing**: Standalone test script with validation metrics

## Next Steps

**For 01-04 (Reporter Service):**
- Reporter will parse roles JSON from classified articles
- Group articles by role for tabbed template rendering
- Use priority field for article sorting within role sections

**For 01-05 (Manual Pipeline):**
- Orchestrate collection → classification → reporting sequence
- Track classification metrics in Run model
- Handle classification failures gracefully

## Lessons Learned

1. **Structured outputs eliminate JSON parsing complexity**: Using `beta.chat.completions.parse()` with Pydantic schema guarantees schema compliance and removes error-prone JSON parsing logic.

2. **Multi-role assignment requires explicit guidance**: Prompts must emphasize generous role assignment with concrete multi-role examples to achieve 40-60% multi-role coverage.

3. **Batch commits enable progress tracking**: Committing every 10 articles provides observability and enables error recovery without losing all progress.

4. **Skip-on-error pattern prevents cascade failures**: Processing remaining articles on single failure improves batch resilience and overall success rate.
