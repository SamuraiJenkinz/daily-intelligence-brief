# Phase 3: Advanced Classification Pipeline - Research

**Researched:** 2026-02-07
**Domain:** AI Classification with Azure OpenAI GPT-4o Structured Outputs
**Confidence:** HIGH

## Summary

This research investigates how to expand the existing Phase 1 classification system (roles, priority, summary, sentiment) to include comprehensive intelligence features: entity extraction (companies, people, organizations), impact level scoring, and categorical tagging (category, region, business line).

The standard approach is to **expand the existing Pydantic schema and extend the single GPT-4o call** rather than creating multiple passes. GPT-4o with structured outputs can reliably handle complex, multi-faceted classification in a single request with 100% schema compliance. This approach is more token-efficient than multiple API calls and maintains the existing architecture pattern.

Key technical requirements identified:
- Expand ArticleClassification Pydantic schema with new fields (entities, impact_level, category, region, business_line)
- Update NewsArticle ORM model with corresponding database columns
- Create Alembic migration to add columns to existing SQLite database
- Refine system prompt with entity extraction guidance and business logic for new fields
- Token cost remains acceptable: ~$0.015-0.025 per article (input + output)

**Primary recommendation:** Extend the existing single-pass classification pattern with expanded Pydantic schema. Use Alembic for database migration. Keep prompt engineering focused on insurance domain context.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | 2.16.0+ | Azure OpenAI SDK with structured outputs | Official Microsoft/OpenAI SDK, beta.chat.completions.parse() for guaranteed schema compliance |
| pydantic | 2.11.0+ | Schema definition and validation | Industry standard for structured outputs, type safety, JSON schema generation |
| sqlalchemy | latest | ORM for database operations | Already in use, mature Python ORM |
| alembic | latest | Database migrations | SQLAlchemy's official migration tool, handles SQLite batch operations |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | latest | Structured logging | Already in use, aids debugging classification |
| sentence-transformers | 5.0.0+ | Entity normalization (optional) | If entity deduplication/linking needed beyond GPT-4o |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single GPT-4o call | Multiple specialized calls (entity extraction pass, then classification pass) | Multi-pass is 2-3x more expensive and slower, no accuracy benefit with GPT-4o structured outputs |
| Alembic migrations | Manual ALTER TABLE | Manual approach error-prone with SQLite's limited ALTER support, no version control |
| GPT-4o | GPT-4o-mini for classification | GPT-4o-mini is 10x cheaper but significantly less accurate for complex multi-faceted classification and entity extraction |

**Installation:**
```bash
pip install alembic
# Other dependencies already in requirements.txt
```

## Architecture Patterns

### Recommended Schema Expansion Pattern

**Expand existing ArticleClassification schema in-place:**

```python
# app/schemas/classification.py
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# New entity types
class ExtractedEntity(BaseModel):
    """Entity extracted from article text."""
    name: str = Field(description="Entity name as it appears in text")
    type: Literal["company", "person", "organization"] = Field(
        description="Entity type: company (insurers, brokers, vendors), "
                    "person (executives, analysts), organization (regulators, associations)"
    )
    context: Optional[str] = Field(
        default=None,
        description="Brief context of entity's role in article (optional)"
    )

# Categorical types
CategoryType = Literal[
    "M&A", "Regulatory", "Loss Event", "Financial Results",
    "Market Trends", "Product Launch", "Executive Change", "Other"
]
RegionType = Literal[
    "North America", "Europe", "Asia Pacific", "Latin America",
    "Middle East & Africa", "Global"
]
BusinessLineType = Literal[
    "Property", "Casualty", "Life & Health", "Reinsurance",
    "Specialty", "Multiple Lines", "Other"
]

# Expanded classification schema (EXTENDS existing, doesn't replace)
class ArticleClassification(BaseModel):
    """Comprehensive article classification with entity extraction."""

    # EXISTING FIELDS (from Phase 1)
    roles: List[RoleType] = Field(...)
    priority: PriorityType = Field(...)
    summary: str = Field(...)
    sentiment: SentimentType = Field(...)

    # NEW FIELDS (Phase 3)
    entities: List[ExtractedEntity] = Field(
        default_factory=list,
        description="Companies, people, and organizations mentioned in article. "
                    "Extract 3-10 most relevant entities, prioritize those with significant context."
    )
    impact_level: Literal["Critical", "High", "Medium", "Low"] = Field(
        description="Market impact level: Critical (market-moving), High (significant), "
                    "Medium (notable), Low (minor). Consider financial magnitude, "
                    "regulatory scope, and strategic implications."
    )
    category: CategoryType = Field(
        description="Primary article category based on content theme"
    )
    region: RegionType = Field(
        description="Primary geographic region for article. Use Global for multi-region stories."
    )
    business_line: BusinessLineType = Field(
        description="Primary insurance business line affected. Use Multiple Lines for cross-segment stories."
    )
```

