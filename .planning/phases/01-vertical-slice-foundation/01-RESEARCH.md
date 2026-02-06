# Phase 1: Vertical Slice Foundation - Research

**Researched:** 2026-02-06
**Domain:** Global insurance/reinsurance news intelligence with AI role classification
**Confidence:** HIGH

## Summary

Phase 1 establishes end-to-end architecture proof-of-concept for MDInsights by implementing a complete pipeline from single news source → AI classification → role-based HTML brief. This phase reuses proven patterns from BrasilIntel (v1.0 shipped) with one critical difference: instead of status-based grouping (Critical/Watch/Monitor), MDInsights uses role-based routing (Brokers/Leadership/Compliance/Underwriting) where each article can belong to multiple roles.

The vertical slice validates: (1) Apify scraping → SQLite storage pattern, (2) Azure OpenAI GPT-4o structured output for multi-role classification, (3) Jinja2 template rendering with role-based filtering, (4) Microsoft Graph email delivery, (5) manual trigger via FastAPI endpoint. Success means a working demo showing the same article appearing in multiple role-specific briefs.

**Primary recommendation:** Start with Reinsurance News as the test source (clean structured data, well-formatted articles, reliable daily updates). Use Azure OpenAI structured outputs with Pydantic model returning `List[str]` for roles. Implement role-based HTML template with CSS-only sections (email clients don't support JavaScript tabs). Focus on proving the classification → routing → delivery pattern before scaling to 18+ sources.

## Standard Stack

The established libraries/tools for this domain — directly inherited from BrasilIntel v1.0:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11+ | Runtime | BrasilIntel proven; async support; Azure SDK compatibility |
| FastAPI | 0.115+ | API framework | BrasilIntel v1.0; typed async APIs; automatic validation |
| SQLite | 3.45+ | Database | BrasilIntel v1.0; zero config; sufficient for single deployment |
| Apify SDK | 2.0+ | Web scraping | BrasilIntel v1.0; proven for news collection; handles rate limiting |
| Azure OpenAI SDK | 2.16+ | LLM classification | BrasilIntel v1.0; official SDK; structured output support |
| Microsoft Graph SDK | 1.0+ | Email delivery | BrasilIntel v1.0; modern M365 API; replaces deprecated SMTP |
| Jinja2 | 3.1+ | HTML templating | BrasilIntel v1.0; industry standard; email-safe rendering |
| Pydantic | 2.11+ | Data validation | BrasilIntel v1.0; structured output schemas; 5-10x faster than v1 |
| SQLAlchemy | 2.0+ | ORM | BrasilIntel v1.0; async support; type-safe queries |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 24.4+ | Structured logging | BrasilIntel v1.0; production observability; JSON output |
| HTTPX | 1.0+ | HTTP client | BrasilIntel v1.0; async; HTTP/2; connection pooling |
| APScheduler | 3.10+ | Task scheduling | Phase 5 only; BrasilIntel v1.0; manual trigger for Phase 1 |
| premailer | 3.10+ | CSS inlining | Email template rendering; ensures email client compatibility |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLite | PostgreSQL | More complexity, unnecessary for single deployment <1M rows |
| Apify | Scrapy/BeautifulSoup | More maintenance, no proxy rotation, rate limiting complexity |
| Graph API | SMTP | Deprecated auth, worse deliverability, no delivery confirmation |
| Jinja2 | React/Vue | Frontend build complexity, unnecessary for server-rendered email |

**Installation:**
```bash
pip install fastapi==0.115.0 uvicorn[standard] sqlalchemy pydantic==2.11.0
pip install openai==2.16.0 apify-client msgraph-sdk
pip install jinja2 premailer structlog httpx
```

## Architecture Patterns

### Recommended Project Structure

Reuse BrasilIntel's proven structure with role-specific adaptations:

```
mdinsights/
├── app/
│   ├── models/
│   │   ├── news_article.py    # Article with role tags (not status)
│   │   ├── source.py           # News sources (18+ eventually)
│   │   └── run.py              # Pipeline execution tracking
│   ├── services/
│   │   ├── collector.py        # Apify scraping coordinator
│   │   ├── sources/
│   │   │   ├── base.py         # Abstract source interface
│   │   │   └── reinsurance_news.py  # Phase 1 test source
│   │   ├── classifier.py       # Azure OpenAI role classification
│   │   ├── reporter.py         # Jinja2 HTML generation with role filtering
│   │   └── emailer.py          # Microsoft Graph delivery
│   ├── schemas/
│   │   ├── classification.py   # Pydantic models for structured output
│   │   └── report.py           # Report context models
│   ├── routers/
│   │   └── admin.py            # Manual trigger endpoint
│   ├── templates/
│   │   └── role_brief.html     # Single template with role filtering
│   ├── database.py             # SQLAlchemy setup (from BrasilIntel)
│   ├── config.py               # Settings (from BrasilIntel pattern)
│   └── main.py                 # FastAPI app
├── data/                       # SQLite database
└── .env                        # Azure credentials
```

### Pattern 1: Multi-Role Classification with Structured Outputs

**What:** Use Azure OpenAI structured outputs to classify each article with multiple audience roles simultaneously.

**When to use:** Every article classification in Phase 1 — core differentiator from BrasilIntel's single-status approach.

**Key difference from BrasilIntel:** BrasilIntel uses single status field (`status = "Critical" | "Watch" | "Monitor" | "Stable"`). MDInsights needs array of roles where one article can have multiple values: `roles = ["Brokers", "Leadership", "Underwriting"]`.

**Example Pydantic model:**
```python
from pydantic import BaseModel, Field
from typing import List, Literal

RoleType = Literal["Brokers", "Leadership", "Compliance", "Underwriting"]

class ArticleClassification(BaseModel):
    """Structured output for multi-role classification."""
    roles: List[RoleType] = Field(
        description="Audience roles this article is relevant for. Can be multiple."
    )
    priority: Literal["Critical", "High", "Medium", "Monitor"] = Field(
        description="Urgency/importance level for decision-making"
    )
    summary: str = Field(
        description="2-3 sentence summary highlighting key points"
    )
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="Overall tone and market impact sentiment"
    )

# Usage with Azure OpenAI
response = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",  # Structured output support
    messages=[
        {"role": "system", "content": ROLE_CLASSIFICATION_PROMPT},
        {"role": "user", "content": article_content}
    ],
    response_format=ArticleClassification
)
classification = response.choices[0].message.parsed
# classification.roles == ["Brokers", "Leadership"] (example)
```

**Source:** [Azure OpenAI Structured Outputs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs) — official Microsoft documentation confirming array support in structured outputs.

### Pattern 2: Role-Based Template Filtering with Jinja2

**What:** Single Jinja2 template generates different HTML outputs based on `target_role` parameter, filtering articles to show only relevant items.

**When to use:** Report generation in Phase 1 — one template serves all four role-specific briefs.

**Key insight:** Email clients don't support JavaScript, so "clickable tabs" in prototype aren't practical for email delivery. Instead, generate separate email per role with pre-filtered content.

**Example template structure:**
```jinja2
{# templates/role_brief.html #}
<!DOCTYPE html>
<html>
<head>
    <title>{{ company_name }} Intelligence Brief — {{ target_role }}</title>
    {# Marsh branding CSS from prototype #}
</head>
<body>
    <div class="header">
        <h1>{{ company_name }} Intelligence Brief</h1>
        <p class="subtitle">{{ target_role }} Edition — {{ report_date.strftime('%B %d, %Y') }}</p>
    </div>

    <div class="container">
        {# Executive summary #}
        <div class="executive-summary">
            <h2>Your {{ target_role }} Intelligence Summary</h2>
            <p>{{ ai_summary }}</p>
        </div>

        {# Filter articles by target role #}
        {% for article in articles %}
            {% if target_role in article.roles %}
            <div class="story-card priority-{{ article.priority|lower }}">
                <div class="story-header">
                    <div class="priority-indicator">
                        {% if article.priority == "Critical" %}🔴{% endif %}
                        {% if article.priority == "High" %}🟠{% endif %}
                    </div>
                    <div class="story-title-block">
                        <h3 class="story-title">{{ article.title }}</h3>
                        <div class="story-meta">
                            <span class="source-tag">{{ article.source_name }}</span>
                            <span class="priority-badge badge-{{ article.priority|lower }}">
                                {{ article.priority }}
                            </span>
                        </div>
                    </div>
                </div>
                <div class="story-body">
                    <p>{{ article.summary }}</p>
                </div>
            </div>
            {% endif %}
        {% endfor %}
    </div>
</body>
</html>
```

**Source:** BrasilIntel `app/templates/report_professional.html` — proven Jinja2 pattern for status-based filtering, adapted for role filtering.

### Pattern 3: Database Schema for Multi-Role Articles

**What:** SQLite schema storing articles with many-to-many relationship to roles via JSON array column (SQLite limitation workaround).

**When to use:** Phase 1 database setup — enables role-based filtering in queries.

**BrasilIntel adaptation:**
```python
# BrasilIntel: Single status column
class NewsItem(Base):
    status = Column(String(50), nullable=True)  # "Critical" | "Watch" | ...

# MDInsights: Multiple roles via JSON array
class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"))

    # Content fields
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_name = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Multi-role classification (JSON array for SQLite)
    roles = Column(JSON, nullable=True)  # ["Brokers", "Leadership", ...]
    priority = Column(String(50), nullable=True)  # "Critical" | "High" | ...
    summary = Column(Text, nullable=True)  # AI-generated summary
    sentiment = Column(String(20), nullable=True)  # positive/negative/neutral

    created_at = Column(DateTime, default=datetime.utcnow)
```

**Query pattern for role filtering:**
```python
from sqlalchemy import func

# Get all articles for "Brokers" role
articles = session.query(NewsArticle).filter(
    func.json_extract(NewsArticle.roles, '$') # SQLite JSON support
).all()

# Filter in Python (simpler for Phase 1)
articles = session.query(NewsArticle).all()
brokers_articles = [a for a in articles if "Brokers" in (a.roles or [])]
```

**Source:** BrasilIntel `app/models/news_item.py` — adapted with JSON column for role array.

### Pattern 4: Apify Single-Source Integration

**What:** Start with one well-structured Apify actor (or custom scraper) to validate end-to-end flow.

**When to use:** Phase 1 only — prove pipeline before scaling to 18+ sources.

**Recommended test source:** Reinsurance News (https://www.reinsurancene.ws/)
- **Why:** Clean structured HTML, reliable daily updates, covers global reinsurance market, well-formatted articles with clear titles/descriptions
- **Alternative:** Insurance Journal (https://www.insurancejournal.com/) — also reliable, US-focused

**Apify integration pattern (from BrasilIntel):**
```python
from apify_client import ApifyClient
from typing import List, Dict
import structlog

logger = structlog.get_logger()

class ApifyCollector:
    """Coordinator for Apify-based news scraping."""

    def __init__(self, apify_token: str):
        self.client = ApifyClient(apify_token)

    async def scrape_reinsurance_news(self, limit: int = 20) -> List[Dict]:
        """
        Scrape latest articles from Reinsurance News.

        Phase 1: Use generic Web Scraper actor or custom actor.
        """
        try:
            # Option A: Generic Web Scraper actor
            run = self.client.actor("apify/web-scraper").call(
                run_input={
                    "startUrls": [{"url": "https://www.reinsurancene.ws/"}],
                    "pageFunction": """
                        async function pageFunction(context) {
                            const articles = [];
                            const $ = context.jQuery;

                            $('.article-item').each((i, elem) => {
                                articles.push({
                                    title: $(elem).find('h2').text().trim(),
                                    description: $(elem).find('.excerpt').text().trim(),
                                    url: $(elem).find('a').attr('href'),
                                    published_at: $(elem).find('.date').text().trim()
                                });
                            });

                            return articles;
                        }
                    """,
                    "maxRequestsPerCrawl": limit
                }
            )

            # Get results from dataset
            dataset = self.client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())

            logger.info("apify_scrape_complete",
                       source="reinsurance_news",
                       count=len(items))
            return items

        except Exception as e:
            logger.error("apify_scrape_failed",
                        source="reinsurance_news",
                        error=str(e))
            raise
```

**Phase 1 simplification:** Don't build generic multi-source framework yet. Hard-code Reinsurance News scraping to prove the pattern. Expand to 18+ sources in Phase 2.

**Source:** [Apify Actors](https://apify.com/actors) — platform documentation; [Apify Review 2026](https://hackceleration.com/apify-review/) — real-world performance data.

### Anti-Patterns to Avoid

1. **Building clickable tabs with JavaScript for email** → Email clients block JavaScript; prototype's tabs won't work in email; use separate email per role instead

2. **Trying to create one unified HTML with hidden sections** → Email client CSS support varies; hidden content may still show; cleaner to send role-specific HTML

3. **Using status-based grouping like BrasilIntel** → MDInsights value is role-based routing; don't copy BrasilIntel's status pattern

4. **Scraping 18 sources in Phase 1** → Validate pipeline with one source first; parallel scraping complexity comes in Phase 2

5. **Complex database schema with join tables** → SQLite JSON column sufficient for Phase 1; premature optimization adds complexity

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Web scraping infrastructure | Custom requests + BeautifulSoup | Apify SDK | Proxy rotation, rate limiting, CAPTCHA solving, anti-bot evasion — 65.8% report increased anti-bot complexity in 2026 |
| Email HTML rendering | Manual HTML + inline CSS | Jinja2 + premailer | Email client compatibility (200+ clients), CSS inlining, template inheritance |
| Email delivery | SMTP with smtplib | Microsoft Graph SDK | Deprecated auth, better deliverability, delivery confirmation, corporate compliance |
| Structured LLM output | Parse JSON with try/except | Azure OpenAI structured outputs | 100% schema compliance vs ~70-80% with JSON mode, automatic validation |
| Database session management | Global session object | FastAPI dependency injection | Thread safety, automatic cleanup, proper transaction boundaries |

**Key insight:** BrasilIntel already solved these problems. Reuse patterns, don't rebuild.

**Source:** [State of Web Scraping 2026](https://blog.apify.com/web-scraping-report-2026/) — anti-bot complexity data; [OpenAI Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/) — 100% reliability claim.

## Common Pitfalls

### Pitfall 1: Assuming Email Supports Interactive JavaScript Tabs

**What goes wrong:** Prototype HTML (`RefChyt/prototype_daily_intelligence_brief.html`) shows beautiful clickable tabs. Developers try to use same HTML for email. Email clients strip JavaScript. Tabs don't work. Users see broken layout.

**Why it happens:** Prototype is web page, not email. Gmail, Outlook, Apple Mail all block `<script>` tags for security. Even CSS-only tabs using `:checked` pseudo-class don't work in Gmail (support dropped October 2016).

**How to avoid:**
1. Generate **separate email per role** — "Brokers Edition", "Leadership Edition", etc.
2. Each email contains pre-filtered articles for that role only
3. Use static HTML sections, not tabs or accordions
4. Test with premailer for CSS inlining before delivery

**Warning signs:**
- Developer copies prototype HTML directly for email template
- Template includes `<input type="checkbox">` or `:target` CSS selectors
- No email client testing (Litmus/Email on Acid)

**Sources:**
- [Interactive Tabs for Email](https://freshinbox.com/blog/interactive-tabs-for-email/) — explains CSS-only tabs and limitations
- [CSS3 Accordion in Email](https://litmus.com/community/discussions/1104-css3-accordion-in-email) — Gmail support issues documented

### Pitfall 2: Role Classification Produces Single Role Instead of Array

**What goes wrong:** GPT-4o returns single role ("Brokers") when article is relevant to multiple audiences ("Brokers" + "Leadership"). Result: Leadership team misses important M&A news because it was only tagged for Brokers.

**Why it happens:**
1. Prompt doesn't explicitly request multiple roles
2. Pydantic model uses `role: str` instead of `roles: List[str]`
3. No validation that high-priority articles get multiple roles

**How to avoid:**
1. **Explicit prompt instruction:** "Identify ALL relevant audience roles. Most articles apply to 2-3 roles. Be generous with role assignment — better to over-include than miss an audience."
2. **Pydantic model enforces list:** `roles: List[RoleType]` not `role: RoleType`
3. **Validation rule:** High/Critical priority articles should typically have 2+ roles
4. **Test with edge cases:** M&A article (Brokers + Leadership), regulatory change (Compliance + Leadership + Underwriting)

**Warning signs:**
- Article about major insurer acquisition only appears in Brokers brief
- Compliance team complains they're missing regulatory news
- High percentage of articles have exactly 1 role (should be 40-60% with multiple)

**Example prompt snippet:**
```
Identify ALL audience roles relevant to this article (can be multiple):
- Brokers: Market positioning, competitor moves, pricing trends, capacity shifts
- Leadership: M&A activity, financial results, strategic signals, market forecasts
- Compliance: Regulatory developments, legal changes, coverage gaps, policy reforms
- Underwriting: Loss trends, catastrophe events, reserve adequacy, rate movements

IMPORTANT: Most significant articles apply to multiple roles. For example:
- Major insurer acquisition → Brokers (competitor intelligence) + Leadership (strategic signal)
- New regulatory requirement → Compliance (rule changes) + Leadership (strategic impact)
- Catastrophic loss event → Underwriting (loss trends) + Leadership (financial impact)

Return an ARRAY of roles, not a single value.
```

**Source:** [Azure OpenAI Structured Outputs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs) — confirms array support in structured outputs.

### Pitfall 3: SQLite JSON Column Queries Are Slow or Broken

**What goes wrong:** Developer stores roles as JSON array (`["Brokers", "Leadership"]`) but can't efficiently query "give me all articles for Brokers role". Queries are slow or require loading all records into Python for filtering.

**Why it happens:** SQLite JSON support is limited compared to PostgreSQL. `json_extract()` function exists but syntax is tricky. Developers default to loading all records and filtering in Python (works for Phase 1, breaks at scale).

**How to avoid:**
1. **Phase 1: Python filtering is acceptable** — <100 articles/day, performance not an issue
2. **Phase 2+: Add indexed role columns** — `has_brokers BOOLEAN`, `has_leadership BOOLEAN` for efficient filtering
3. **Alternative: Use simple string with delimiters** — `roles = "Brokers|Leadership|Underwriting"` enables `LIKE '%Brokers%'` queries
4. **Long-term: Migrate to PostgreSQL** — proper JSON array support with GIN indexes

**Working query patterns:**

```python
# Option A: Python filtering (Phase 1)
all_articles = session.query(NewsArticle).all()
brokers_articles = [a for a in all_articles if "Brokers" in (a.roles or [])]

# Option B: SQLite JSON (works but slow)
from sqlalchemy import func, text
articles = session.query(NewsArticle).filter(
    text("json_extract(roles, '$') LIKE '%Brokers%'")
).all()

# Option C: Indexed boolean columns (Phase 2+)
class NewsArticle(Base):
    roles_json = Column(JSON)  # Keep for display
    has_brokers = Column(Boolean, index=True)
    has_leadership = Column(Boolean, index=True)
    has_compliance = Column(Boolean, index=True)
    has_underwriting = Column(Boolean, index=True)

articles = session.query(NewsArticle).filter(
    NewsArticle.has_brokers == True
).all()
```

**Warning signs:**
- Query time >1 second for <1000 articles
- Full table scans in EXPLAIN QUERY PLAN
- Memory usage spikes when filtering by role

**Source:** SQLite JSON documentation; BrasilIntel schema design patterns.

### Pitfall 4: Forgetting to Test Email Rendering Across Clients

**What goes wrong:** Beautiful HTML renders perfectly in browser. Send via email → broken layout in Outlook, missing styles in Gmail, images blocked in Apple Mail.

**Why it happens:** Email clients use ancient rendering engines (Outlook uses Microsoft Word engine!). CSS support varies wildly. Inline styles required. External stylesheets ignored. Media queries limited.

**How to avoid:**
1. **Use premailer library** — automatically inlines CSS before sending
2. **Test in Litmus or Email on Acid** — preview across 90+ email clients
3. **Follow email HTML best practices** — tables for layout, inline styles, no floats/flexbox/grid
4. **Use Marsh's proven template** — BrasilIntel's `report_professional.html` already tested in M365
5. **Send test emails to yourself** — check in Outlook Desktop, Outlook Web, Gmail, Apple Mail

**Working premailer integration:**
```python
from premailer import transform

def render_email_html(template_name: str, context: dict) -> str:
    """Render Jinja2 template and inline CSS for email compatibility."""
    template = jinja_env.get_template(template_name)
    html = template.render(**context)

    # Inline CSS for email clients
    inlined_html = transform(html)
    return inlined_html
```

**Warning signs:**
- Testing only in Chrome browser, not actual email clients
- External `<link>` stylesheets instead of `<style>` blocks
- Complex CSS (flexbox, grid, custom fonts)
- No premailer or equivalent inlining tool

**Source:** [HTML and CSS in Emails: What Works in 2026?](https://designmodo.com/html-css-emails/) — compatibility guide; BrasilIntel proven template patterns.

## Code Examples

Verified patterns from sister project and official sources:

### Azure OpenAI Structured Output for Role Classification

```python
"""
Classification service using Azure OpenAI structured outputs.
Adapted from BrasilIntel classifier.py with role-based modifications.
"""
from openai import AzureOpenAI
from pydantic import BaseModel, Field
from typing import List, Literal
import structlog

logger = structlog.get_logger()

# Role and priority types
RoleType = Literal["Brokers", "Leadership", "Compliance", "Underwriting"]
PriorityType = Literal["Critical", "High", "Medium", "Monitor"]
SentimentType = Literal["positive", "negative", "neutral"]

class ArticleClassification(BaseModel):
    """
    Structured output schema for multi-role article classification.

    Ensures GPT-4o returns consistent, validated JSON matching this schema.
    """
    roles: List[RoleType] = Field(
        description="All relevant audience roles (can be multiple). "
                    "Brokers: market intelligence, competitor moves. "
                    "Leadership: M&A, financials, strategy. "
                    "Compliance: regulatory, legal, policy. "
                    "Underwriting: losses, rates, risk assessment."
    )
    priority: PriorityType = Field(
        description="Urgency level: Critical (immediate action), "
                    "High (monitor closely), Medium (informational), "
                    "Monitor (background awareness)"
    )
    summary: str = Field(
        description="2-3 sentence summary highlighting key points and implications"
    )
    sentiment: SentimentType = Field(
        description="Overall market sentiment: positive (opportunity), "
                    "negative (threat/loss), neutral (factual)"
    )

CLASSIFICATION_PROMPT = """You are an insurance industry analyst classifying news articles for different Marsh audiences.

Identify ALL relevant roles for each article:
- **Brokers**: Competitor intelligence, market positioning, pricing trends, capacity shifts, broker M&A
- **Leadership**: Major M&A, financial results, strategic market shifts, industry forecasts, executive changes
- **Compliance**: Regulatory changes, legal developments, coverage gaps, policy reforms, sanctions
- **Underwriting**: Catastrophe losses, combined ratios, reserve adequacy, rate movements, risk trends

IMPORTANT: Most significant articles apply to multiple roles. Examples:
- Major insurer acquisition → Brokers (market impact) + Leadership (strategic signal)
- New regulatory requirement → Compliance (rules) + Leadership (strategy) + Underwriting (risk)
- Catastrophic loss → Underwriting (reserves) + Leadership (financials)

Be generous with role assignment — better to over-include than miss an audience.

Priority levels:
- Critical: Immediate action required, major market event, regulatory deadline
- High: Monitor closely, significant but not urgent, emerging trend
- Medium: Informational, routine developments, background context
- Monitor: Low-impact, peripheral news, routine updates

Sentiment:
- Positive: Growth, opportunities, favorable outcomes
- Negative: Losses, threats, adverse developments
- Neutral: Factual reporting, balanced analysis
"""

class RoleClassificationService:
    """
    Classifies news articles for multiple audience roles using Azure OpenAI.

    Uses structured outputs to guarantee schema compliance.
    """

    def __init__(self, endpoint: str, api_key: str, deployment: str):
        """Initialize Azure OpenAI client."""
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-08-01-preview"  # Structured outputs support
        )
        self.deployment = deployment

    async def classify_article(
        self,
        title: str,
        description: str,
        source: str
    ) -> ArticleClassification:
        """
        Classify single article for multiple roles.

        Returns structured ArticleClassification with guaranteed schema.
        """
        user_message = f"""
Source: {source}
Title: {title}
Description: {description}

Classify this article for relevant audiences.
"""

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                response_format=ArticleClassification,
                temperature=0.3  # Lower temperature for consistent classification
            )

            classification = response.choices[0].message.parsed

            logger.info(
                "article_classified",
                title=title[:50],
                roles=classification.roles,
                priority=classification.priority,
                sentiment=classification.sentiment
            )

            return classification

        except Exception as e:
            logger.error("classification_failed", title=title[:50], error=str(e))
            raise
```

**Source:** [Azure OpenAI Structured Outputs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs); BrasilIntel `app/services/classifier.py` adapted for role classification.

### Jinja2 Template with Role Filtering

```jinja2
{# templates/role_brief.html - Single template serves all roles with filtering #}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ company_name }} Intelligence Brief — {{ target_role }}</title>
    <style>
        /* Marsh branding from prototype */
        :root {
            --marsh-blue: #00263e;
            --marsh-light-blue: #0077c8;
            --alert-red: #dc3545;
            --alert-orange: #fd7e14;
            --success-green: #28a745;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
            margin: 0;
            padding: 0;
        }

        .header {
            background: linear-gradient(135deg, var(--marsh-blue) 0%, #005a87 100%);
            color: white;
            padding: 40px 60px;
        }

        .header h1 {
            font-size: 2em;
            font-weight: 300;
            margin: 0 0 10px 0;
        }

        .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px 20px;
        }

        .story-card {
            background: white;
            border-radius: 8px;
            margin-bottom: 20px;
            padding: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }

        .story-title {
            color: var(--marsh-blue);
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .story-meta {
            font-size: 0.85em;
            color: #666;
            margin-bottom: 15px;
        }

        .priority-critical { border-left: 4px solid var(--alert-red); }
        .priority-high { border-left: 4px solid var(--alert-orange); }
        .priority-medium { border-left: 4px solid var(--marsh-light-blue); }
        .priority-monitor { border-left: 4px solid var(--success-green); }

        .summary {
            color: #444;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ company_name }} Intelligence Brief</h1>
        <p class="subtitle">{{ target_role }} Edition — {{ report_date.strftime('%B %d, %Y') }}</p>
    </div>

    <div class="container">
        {# Priority sections #}
        {% for priority in ["Critical", "High", "Medium", "Monitor"] %}
            {% set priority_articles = [] %}
            {% for article in articles %}
                {% if target_role in article.roles and article.priority == priority %}
                    {% do priority_articles.append(article) %}
                {% endif %}
            {% endfor %}

            {% if priority_articles %}
            <h2 style="color: var(--marsh-blue); margin: 30px 0 20px;">
                {{ priority }} Priority ({{ priority_articles|length }})
            </h2>

            {% for article in priority_articles %}
            <div class="story-card priority-{{ priority|lower }}">
                <h3 class="story-title">{{ article.title }}</h3>
                <div class="story-meta">
                    <span>{{ article.source_name }}</span>
                    {% if article.published_at %}
                    <span> • {{ article.published_at.strftime('%b %d, %Y') }}</span>
                    {% endif %}
                    <span> • {{ article.sentiment|capitalize }}</span>
                </div>
                <p class="summary">{{ article.summary }}</p>
                {% if article.source_url %}
                <p style="margin-top: 10px;">
                    <a href="{{ article.source_url }}"
                       style="color: var(--marsh-light-blue); text-decoration: none;">
                        Read full article →
                    </a>
                </p>
                {% endif %}
            </div>
            {% endfor %}
            {% endif %}
        {% endfor %}

        {# Footer attribution #}
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;
                    color: #666; font-size: 0.85em; text-align: center;">
            <p>Generated by Kevin Taylor, Colleague Technology Services</p>
            <p style="margin-top: 5px;">
                Powered by Azure OpenAI • Delivered via Microsoft Graph
            </p>
        </div>
    </div>
</body>
</html>
```

**Source:** BrasilIntel `app/templates/report_professional.html` adapted for role filtering; prototype styling from `RefChyt/prototype_daily_intelligence_brief.html`.

### Report Generation with Role Filtering

```python
"""
Report service for role-specific HTML generation.
Adapted from BrasilIntel reporter.py with multi-role support.
"""
from jinja2 import Environment, FileSystemLoader
from premailer import transform
from pathlib import Path
from datetime import datetime
from typing import List
import structlog

logger = structlog.get_logger()

class RoleReportService:
    """
    Generates role-specific HTML briefs from classified articles.

    Key difference from BrasilIntel: Filters by role instead of status.
    """

    def __init__(self):
        """Initialize Jinja2 environment."""
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )

    def generate_role_brief(
        self,
        target_role: str,
        articles: List[dict],
        report_date: datetime,
        company_name: str = "Marsh"
    ) -> str:
        """
        Generate HTML brief for specific role with filtered articles.

        Args:
            target_role: "Brokers" | "Leadership" | "Compliance" | "Underwriting"
            articles: All classified articles (will be filtered by role)
            report_date: Date for report header
            company_name: Company name for branding

        Returns:
            HTML string with inlined CSS (email-safe)
        """
        # Load template
        template = self.env.get_template("role_brief.html")

        # Render with role filtering
        html = template.render(
            target_role=target_role,
            articles=articles,  # Template filters by role
            report_date=report_date,
            company_name=company_name
        )

        # Inline CSS for email compatibility
        inlined_html = transform(html)

        logger.info(
            "role_brief_generated",
            role=target_role,
            total_articles=len(articles),
            filtered_count=len([a for a in articles if target_role in a.get("roles", [])])
        )

        return inlined_html

    def generate_all_role_briefs(
        self,
        articles: List[dict],
        report_date: datetime
    ) -> dict[str, str]:
        """
        Generate separate HTML brief for each role.

        Returns dict mapping role name to HTML content:
        {"Brokers": "<html>...", "Leadership": "<html>...", ...}
        """
        roles = ["Brokers", "Leadership", "Compliance", "Underwriting"]
        briefs = {}

        for role in roles:
            briefs[role] = self.generate_role_brief(
                target_role=role,
                articles=articles,
                report_date=report_date
            )

        logger.info("all_briefs_generated", role_count=len(briefs))
        return briefs
```

**Source:** BrasilIntel `app/services/reporter.py` pattern; premailer library documentation.

## State of the Art

Current approaches vs deprecated patterns:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON mode with manual parsing | Structured outputs with Pydantic | Aug 2024 | 100% schema compliance vs ~70-80% |
| SMTP email delivery | Microsoft Graph API | 2023 | Deprecated auth, better deliverability |
| Single-role classification | Multi-role array classification | 2026 (this project) | More relevant routing, less missed content |
| JavaScript tabs in email | Separate email per role | Always (email limitation) | Better compatibility, simpler implementation |
| BeautifulSoup scraping | Apify with anti-bot features | Ongoing | 65.8% report increased anti-bot complexity |

**Deprecated/outdated:**
- **JSON mode without structured outputs**: Lower reliability, no automatic validation, requires error handling
- **Gmail support for `:checked` CSS**: Dropped October 2016, breaks interactive tabs
- **SMTP AUTH for M365**: Deprecated, Graph API is corporate standard
- **Manual HTML CSS inlining**: Error-prone, premailer automates this

**Sources:**
- [OpenAI Structured Outputs Launch](https://openai.com/index/introducing-structured-outputs-in-the-api/) — August 2024
- [Interactive Tabs for Email](https://freshinbox.com/blog/interactive-tabs-for-email/) — Gmail limitations
- [Microsoft Graph Email Tutorial](https://learn.microsoft.com/en-us/graph/tutorials/python-email) — modern auth
- [State of Web Scraping 2026](https://blog.apify.com/web-scraping-report-2026/) — anti-bot trends

## Open Questions

Things that couldn't be fully resolved:

### 1. Optimal role classification prompt for insurance domain

**What we know:**
- Structured outputs with Pydantic work reliably (100% schema compliance)
- Multi-role classification is supported via `List[RoleType]`
- Insurance domain requires nuanced understanding of audience needs

**What's unclear:**
- Exact prompt wording that maximizes role coverage without over-inclusion
- Whether few-shot examples improve classification accuracy for edge cases
- Optimal balance between precision (only relevant roles) and recall (don't miss any role)

**Recommendation:**
- Start with prompt template provided in Code Examples section
- Measure classification quality with test dataset (20-30 articles manually labeled)
- Iterate prompt based on role coverage metrics (target: 60% multi-role, 40% single-role)
- Add few-shot examples if edge cases emerge (e.g., complex M&A deals)

### 2. Reinsurance News scraping reliability and Apify actor availability

**What we know:**
- Reinsurance News has clean structured content (good test source)
- Apify has 10,000+ actors in marketplace
- Generic Web Scraper actor can scrape most sites

**What's unclear:**
- Whether dedicated Reinsurance News actor exists in Apify marketplace
- Scraping reliability for Reinsurance News specifically (rate limits, blocks, structure changes)
- Whether custom actor needed or generic Web Scraper sufficient

**Recommendation:**
1. Check Apify Store for existing news scraper actors (Insurance Journal, Google News)
2. Test generic Web Scraper with Reinsurance News URL first
3. If blocked/unreliable, build custom actor using Apify SDK (1-2 days work)
4. Alternative: Start with RSS feed if available (simpler, more reliable)
5. Document scraping patterns in Phase 1 for reuse in Phase 2 (18+ sources)

### 3. Email client CSS compatibility for role brief template

**What we know:**
- Outlook uses Word rendering engine (limited CSS)
- Gmail strips some CSS classes and styles
- Premailer inlines CSS for compatibility
- BrasilIntel template works in M365

**What's unclear:**
- Whether role brief template (simpler than prototype) renders correctly across all corporate email clients
- Specific CSS features that need fallbacks (flexbox → tables, grid → nested tables)
- Whether premailer alone is sufficient or additional email-specific CSS needed

**Recommendation:**
1. Start with simplified BrasilIntel template (proven in M365)
2. Test in Outlook Desktop, Outlook Web, Gmail before Phase 1 complete
3. Use Litmus or Email on Acid for comprehensive client testing (optional, not blocking)
4. Document CSS compatibility issues for future template enhancements
5. Keep prototype's visual design as reference, but simplify implementation for email

## Sources

### Primary (HIGH confidence)

**Official Documentation:**
- [Azure OpenAI Structured Outputs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs) — Microsoft official guide, array classification confirmed
- [OpenAI Structured Outputs Launch](https://openai.com/index/introducing-structured-outputs-in-the-api/) — 100% reliability claim, Pydantic integration
- [Microsoft Graph Email Tutorial](https://learn.microsoft.com/en-us/graph/tutorials/python-email) — Modern M365 email delivery patterns
- [Apify Actors Platform](https://apify.com/actors) — Web scraping infrastructure documentation

**Sister Project (Proven Patterns):**
- BrasilIntel Research Summary (`C:\BrasilIntel\.planning\research\SUMMARY.md`) — Comprehensive stack validation
- BrasilIntel Project Overview (`C:\BrasilIntel\.planning\PROJECT.md`) — Proven architecture decisions
- BrasilIntel Source Code (`C:\BrasilIntel\app\`) — Working implementations of all patterns

### Secondary (MEDIUM confidence)

**Industry Reports & Best Practices:**
- [State of Web Scraping Report 2026](https://blog.apify.com/web-scraping-report-2026/) — Anti-bot complexity trends (65.8% stat)
- [Apify Review 2026](https://hackceleration.com/apify-review/) — Real-world performance data
- [HTML and CSS in Emails: What Works in 2026?](https://designmodo.com/html-css-emails/) — Email client compatibility guide
- [Interactive Tabs for Email](https://freshinbox.com/blog/interactive-tabs-for-email/) — CSS-only tabs limitations
- [Build HTML Email Template: Tutorial 2026](https://mailtrap.io/blog/building-html-email-template/) — Modern email template patterns

**Academic & Industry Research:**
- [Relm Insurance AI Embedding](https://www.insurancebusinessmag.com/us/news/technology/how-relm-insurance-embeds-ai-across-underwriting-leadership-and-product-design-564232.aspx) — Insurance role classification example
- [Benchmarking Agents in Insurance Underwriting](https://arxiv.org/html/2602.00456v1) — Insurance AI use cases

### Tertiary (LOW confidence - context only)

**Community Discussions:**
- [CSS3 Accordion in Email](https://litmus.com/community/discussions/1104-css3-accordion-in-email) — Gmail `:checked` deprecation (2016)
- [Structured Output with Azure OpenAI - OpenAI Community](https://community.openai.com/t/structured-output-with-azure-openai/918260) — Implementation discussions

## Metadata

**Confidence breakdown:**
- **Standard stack: HIGH** — 100% reused from BrasilIntel v1.0 (shipped and working)
- **Architecture patterns: HIGH** — Sister project proven, role classification documented
- **Pitfalls: MEDIUM-HIGH** — Email limitations well-documented, role classification patterns inferred from structured outputs docs
- **Code examples: HIGH** — Adapted from working BrasilIntel code + official Azure OpenAI examples

**Research date:** 2026-02-06
**Valid until:** 2026-03-06 (30 days) — stack stable, email client limitations unchanging, sister project patterns proven

**Key dependencies:**
- BrasilIntel codebase as reference implementation
- Azure OpenAI structured outputs feature (stable since Aug 2024)
- Prototype HTML for visual design reference
- Microsoft Graph API for email delivery (corporate standard)

**Research gaps requiring Phase 1 validation:**
- Role classification prompt effectiveness (needs test dataset)
- Reinsurance News scraping reliability (needs production testing)
- Email template rendering across all corporate clients (needs Litmus testing)

---

## Sources Summary

**Primary Sources:**
- [Azure OpenAI Structured Outputs Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs)
- [OpenAI Structured Outputs Launch](https://openai.com/index/introducing-structured-outputs-in-the-api/)
- [Microsoft Graph Email Tutorial](https://learn.microsoft.com/en-us/graph/tutorials/python-email)
- [Apify Actors Platform](https://apify.com/actors)
- BrasilIntel Research & Codebase (sister project)

**Secondary Sources:**
- [State of Web Scraping Report 2026](https://blog.apify.com/web-scraping-report-2026/)
- [Apify Review 2026](https://hackceleration.com/apify-review/)
- [HTML and CSS in Emails: What Works in 2026?](https://designmodo.com/html-css-emails/)
- [Interactive Tabs for Email](https://freshinbox.com/blog/interactive-tabs-for-email/)
- [Relm Insurance AI Embedding](https://www.insurancebusinessmag.com/us/news/technology/how-relm-insurance-embeds-ai-across-underwriting-leadership-and-product-design-564232.aspx)

**Tertiary Sources:**
- [CSS3 Accordion in Email Discussion](https://litmus.com/community/discussions/1104-css3-accordion-in-email)
- [Build HTML Email Template: Tutorial 2026](https://mailtrap.io/blog/building-html-email-template/)
