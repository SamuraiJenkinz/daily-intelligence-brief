# Phase 4: Intelligence Report Generation - Research

**Researched:** 2026-02-07
**Domain:** HTML report generation with Azure OpenAI, Jinja2, and data visualization
**Confidence:** HIGH

## Summary

Phase 4 generates production-quality tabbed HTML intelligence briefs with executive summaries, sector heatmaps, entity tracking, and forward-looking analysis. The research confirms that the existing stack (Azure OpenAI GPT-4o with structured outputs, Jinja2 templates, premailer CSS inlining) is optimal for this phase. The key technical challenge is structuring GPT-4o calls for per-role executive summaries and "What to Watch" analysis, and implementing pure Python data aggregation for heatmaps and entity tracking.

The consolidation directive (merging plans 04-07 through 04-10) is technically sound because all four involve template/CSS work without data aggregation logic. These can be grouped into a single "Template Enhancement & Branding" plan plus a separate "Mobile Responsive & Attribution" plan.

**Primary recommendation:** Use separate GPT-4o calls for per-role executive summaries (4 calls) and one call for cross-role "What to Watch" analysis. Implement data aggregation as pure Python functions in the reporter service, passing pre-computed data structures to the template.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Azure OpenAI Python SDK | 1.x | GPT-4o structured outputs | Native Azure integration, beta.chat.completions.parse() |
| Jinja2 | 3.1+ | HTML template rendering | Industry standard for Python templating |
| Pydantic | 2.x | Schema validation for AI outputs | Already used in Phase 3 for ArticleClassification |
| premailer | 3.10+ | CSS inlining for email | Email client compatibility (Phase 5) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | Latest | Structured logging | Already in use, track AI call patterns |
| Collections (stdlib) | Python 3.11 | Counter, defaultdict for aggregation | Entity counting, sector grouping |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 | Mako, Cheetah | Jinja2 has better email/HTML ecosystem |
| Azure OpenAI | OpenAI direct | Azure provides enterprise compliance |
| Pure Python aggregation | Pandas | Pandas overkill for simple counting/grouping |

**Installation:**
```bash
# Already installed in existing environment
# No new dependencies required for Phase 4
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── services/
│   ├── reporter.py           # RoleReportService with AI summary generation
│   ├── aggregator.py          # NEW: Data aggregation functions (heatmap, entities, pulse)
│   └── classifier.py          # Existing: Article classification
├── schemas/
│   ├── classification.py      # Existing: ArticleClassification
│   └── report_context.py      # NEW: ReportContext, ExecutiveSummary, WhatToWatch schemas
├── templates/
│   ├── role_brief.html        # Existing: Enhance with new sections
│   └── components/            # OPTIONAL: Reusable template fragments
└── storage/
    └── reports/               # Existing: Generated HTML files
```

### Pattern 1: Per-Role Executive Summary Generation
**What:** Generate tailored AI summaries for each role tab using separate GPT-4o calls
**When to use:** Need role-specific context and priorities in executive summary
**Example:**
```python
# Source: Azure OpenAI structured outputs documentation
# https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs

class ExecutiveSummary(BaseModel):
    """Schema for role-specific executive summary."""
    summary_paragraphs: List[str] = Field(
        description="2-3 paragraphs of executive summary for this role",
        min_items=2,
        max_items=3
    )
    key_numbers: List[str] = Field(
        description="3-5 highlighted numbers/statistics from today's articles",
        max_items=5
    )
    role_context: str = Field(
        description="One-sentence context about why this matters to this role"
    )

# In RoleReportService
def generate_executive_summary(
    self,
    role: str,
    articles: List[NewsArticle],
    report_date: datetime
) -> ExecutiveSummary:
    """Generate AI executive summary for specific role."""

    # Filter articles for this role
    role_articles = [a for a in articles if role in json.loads(a.roles)]

    # Build context from articles
    article_summaries = "\n\n".join([
        f"- [{a.priority}] {a.title}: {a.summary}"
        for a in sorted(role_articles, key=lambda x: priority_order(x.priority))
    ])

    prompt = f"""Generate an executive summary for {role} based on today's intelligence.

Articles for {role} ({len(role_articles)} total):
{article_summaries}

Write 2-3 paragraphs highlighting the most important developments for {role}.
Include specific numbers, dates, and entity names where relevant.
Focus on actionable insights and strategic implications."""

    completion = self.client.beta.chat.completions.parse(
        model=self.deployment,
        messages=[
            {"role": "system", "content": "You are an intelligence analyst writing executive summaries for insurance industry professionals."},
            {"role": "user", "content": prompt}
        ],
        response_format=ExecutiveSummary,
        temperature=0.5  # Slightly higher for natural prose
    )

    return completion.choices[0].message.parsed
```