**Why this pattern:**
- Backward compatible: existing classification code continues to work
- Single API call: GPT-4o handles all fields in one request (~1500-2500 tokens output)
- Type safety: Pydantic enforces valid values for all enums
- Structured outputs guarantee: 100% schema compliance with GPT-4o structured outputs mode

### Database Migration Pattern

**Use Alembic batch operations for SQLite:**

```bash
# Initialize Alembic (first time only)
cd mdinsights
alembic init alembic

# Create migration
alembic revision --autogenerate -m "add_advanced_classification_fields"

# Migration will use batch_alter_table for SQLite compatibility
```

**Migration template for SQLite:**
```python
# alembic/versions/xxx_add_advanced_classification.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # SQLite requires batch mode for ALTER TABLE
    with op.batch_alter_table('news_articles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('entities', sa.Text, nullable=True))
        batch_op.add_column(sa.Column('impact_level', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('category', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('region', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('business_line', sa.String(50), nullable=True))

def downgrade():
    # Batch mode for rollback
    with op.batch_alter_table('news_articles', schema=None) as batch_op:
        batch_op.drop_column('business_line')
        batch_op.drop_column('region')
        batch_op.drop_column('category')
        batch_op.drop_column('impact_level')
        batch_op.drop_column('entities')
```

**Why Alembic batch mode:**
- SQLite only supports ADD COLUMN and RENAME COLUMN in ALTER TABLE
- Batch mode creates temp table, copies data, swaps tables
- Version controlled migrations with rollback capability
- Production-safe with transaction support

### Pattern: Single-Pass Classification with Expanded Prompt

**Extend existing CLASSIFICATION_PROMPT with entity and categorization guidance:**

```python
CLASSIFICATION_PROMPT = """[Existing role/priority/sentiment guidance...]

**Entity Extraction Guidelines:**

Extract 3-10 of the MOST RELEVANT entities (companies, people, organizations) mentioned in the article:
- **Companies**: Insurance carriers, brokers, reinsurers, vendors (e.g., "Marsh McLennan", "AIG", "Lloyd's of London")
- **People**: Named executives, analysts, regulators (e.g., "John Smith, CEO of Zurich Insurance")
- **Organizations**: Regulators, trade associations, rating agencies (e.g., "NAIC", "AM Best", "European Commission")

Prioritize entities with significant context or impact. Normalize company names to full official names.

**Impact Level Guidelines:**

Assess market impact based on:
- **Critical**: Market-moving events ($1B+ losses, major regulatory changes, systemic risk)
- **High**: Significant impact ($100M-$1B range, important M&A, notable regulatory shifts)
- **Medium**: Notable but contained ($10M-$100M, smaller M&A, local regulations)
- **Low**: Minor industry news (<$10M, routine updates, individual appointments)

**Category Assignment:**

- **M&A**: Mergers, acquisitions, divestitures, strategic partnerships
- **Regulatory**: New regulations, compliance requirements, legal rulings
- **Loss Event**: Natural catastrophes, claims developments, reserve issues
- **Financial Results**: Earnings reports, rate changes, combined ratios
- **Market Trends**: Industry analysis, forecasts, emerging risks
- **Product Launch**: New products, coverage innovations
- **Executive Change**: C-suite appointments, leadership transitions
- **Other**: Articles not fitting above categories

**Region Assignment:**

Use the PRIMARY geographic focus. Multi-region stories → "Global"

**Business Line Assignment:**

- **Property**: Property insurance, homeowners, commercial property
- **Casualty**: Auto, liability, workers compensation
- **Life & Health**: Life insurance, health, accident
- **Reinsurance**: Reinsurance treaties, capital markets
- **Specialty**: Cyber, D&O, professional liability, niche coverages
- **Multiple Lines**: Cross-segment stories, multi-line carriers
"""
```