### Pattern 2: Cross-Role "What to Watch" Analysis
**What:** Single GPT-4o call analyzing all articles for forward-looking insights
**When to use:** Need comprehensive market outlook across all roles
**Example:**
```python
class WhatToWatchItem(BaseModel):
    """Single forward-looking item."""
    title: str = Field(description="Concise headline (5-8 words)")
    description: str = Field(description="1-2 sentence explanation of what to watch and why")
    timeframe: str = Field(description="When this matters (e.g., 'Next 30-60 days', 'Q2 2026')")
    impact_roles: List[str] = Field(description="Which roles should monitor this")

class WhatToWatch(BaseModel):
    """Cross-role forward-looking analysis."""
    items: List[WhatToWatchItem] = Field(
        description="4-6 forward-looking items to monitor",
        min_items=4,
        max_items=6
    )

# Single call analyzing all articles
def generate_what_to_watch(
    self,
    articles: List[NewsArticle],
    report_date: datetime
) -> WhatToWatch:
    """Generate forward-looking 'What to Watch' section."""

    # Include all high/critical articles plus market trends
    relevant_articles = [
        a for a in articles
        if a.priority in ["Critical", "High"] or a.category == "Market Trends"
    ]

    prompt = f"""Analyze today's intelligence for forward-looking signals.

Identify 4-6 items that require monitoring over the next 30-180 days.
Focus on:
- Ongoing M&A due diligence and approvals
- Regulatory changes with implementation timelines
- Market renewal cycles (reinsurance, specific geographies)
- Emerging risks flagged by analysts

Today's articles: {len(relevant_articles)} relevant items
{build_article_context(relevant_articles)}

For each item, specify WHEN it matters and WHO should monitor it."""

    completion = self.client.beta.chat.completions.parse(
        model=self.deployment,
        messages=[
            {"role": "system", "content": "You are a strategic intelligence analyst identifying forward-looking market signals."},
            {"role": "user", "content": prompt}
        ],
        response_format=WhatToWatch,
        temperature=0.6  # Balance creativity with accuracy
    )

    return completion.choices[0].message.parsed
```

### Pattern 3: Pure Python Data Aggregation
**What:** Pre-compute heatmap, entity tracker, market pulse data before template rendering
**When to use:** Simple counting/grouping that doesn't need AI
**Example:**
```python
# app/services/aggregator.py
from collections import Counter, defaultdict
from typing import List, Dict
import json

class ReportAggregator:
    """Pure Python data aggregation for report components."""

    @staticmethod
    def aggregate_sector_heatmap(articles: List[NewsArticle]) -> List[Dict]:
        """
        Aggregate articles by business line and sentiment for heatmap.

        Returns list of {sector, signal, sentiment_class} dicts for template.
        """
        sector_data = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})

        for article in articles:
            if article.business_line and article.sentiment:
                sector_data[article.business_line][article.sentiment] += 1

        heatmap_cells = []
        for sector, sentiments in sector_data.items():
            # Determine overall signal
            if sentiments["positive"] > sentiments["negative"]:
                signal = "positive"
                signal_text = "Favorable trends"
            elif sentiments["negative"] > sentiments["positive"]:
                signal = "negative"
                signal_text = "Risk indicators"
            else:
                signal = "neutral"
                signal_text = "Mixed signals"

            heatmap_cells.append({
                "sector": sector,
                "signal": signal_text,
                "signal_class": f"heat-{signal}",
                "article_count": sum(sentiments.values())
            })

        # Sort by article count descending
        return sorted(heatmap_cells, key=lambda x: x["article_count"], reverse=True)

    @staticmethod
    def aggregate_entity_tracker(articles: List[NewsArticle], top_n: int = 15) -> List[Dict]:
        """
        Count entity mentions across all articles.

        Returns list of {name, count, type} dicts sorted by count.
        """
        entity_counts = defaultdict(lambda: {"count": 0, "type": None})

        for article in articles:
            if article.entities:
                entities = json.loads(article.entities)
                for entity in entities:
                    name = entity["name"]
                    entity_counts[name]["count"] += 1
                    entity_counts[name]["type"] = entity["type"]  # Last seen type

        # Convert to list and sort
        entity_list = [
            {"name": name, "count": data["count"], "type": data["type"]}
            for name, data in entity_counts.items()
        ]

        return sorted(entity_list, key=lambda x: x["count"], reverse=True)[:top_n]

    @staticmethod
    def aggregate_market_pulse(articles: List[NewsArticle]) -> List[Dict]:
        """
        Generate market pulse indicators by sector.

        Returns list of {label, value, status_class} for pulse bar.
        """
        # Group by business line + region for sector-specific signals
        pulse_items = []

        # Example: US P&C industry health
        us_pc_articles = [
            a for a in articles
            if a.region == "North America" and a.business_line in ["Property", "Casualty"]
        ]
        if us_pc_articles:
            avg_sentiment = calculate_sentiment_score(us_pc_articles)
            pulse_items.append({
                "label": "US P&C Industry",
                "value": "Strong" if avg_sentiment > 0.3 else "Softening",
                "status_class": "up" if avg_sentiment > 0.3 else "down"
            })

        # Reinsurance pricing (look for rate change mentions)
        re_articles = [a for a in articles if a.business_line == "Reinsurance"]
        if re_articles:
            # Simplified: check category and sentiment
            pulse_items.append({
                "label": "Reinsurance Pricing",
                "value": aggregate_pricing_signal(re_articles),
                "status_class": determine_status_class(re_articles)
            })

        return pulse_items

def calculate_sentiment_score(articles: List[NewsArticle]) -> float:
    """Convert sentiment to numeric score."""
    sentiment_map = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
    scores = [sentiment_map.get(a.sentiment, 0.0) for a in articles if a.sentiment]
    return sum(scores) / len(scores) if scores else 0.0
```