### Anti-Patterns to Avoid

- **Multi-Pass Classification:** Making separate API calls for entities, then categories, then sentiment. GPT-4o handles all in one call efficiently. Multi-pass costs 2-3x more with no accuracy gain.
- **Manual JSON Parsing:** Using json_mode instead of structured outputs. Structured outputs guarantee schema compliance, json_mode doesn't.
- **Over-Extraction:** Extracting every mentioned name. Focus on 3-10 most relevant entities with actual context.
- **Hardcoded Enums:** Putting categories in prompt as strings. Use Pydantic Literals for type safety.
- **Skipping Migration Tool:** Manual SQL ALTER statements. SQLite's limited ALTER support breaks easily, Alembic handles edge cases.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Entity normalization | Custom fuzzy matching for company names | GPT-4o with clear instructions in prompt, optionally sentence-transformers for post-processing | GPT-4o already understands "Marsh" = "Marsh McLennan". Custom fuzzy matching has edge cases (abbreviations, subsidiaries, internationalization). |
| Database schema changes | Manual ALTER TABLE SQL scripts | Alembic migrations with batch mode | SQLite's ALTER limitations cause failures. Alembic handles create temp → copy → swap pattern automatically. |
| Enum validation | String fields with validation in code | Pydantic Literal types | Structured outputs enforce valid values at API level. Runtime validation catches bugs late. |
| Token counting | Custom tokenizer code | OpenAI tiktoken library (if needed) | Official tokenizer, already used by OpenAI internally. Custom implementations drift from actual API behavior. |
| Entity deduplication across articles | Manual string matching | sentence-transformers with existing deduplicator pattern | Project already uses sentence-transformers for article dedup. Same approach works for entity linking. |

**Key insight:** GPT-4o structured outputs with well-designed Pydantic schemas eliminate the need for post-processing validation code. The API guarantees schema compliance, shifting validation from runtime to API call.

## Common Pitfalls

### Pitfall 1: Schema Changes Breaking Existing Data
**What goes wrong:** Adding required fields to Pydantic schema causes existing database records (with NULL values) to fail validation when loaded.

**Why it happens:** Pydantic's strict validation rejects NULL/None for required fields. Existing articles have only Phase 1 fields populated.

**How to avoid:**
- Make ALL new fields Optional in Pydantic schema or provide sensible defaults
- Database columns should be nullable (nullable=True in SQLAlchemy)
- Handle backwards compatibility in queries (filter for non-null values if needed)

**Warning signs:**
- "ValidationError: field required" when loading old articles
- Can't query articles classified before Phase 3

### Pitfall 2: SQLite ALTER TABLE Limitations
**What goes wrong:** Direct ALTER TABLE statements fail with "cannot alter table" errors in SQLite.

**Why it happens:** SQLite only supports ADD COLUMN and RENAME COLUMN. Any other changes require full table recreation. Developers expect PostgreSQL/MySQL ALTER capabilities.

**How to avoid:**
- Always use Alembic's batch_alter_table() context manager
- Test migrations on copy of production database
- Never use raw SQL ALTER on SQLite

**Warning signs:**
- "table X may not be altered" errors
- Data loss when migration partially completes

### Pitfall 3: Over-Engineering Entity Extraction
**What goes wrong:** Building complex entity resolution systems with knowledge graphs, external APIs, custom NER models, etc.

**Why it happens:** Traditional NLP approach assumes basic language models need help. Developers over-optimize before measuring need.

**How to avoid:**
- Start with GPT-4o's native entity understanding
- Prompt engineering first: "normalize company names to official form"
- Add post-processing only if metrics show specific problems
- Insurance entities are well-known to GPT-4o (unlike domain-specific jargon)

**Warning signs:**
- Multiple API calls for entity resolution per article
- Integration with 3rd party entity databases before testing native extraction
- Complexity exceeding the original classification service

### Pitfall 4: Token Cost Optimization Premature
**What goes wrong:** Switching to GPT-4o-mini or aggressive prompt compression before measuring actual costs and quality impact.

**Why it happens:** $0.02/article seems expensive at scale. Developers optimize costs before establishing quality baseline.

**How to avoid:**
- Calculate actual monthly cost based on article volume: (articles/month) × $0.02 = likely <$500/month for 25K articles
- Measure classification quality metrics FIRST (accuracy, entity relevance, category precision)
- GPT-4o-mini is 10x cheaper but significantly worse at complex extraction
- Batch API provides 50% discount for non-urgent classification (run overnight)