### Pattern 4: Template Architecture for New Sections
**What:** Integrate new report sections into existing tabbed template
**When to use:** Adding cross-tab sections (appear once) vs per-tab sections
**Example:**
```jinja2
<!-- role_brief.html structure -->

<div class="confidential-banner">CONFIDENTIAL — FOR INTERNAL USE ONLY</div>

<div class="header">
  <!-- Existing header with Kevin Taylor attribution badge -->
  <div class="edition-tag">{{ edition_stats.source_count }} sources monitored • {{ edition_stats.article_count }} stories classified</div>
</div>

<!-- NEW: Market Pulse Bar (cross-tab section) -->
<div class="pulse-bar">
  {% for pulse_item in market_pulse %}
  <div class="pulse-item">
    <span class="pulse-dot {{ pulse_item.dot_class }}"></span>
    <span class="pulse-label">{{ pulse_item.label }}</span>
    <span class="pulse-value {{ pulse_item.status_class }}">{{ pulse_item.value }}</span>
  </div>
  {% endfor %}
</div>

<div class="container">

  <!-- TAB NAVIGATION (existing) -->
  <div class="tab-navigation">
    {% for role in ["Brokers", "Leadership", "Compliance", "Underwriting"] %}
    <button class="tab-button {% if loop.first %}active{% endif %}" onclick="showTab('{{ role }}')">
      {{ role }}
    </button>
    {% endfor %}
  </div>

  <!-- TAB CONTENT SECTIONS -->
  {% for role in ["Brokers", "Leadership", "Compliance", "Underwriting"] %}
  <div class="tab-content {% if loop.first %}active{% endif %}" id="tab-{{ role }}">
    <h2>{{ role }} Intelligence</h2>

    <!-- NEW: Per-Role Executive Summary (per-tab section) -->
    {% if executive_summaries[role] %}
    <div class="exec-summary">
      <h3>Executive Summary</h3>
      {% for paragraph in executive_summaries[role].summary_paragraphs %}
      <p>{{ paragraph }}</p>
      {% endfor %}
    </div>
    {% endif %}

    <!-- Existing: Article cards grouped by priority -->
    {% set role_articles = articles | selectattr('roles', 'containing', role) | list %}
    <!-- ... existing article rendering ... -->
  </div>
  {% endfor %}

  <!-- NEW: Cross-Tab Sections (appear after all tabs) -->

  <!-- Sector Heatmap -->
  <div class="heatmap">
    <h3>Sector Signal Map</h3>
    <div class="heatmap-grid">
      {% for cell in sector_heatmap %}
      <div class="heat-cell {{ cell.signal_class }}">
        <div class="heat-label">{{ cell.sector }}</div>
        <div class="heat-signal">{{ cell.signal }}</div>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- Entity Tracker -->
  <div class="entity-tracker">
    <h3>Entity Tracker — Companies in Today's Brief</h3>
    <div class="entity-grid">
      {% for entity in entity_tracker %}
      <div class="entity-item">
        <span class="entity-count">{{ entity.count }}</span>
        <div class="entity-name">{{ entity.name }}</div>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- What to Watch -->
  <div class="watch-section">
    <h3>What to Watch</h3>
    <div class="watch-grid">
      {% for item in what_to_watch.items %}
      <div class="watch-item">
        <h4>{{ item.title }}</h4>
        <p>{{ item.description }}</p>
        <span class="watch-timeframe">{{ item.timeframe }}</span>
      </div>
      {% endfor %}
    </div>
  </div>

</div>

<!-- FOOTER (existing, enhanced with stats) -->
<div class="footer">
  <div>{{ edition_stats.article_count }} stories • {{ edition_stats.source_count }} sources monitored • {{ entity_tracker|length }} entities tracked • {{ what_to_watch.items|length }} forward-looking signals</div>
  <div class="attribution">Kevin Taylor — Colleague Technology Services</div>
</div>
```

### Anti-Patterns to Avoid
- **AI over-use:** Don't call GPT-4o for simple counting/grouping (entity tracker, heatmap data) — pure Python is faster and cheaper
- **Template logic complexity:** Don't put aggregation logic in Jinja2 templates — pre-compute in Python, pass clean data structures
- **Single giant prompt:** Don't try to generate all AI content (4 role summaries + what-to-watch) in one call — separate calls give better role-specific context
- **Inline CSS in template:** Already using premailer for CSS inlining, don't manually inline styles in template code

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS inlining for email | Manual style attribute insertion | premailer (already installed) | Email client quirks, specificity issues |
| JSON schema validation | Manual dict checking | Pydantic models (already used) | Type safety, auto-documentation |
| Sentiment aggregation | Custom sentiment averaging | Collections.Counter + simple average | Built-in, readable, sufficient |
| HTML escaping | Manual string replacement | Jinja2 autoescape (default enabled) | Security, completeness |
| Date formatting | Manual strftime everywhere | Template filters + central format | Consistency, maintainability |

**Key insight:** Phase 4 doesn't need new libraries. The existing stack (Azure OpenAI, Jinja2, Pydantic, premailer) covers all requirements. Custom code should focus on domain logic (aggregation, AI prompts) not infrastructure.

## Common Pitfalls

### Pitfall 1: Token Waste on Aggregation
**What goes wrong:** Calling GPT-4o to count entities or calculate sector distributions
**Why it happens:** AI seems like the solution to all data problems
**How to avoid:** Use pure Python for deterministic operations (counting, sorting, grouping). Reserve AI for semantic tasks (summarization, insight extraction).
**Warning signs:** High token costs, slow report generation, non-deterministic aggregation results

### Pitfall 2: Template Data Structure Mismatch
**What goes wrong:** Template expects list of dicts but receives list of ORM objects, causing AttributeError
**Why it happens:** Mixing ORM query results with template rendering without transformation
**How to avoid:** Create explicit data transformation layer in reporter service. Convert ORM objects to dicts before passing to template.
**Warning signs:** AttributeError in template rendering, need for complex template logic

### Pitfall 3: AI Hallucination in Executive Summaries
**What goes wrong:** GPT-4o invents statistics or entities not in source articles
**Why it happens:** AI fills gaps in context with plausible-sounding content
**How to avoid:** Include full article summaries in prompt context. Use structured output schema to require specific fields (key_numbers must be from articles). Lower temperature (0.3-0.5) for factual content.
**Warning signs:** Numbers in summary don't match articles, entity names slightly wrong

### Pitfall 4: Per-Role vs Cross-Role Section Confusion
**What goes wrong:** Executive summary appears 4 times (once per tab) instead of unique per role
**Why it happens:** Misunderstanding template loop scope and variable scoping
**How to avoid:** Executive summaries are per-role (inside tab loop). Heatmap, entity tracker, what-to-watch are cross-role (outside tab loop). Use clear variable naming: `executive_summaries[role]` vs `sector_heatmap` (no role key).
**Warning signs:** Duplicate sections, same content across all tabs

### Pitfall 5: CSS Specificity Wars with Premailer
**What goes wrong:** Premailer inlines some styles but not others, creating visual inconsistencies
**Why it happens:** CSS specificity rules + premailer's inlining algorithm
**How to avoid:** Use simple selectors (.class not .parent .child .grandchild). Test premailer output in email client preview. Avoid !important unless necessary.
**Warning signs:** Styles work in browser but break in email clients

### Pitfall 6: JSON Parsing Errors from Database
**What goes wrong:** `json.loads(article.roles)` fails with JSONDecodeError
**Why it happens:** Database stores string "null" or empty string instead of JSON array
**How to avoid:** Defensive parsing with fallback: `json.loads(article.roles) if article.roles else []`
**Warning signs:** Intermittent crashes when processing articles, errors on specific articles

## Code Examples

Verified patterns from official sources and existing codebase:

### Reporter Service with AI Summary Generation
```python
# app/services/reporter.py (enhanced version)
from typing import List, Dict
from datetime import datetime
import json
from jinja2 import Environment, FileSystemLoader
from premailer import transform
from openai import AzureOpenAI

from app.models.news_article import NewsArticle
from app.schemas.report_context import ExecutiveSummary, WhatToWatch
from app.services.aggregator import ReportAggregator

class RoleReportService:
    """Enhanced reporter service with AI summary generation."""

    def __init__(self, azure_endpoint: str, api_key: str, deployment: str):
        # Existing Jinja2 setup
        self.env = Environment(
            loader=FileSystemLoader("app/templates"),
            autoescape=True
        )

        # Azure OpenAI client
        self.client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version="2024-08-01-preview"
        )
        self.deployment = deployment

        # Aggregator for data pre-processing
        self.aggregator = ReportAggregator()

    def generate_role_brief(
        self,
        articles: List[NewsArticle],
        report_date: datetime,
        company_name: str = "Marsh"
    ) -> str:
        """Generate complete HTML brief with AI summaries and aggregations."""

        # 1. Generate AI executive summaries (4 calls, one per role)
        executive_summaries = {}
        for role in ["Brokers", "Leadership", "Compliance", "Underwriting"]:
            executive_summaries[role] = self._generate_executive_summary(role, articles, report_date)

        # 2. Generate AI "What to Watch" (1 call, cross-role)
        what_to_watch = self._generate_what_to_watch(articles, report_date)

        # 3. Aggregate data for visualizations (pure Python)
        sector_heatmap = self.aggregator.aggregate_sector_heatmap(articles)
        entity_tracker = self.aggregator.aggregate_entity_tracker(articles, top_n=15)
        market_pulse = self.aggregator.aggregate_market_pulse(articles)

        # 4. Prepare articles for template (convert ORM to dict)
        prepared_articles = self._prepare_articles(articles)

        # 5. Build edition stats
        edition_stats = {
            "source_count": len(set(a.source_name for a in articles if a.source_name)),
            "article_count": len(articles),
            "entity_count": len(entity_tracker),
            "signal_count": len(what_to_watch.items)
        }

        # 6. Render template
        template = self.env.get_template('role_brief.html')
        context = {
            "articles": prepared_articles,
            "report_date": report_date,
            "company_name": company_name,
            "executive_summaries": executive_summaries,
            "what_to_watch": what_to_watch,
            "sector_heatmap": sector_heatmap,
            "entity_tracker": entity_tracker,
            "market_pulse": market_pulse,
            "edition_stats": edition_stats,
        }
        html = template.render(**context)

        # 7. Inline CSS for email compatibility
        html_inlined = transform(html)

        return html_inlined

    def _generate_executive_summary(
        self,
        role: str,
        articles: List[NewsArticle],
        report_date: datetime
    ) -> ExecutiveSummary:
        """Generate AI summary for specific role."""
        # Filter articles for this role
        role_articles = [
            a for a in articles
            if a.roles and role in json.loads(a.roles)
        ]

        if not role_articles:
            # Return empty summary if no articles for this role
            return ExecutiveSummary(
                summary_paragraphs=["No significant developments for this role today."],
                key_numbers=[],
                role_context=f"No {role}-relevant intelligence in today's edition."
            )

        # Sort by priority
        priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Monitor": 3}
        role_articles.sort(key=lambda a: priority_order.get(a.priority, 4))

        # Build article context (limit to top 20 to control token usage)
        article_context = "\n\n".join([
            f"[{a.priority}] {a.title}\n{a.summary}\n(Category: {a.category}, Impact: {a.impact_level}, Region: {a.region})"
            for a in role_articles[:20]
        ])

        prompt = f"""Generate an executive summary for {role} professionals based on today's insurance market intelligence.

Today's Date: {report_date.strftime('%d %B %Y')}
Role: {role}
Articles for this role: {len(role_articles)}

Article Summaries:
{article_context}

Write 2-3 concise paragraphs (150-250 words total) highlighting:
1. Most critical developments requiring {role}'s attention
2. Key numbers, dates, and entity names (use EXACT figures from articles)
3. Strategic implications and market signals relevant to {role}

Use professional but readable language. Emphasize actionable intelligence."""

        completion = self.client.beta.chat.completions.parse(
            model=self.deployment,
            messages=[
                {"role": "system", "content": "You are an insurance industry intelligence analyst writing executive summaries for senior professionals. Be concise, fact-based, and actionable."},
                {"role": "user", "content": prompt}
            ],
            response_format=ExecutiveSummary,
            temperature=0.4
        )

        return completion.choices[0].message.parsed

    def _generate_what_to_watch(
        self,
        articles: List[NewsArticle],
        report_date: datetime
    ) -> WhatToWatch:
        """Generate cross-role forward-looking analysis."""
        # Include high-priority and market trend articles
        relevant_articles = [
            a for a in articles
            if a.priority in ["Critical", "High"] or a.category == "Market Trends"
        ]

        article_context = "\n\n".join([
            f"{a.title}\n{a.summary}\n(Category: {a.category}, Timeframe indicators: {a.description[:200]})"
            for a in relevant_articles[:15]
        ])

        prompt = f"""Analyze today's intelligence for forward-looking signals that require monitoring.

Today's Date: {report_date.strftime('%d %B %Y')}
Relevant Articles: {len(relevant_articles)}

{article_context}

Identify 4-6 items to watch over the next 30-180 days. For each item:
- Provide a concise title (5-8 words)
- Explain what to watch and why (1-2 sentences)
- Specify WHEN this matters (e.g., "Next 30-60 days", "Q2 2026", "April renewals")
- Note which roles should monitor this

Focus on:
- Ongoing M&A transactions (due diligence, approvals, completion timelines)
- Regulatory changes with implementation dates
- Market renewal cycles (reinsurance, geographic markets)
- Emerging risks flagged by analysts or rating agencies
- Strategic trends with near-term inflection points"""

        completion = self.client.beta.chat.completions.parse(
            model=self.deployment,
            messages=[
                {"role": "system", "content": "You are a strategic intelligence analyst identifying forward-looking market signals for insurance professionals."},
                {"role": "user", "content": prompt}
            ],
            response_format=WhatToWatch,
            temperature=0.5
        )

        return completion.choices[0].message.parsed

    def _prepare_articles(self, articles: List[NewsArticle]) -> List[dict]:
        """Convert ORM objects to template-friendly dicts."""
        prepared = []
        for article in articles:
            # Parse JSON fields defensively
            roles = json.loads(article.roles) if article.roles else []
            entities = json.loads(article.entities) if article.entities else []

            article_dict = {
                'id': article.id,
                'title': article.title,
                'description': article.description,
                'source_url': article.source_url,
                'source_name': article.source_name,
                'published_at': article.published_at,
                'roles': roles,
                'priority': article.priority,
                'summary': article.summary,
                'sentiment': article.sentiment,
                'entities': entities,
                'impact_level': article.impact_level,
                'category': article.category,
                'region': article.region,
                'business_line': article.business_line,
            }
            prepared.append(article_dict)
        return prepared
```