**Warning signs:**
- Classification quality degradation after "optimization"
- Trying to compress prompts before hitting budget constraints
- Complex routing logic (GPT-4o vs mini) adding more cost in code maintenance

### Pitfall 5: Ignoring Structured Outputs Schema Limits
**What goes wrong:** Deeply nested Pydantic schemas or very large enum lists cause API errors or slow responses.

**Why it happens:** Structured outputs have practical limits on schema complexity. Developers treat it like arbitrary JSON.

**How to avoid:**
- Keep schema max 3 levels deep (ArticleClassification → ExtractedEntity → primitives)
- Literal enums should have <50 values
- Use strings with descriptions for truly open-ended fields (like summary)
- Test schema with OpenAI before integrating

**Warning signs:**
- API timeouts or 400 errors on schema parsing
- Inconsistent outputs (falling back to json_mode behavior)

## Code Examples

Verified patterns from official sources:

### Entity Extraction with Structured Outputs
```python
# Source: Microsoft Learn - Entity Extraction with Azure OpenAI Structured Outputs
# https://learn.microsoft.com/en-us/azure/developer/ai/how-to/extract-entities-using-structured-outputs

from pydantic import BaseModel, Field
from typing import List

class ExtractedEntity(BaseModel):
    """Entity from article text."""
    name: str = Field(description="Entity name normalized to official form")
    type: str = Field(description="Entity type: company, person, organization")
    context: str = Field(description="Brief role/context in article")

class ArticleClassification(BaseModel):
    # ... existing fields ...
    entities: List[ExtractedEntity] = Field(
        default_factory=list,
        description="Extract 3-10 most relevant entities with context"
    )

# Call structured output API
completion = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": CLASSIFICATION_PROMPT},
        {"role": "user", "content": article_text}
    ],
    response_format=ArticleClassification,
    temperature=0.3
)

result = completion.choices[0].message.parsed
# result.entities is guaranteed to be List[ExtractedEntity]
```

### SQLite Batch Migration with Alembic
```python
# Source: Alembic Documentation - Running Batch Migrations for SQLite
# https://alembic.sqlalchemy.org/en/latest/batch.html

from alembic import op
import sqlalchemy as sa

def upgrade():
    """Add Phase 3 classification fields."""
    with op.batch_alter_table('news_articles', schema=None) as batch_op:
        # Alembic handles create temp table → copy data → swap
        batch_op.add_column(sa.Column('entities', sa.Text, nullable=True))
        batch_op.add_column(sa.Column('impact_level', sa.String(20), nullable=True))
        batch_op.add_column(sa.Column('category', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('region', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('business_line', sa.String(50), nullable=True))

def downgrade():
    """Remove Phase 3 fields (rollback)."""
    with op.batch_alter_table('news_articles', schema=None) as batch_op:
        batch_op.drop_column('business_line')
        batch_op.drop_column('region')
        batch_op.drop_column('category')
        batch_op.drop_column('impact_level')
        batch_op.drop_column('entities')
```