### Pydantic Schemas for AI Outputs
```python
# app/schemas/report_context.py (new file)
from typing import List
from pydantic import BaseModel, Field

class ExecutiveSummary(BaseModel):
    """Schema for role-specific executive summary."""
    summary_paragraphs: List[str] = Field(
        description="2-3 paragraphs of executive summary for this role",
        min_items=2,
        max_items=3
    )
    key_numbers: List[str] = Field(
        description="3-5 highlighted numbers/statistics from articles (with context)",
        max_items=5
    )
    role_context: str = Field(
        description="One-sentence context about why this matters to this role"
    )

class WhatToWatchItem(BaseModel):
    """Single forward-looking item."""
    title: str = Field(description="Concise headline (5-8 words)")
    description: str = Field(description="1-2 sentence explanation")
    timeframe: str = Field(description="When this matters (e.g., 'Next 30-60 days', 'Q2 2026')")
    impact_roles: List[str] = Field(description="Which roles should monitor this")

class WhatToWatch(BaseModel):
    """Cross-role forward-looking analysis."""
    items: List[WhatToWatchItem] = Field(
        description="4-6 forward-looking items to monitor",
        min_items=4,
        max_items=6
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual template data prep | Pydantic schemas + structured outputs | Aug 2024 | Guaranteed schema compliance, no manual validation |
| Single AI call for all content | Separate calls per concern | 2025+ | Better role-specific context, parallel execution possible |
| Template-based aggregation | Service-layer pure Python | Always best practice | Performance, testability, separation of concerns |
| Manual CSS inlining | Premailer automated | 2015+ | Email compatibility, maintainability |

**Deprecated/outdated:**
- OpenAI completion API (text, not chat): Replaced by chat completions with structured outputs
- Jinja2 manual escaping: autoescape=True is default and secure
- Inline style attributes in template: premailer handles this automatically

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal prompt length for executive summaries**
   - What we know: Azure OpenAI has 128K context window, structured outputs work with long prompts
   - What's unclear: Whether including all 50+ articles or limiting to top 20 produces better summaries
   - Recommendation: Start with top 20 per role (sorted by priority), validate quality, expand if needed

2. **Market pulse bar data sources**
   - What we know: Pure Python aggregation needed, prototype shows 5 specific indicators (US P&C, Reinsurance Pricing, Cat Losses, Moody's Outlook, M&A Activity)
   - What's unclear: Whether these indicators can be reliably computed from article metadata alone or need manual configuration
   - Recommendation: Start with simple sentiment aggregation by business_line + region, refine with domain-specific rules based on category

3. **Entity deduplication for tracker**
   - What we know: Entity names normalized during classification (Phase 3)
   - What's unclear: Whether "Marsh McLennan" and "Marsh" will be properly deduplicated in entity counts
   - Recommendation: Trust Phase 3 normalization initially, add deduplication logic if needed after testing

4. **Cross-tab section placement**
   - What we know: Heatmap, entity tracker, what-to-watch should appear once (not per tab)
   - What's unclear: Whether to place before tabs (executive context) or after tabs (detailed appendix)
   - Recommendation: Place after tabs based on prototype structure (header → pulse bar → tabs → cross-tab sections → footer)

## Consolidation Analysis

### Original 10 Plans Grouping

**Group A: Data Logic (Cannot Consolidate - Different Domains)**
- 04-01: Role filtering + priority ranking (query logic)
- 04-02: Executive summary generation (GPT-4o per role)
- 04-03: Sector heatmap (aggregation logic)
- 04-04: Entity tracker (aggregation logic)
- 04-05: "What to Watch" (GPT-4o cross-role)
- 04-06: Market pulse bar (aggregation logic)

**Group B: Template/CSS (CAN Consolidate - Same Domain)**
- 04-07: Article card chips (template enhancement)
- 04-08: Marsh branding CSS (CSS enhancement)
- 04-09: Mobile responsive (CSS enhancement)
- 04-10: Author attribution (template enhancement)

### Recommended Consolidation

**New Plan Structure (7 plans instead of 10):**

1. **04-01: Role Filtering & Priority Ranking** (query logic, supports all other plans)
2. **04-02: Executive Summary Generation** (GPT-4o per role, Pydantic schema)
3. **04-03: Sector Heatmap Component** (pure Python aggregation)
4. **04-04: Entity Tracker Component** (pure Python aggregation)
5. **04-05: "What to Watch" Section** (GPT-4o cross-role analysis)
6. **04-06: Market Pulse Bar** (pure Python aggregation, top of page)
7. **04-07: Template Enhancement & Branding** (CONSOLIDATED: article chips + Marsh CSS + mobile responsive + attribution)

**Rationale for consolidation:**
- Plans 04-07 through 04-10 all modify the same template file (role_brief.html)
- No data logic dependencies between them
- All involve CSS and HTML structure changes
- Can be implemented and tested together as "final template polish"
- Reduces context switching between template and service code

**Dependencies after consolidation:**
- Wave 1: 04-01 (foundation for all other plans)
- Wave 2: 04-02, 04-03, 04-04, 04-05, 04-06 (parallel - independent data components)
- Wave 3: 04-07 (depends on all Wave 2 plans for complete template integration)

## Sources

### Primary (HIGH confidence)
- [Azure OpenAI Structured Outputs Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs) - GPT-4o structured outputs feature
- [OpenAI Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs) - Pydantic schema integration
- [Azure OpenAI Blog: GPT-4o-2024-08-06](https://techcommunity.microsoft.com/t5/ai-azure-ai-services-blog/introducing-gpt-4o-2024-08-06-api-with-structured-outputs-on/ba-p/4232684) - Structured outputs announcement
- Existing codebase (C:\BrasilIntel\mdinsights\app\services\reporter.py, classifier.py, schemas\classification.py) - Established patterns

### Secondary (MEDIUM confidence)
- [Jinja2 Templating Guide - Better Stack](https://betterstack.com/community/guides/scaling-python/jinja-templating/) - Template best practices
- [Real Python Jinja Primer](https://realpython.com/primer-on-jinja-templating/) - Data passing patterns
- Prototype HTML (C:\BrasilIntel\RefChyt\prototype_daily_intelligence_brief.html) - Visual requirements

### Tertiary (LOW confidence)
- Heatmap visualization libraries (heatmap.js, Heat.js) - Not needed for this phase (using pure CSS grid)
- Pandas aggregation - Over-engineered for simple counting/grouping

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use, proven patterns
- Architecture: HIGH - Clear separation of concerns (AI calls, aggregation, template rendering)
- Pitfalls: HIGH - Based on codebase analysis and Azure OpenAI documentation
- Consolidation: HIGH - Template/CSS work clearly separable from data logic

**Research date:** 2026-02-07
**Valid until:** 2026-03-07 (30 days - stable technologies, no fast-moving APIs)