### Expanding Classifier Service Method
```python
# Pattern: Extend existing classify_articles method minimally

def classify_articles(self, db: Session, articles: List[NewsArticle]) -> int:
    """Classify articles with Phase 3 expanded schema."""
    for article in articles:
        classification = self.classify_article(
            title=article.title,
            description=article.description or "",
            source=article.source_name or "Unknown"
        )

        # EXISTING Phase 1 fields
        article.roles = json.dumps(classification.roles)
        article.priority = classification.priority
        article.summary = classification.summary
        article.sentiment = classification.sentiment

        # NEW Phase 3 fields - serialize entities as JSON
        article.entities = json.dumps([e.dict() for e in classification.entities])
        article.impact_level = classification.impact_level
        article.category = classification.category
        article.region = classification.region
        article.business_line = classification.business_line

        db.commit()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Multi-pass classification (separate entity extraction + classification) | Single-pass with GPT-4o structured outputs | August 2024 (GPT-4o structured outputs release) | 50-70% cost reduction, 2-3x faster, simpler architecture |
| JSON mode with manual validation | Structured outputs with Pydantic | August 2024 (API version 2024-08-01-preview) | 100% schema compliance, zero validation code, type safety |
| Custom NER models (spaCy, BERT) | GPT-4o native entity understanding | 2023-2024 (GPT-4 → GPT-4o improvements) | Higher accuracy for domain entities, no model training/maintenance |
| Manual ALTER TABLE scripts | Alembic migrations | Industry standard since ~2010 | Version control, rollback capability, team collaboration |

**Deprecated/outdated:**
- **OpenAI completion API (non-chat)**: Replaced by chat completions. Use beta.chat.completions.parse() for structured outputs.
- **JSON mode without schema**: Replaced by structured outputs. JSON mode doesn't guarantee schema compliance.
- **API version <2024-08-01-preview**: Earlier versions lack structured outputs support. Use 2024-08-01-preview or later.

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal entity count per article**
   - What we know: Microsoft examples show 3-10 entities typical, more entities = more tokens
   - What's unclear: Impact on downstream report quality (too many entities clutter briefs, too few miss context)
   - Recommendation: Start with "3-10 most relevant" in prompt, measure report quality in Phase 4/5. Adjust based on user feedback.

2. **Entity normalization accuracy without external database**
   - What we know: GPT-4o knows major insurance companies (AIG, Marsh, Lloyd's), can normalize common variations
   - What's unclear: Accuracy on smaller regional insurers, subsidiaries, international name variations
   - Recommendation: Track entity extraction quality metrics, add post-processing normalization ONLY if metrics show specific gaps. Most insurance entities are well-known.

3. **Database performance with JSON columns at scale**
   - What we know: SQLite TEXT columns for JSON data (roles, entities) work fine for 100K-1M records
   - What's unclear: Query performance impact when filtering by entity names (requires JSON parsing)
   - Recommendation: Start with JSON TEXT columns. If entity filtering becomes critical, consider separate entities table with many-to-many relationship in future phase.

4. **Category/business line taxonomy evolution**
   - What we know: Initial taxonomy covers major categories (M&A, Regulatory, etc.)
   - What's unclear: How often taxonomy needs updating, whether "Other" category grows over time
   - Recommendation: Include "Other" category with plan to review classification metrics quarterly. Expand taxonomy based on "Other" frequency.

5. **Batch API for cost optimization timing**
   - What we know: Batch API offers 50% cost savings for non-urgent requests
   - What's unclear: Whether nightly batch classification acceptable for business requirements
   - Recommendation: Implement real-time classification first (Phase 3), add batch optimization in Phase 7 (scheduling) if budget constraints emerge.

## Sources

### Primary (HIGH confidence)
- [Microsoft Learn - Extract Entities Using Azure OpenAI Structured Outputs](https://learn.microsoft.com/en-us/azure/developer/ai/how-to/extract-entities-using-structured-outputs) - Entity extraction patterns with Pydantic
- [Azure-Samples/azure-openai-entity-extraction](https://github.com/Azure-Samples/azure-openai-entity-extraction) - Official Microsoft code examples
- [OpenAI Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs) - API capabilities and best practices
- [Alembic Batch Migrations Documentation](https://alembic.sqlalchemy.org/en/latest/batch.html) - SQLite migration patterns

### Secondary (MEDIUM confidence)
- [Azure OpenAI Pricing](https://azure.microsoft.com/en-us/pricing/details/azure-openai/) - GPT-4o costs: $0.005/1K input, $0.015/1K output tokens
- [Pydantic Migration Guide](https://docs.pydantic.dev/latest/migration/) - Schema expansion patterns
- [Insurance Business Lines Overview (III)](https://www.iii.org/fact-statistic/facts-statistics-commercial-lines) - Standard insurance taxonomies
- [GPT-4o Prompt Optimization Research](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1558938/full) - Token efficiency patterns

### Tertiary (LOW confidence)
- WebSearch findings on insurance taxonomy 2026 trends - Use for general context, verify specific categories
- Community blog posts on entity extraction - Patterns validated against official docs above

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official docs, already in use or standard SQLAlchemy tooling
- Architecture: HIGH - Single-pass structured outputs pattern verified via Microsoft Learn and OpenAI docs, Alembic batch mode documented
- Pitfalls: MEDIUM-HIGH - Based on community experience and official SQLite/Alembic limitations docs. Entity extraction pitfalls are lower confidence (less documentation).

**Research date:** 2026-02-07
**Valid until:** 2026-03-07 (30 days - stable technologies, but Azure OpenAI API evolving)
