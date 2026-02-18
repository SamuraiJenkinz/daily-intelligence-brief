# MDInsights

## What This Is

AI-powered daily intelligence brief for the global insurance and reinsurance market, replacing Marsh's outsourced "Daily Insights" product. The system scrapes news from 20+ global sources, uses GPT-4o to classify, prioritise, summarise, and route articles by audience role, then generates and delivers tailored HTML briefs to Brokers, Leadership, Compliance, and Underwriting teams each morning before market open. Includes a full admin dashboard for source/recipient management and report archive.

## Core Value

Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.

## Requirements

### Validated

- ✓ News collection from 20+ global insurance/reinsurance sources via Apify + RSS — v1.0
- ✓ AI classification: priority, audience roles, entities, sentiment, impact, category, region, business line — v1.0
- ✓ Role-based brief generation: tabbed HTML reports for Brokers, Leadership, Compliance, Underwriting — v1.0
- ✓ AI-generated executive summary per role — v1.0
- ✓ Priority classification: Critical / High / Medium / Monitor — v1.0
- ✓ Entity tracking across editions with mention counts — v1.0
- ✓ Sector heatmap with directional signals — v1.0
- ✓ "What to Watch" forward-looking section with timeframes — v1.0
- ✓ Sentiment and impact tagging per story — v1.0
- ✓ Market pulse bar with at-a-glance sector indicators — v1.0
- ✓ Daily morning email delivery via Microsoft Graph API — v1.0
- ✓ Full admin dashboard: sources, recipients, roles, report history — v1.0
- ✓ SQLite storage with deduplication — v1.0
- ✓ Windows Task Scheduler automation — v1.0
- ✓ Author attribution: Kevin Taylor, Colleague Technology Services — v1.0
- ✓ Production hardening: structured logging, retry logic, backup, health monitoring — v1.0

### Active

- [ ] Factiva/Dow Jones as primary news source via MMC Core API Recent News endpoint
- [ ] Equity price data inline with news stories via MMC Core API Equity Price endpoint
- [ ] Enterprise email delivery via MMC Core API Email endpoint (replacing Graph API)
- [ ] OAuth2 client credentials token management for API authentication
- [ ] Graceful fallback to Apify/RSS when Factiva is unavailable
- [ ] Graceful fallback to Graph API when enterprise email is unavailable
- [ ] Entity-to-ticker mapping for automatic equity price enrichment
- [ ] Admin dashboard updates for enterprise API configuration and status

### Out of Scope

- Real-time alerts — daily morning brief is sufficient for this audience
- Mobile app — HTML email is mobile-responsive by design
- Multi-tenant / SaaS — single Marsh deployment
- Brazilian insurer monitoring — that's BrasilIntel's domain
- Social media monitoring — traditional media and wire services only
- Historical trend analytics — build archive first, add analytics after 6+ months data
- coreapi-access-management (full scope) — only using client credentials grant for token acquisition
- coreapi-data — deferred to future milestone
- Dedicated equity market data section — equity data shown inline with stories only
- Historical stock quotes — Equity Price API provides current quotes only

## Context

**Business Context:**
- v1.0 shipped Feb 2026, replacing the outsourced 27-page "Marsh Daily Insights" with an AI-powered system
- Prototype validated the concept with live data before development began
- System is production-ready with admin dashboard, automated delivery, and monitoring

**Sister Project:**
- BrasilIntel (v1.0 shipped) monitors 897 Brazilian insurers. MDInsights reuses the same architectural patterns and tech stack.

**Technical Environment:**
- Python 3.11+, FastAPI, SQLite, Jinja2
- Azure OpenAI GPT-4o for classification and summarisation
- Apify SDK for web scraping, feedparser for RSS
- Microsoft Graph SDK for email delivery
- Bootstrap 5.3.3 + HTMX 2.0.4 for admin dashboard
- structlog for structured logging, tenacity for retry logic
- Windows Server on AWS (production), Windows 11 (development)
- 9,769 lines of Python across 175 files

**Enterprise API Access (staging access available):**
- MMC Core API platform (Apigee) — staging credentials in hand
- v1.1 scope: coreapi-recent-news, coreapi-equity-price, coreapi-email + access-management (auth only)
- Deferred: coreapi-data, coreapi-access-management (full scope)
- API docs: NewsAPI.pdf, equityref.pdf, emailref.pdf, wtjref.pdf (Access Management)
- Auth: X-Api-Key for News/Equity, JWT Bearer + X-Api-Key for Email
- Client credentials grant via Access Management API for JWT token acquisition
- Non-prod host: mmc-dallas-int-non-prod-ingress.mgti.mmc.com
- Prod host: mmc-dallas-int-prod-ingress.mgti.mmc.com

**Audience Roles:**

| Role | Receives | Examples |
|---|---|---|
| Brokers | Competitor moves, market positioning, pricing trends | Rate changes, capacity shifts, broker M&A |
| Leadership | M&A activity, financial results, strategic signals | Acquisitions, earnings, market forecasts |
| Compliance | Regulatory developments, legal changes, coverage gaps | FCA reform, ransomware bans, war clauses |
| Underwriting | Loss trends, cat events, reserve adequacy, rate movements | Storm losses, combined ratios, softening signals |

## Current Milestone: v1.1 Enterprise API Integration

**Goal:** Integrate MMC Core API platform to make Factiva the primary news source, enrich briefs with inline equity price data, and switch email delivery to enterprise proxy — all with graceful fallback to existing infrastructure.

**Target features:**
- Factiva/Dow Jones as primary news feed (Apify becomes fallback)
- Inline equity price/change data alongside relevant articles
- Enterprise email delivery replacing Microsoft Graph API
- OAuth2 client credentials token management
- Admin dashboard enterprise API status and configuration

## Constraints

- **Tech Stack**: Python 3.11+, FastAPI, SQLite, Apify SDK, Azure OpenAI SDK, Microsoft Graph SDK — matching BrasilIntel
- **Corporate Auth**: Azure AD app registration for Graph API and Azure OpenAI access
- **Deployment**: Windows Scheduled Task (production), matching BrasilIntel pattern
- **Branding**: Reports must match Marsh visual identity (prototype establishes this)
- **Delivery Window**: Brief must be generated and delivered before market open (08:00 local)
- **Author**: All reports attributed to Kevin Taylor, Colleague Technology Services

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate emails per role | Each audience gets only relevant content — core value proposition | ✓ Good |
| Reuse BrasilIntel tech stack | Proven patterns, reduced learning curve, shared deployment infrastructure | ✓ Good |
| Apify + web scraping for collection | Same method that produced the working prototype | ✓ Good |
| Full admin dashboard | Manage sources, recipients, roles, and report history via web UI | ✓ Good |
| Daily morning delivery only | Sufficient for senior management audience, avoids alert fatigue | ✓ Good |
| HTML email (no PDF for v1) | Mobile-responsive, faster to generate, prototype already demonstrates quality | ✓ Good |
| Bootstrap 5.3.3 + HTMX 2.0.4 | CDN-only, zero build step, latest stable versions | ✓ Good |
| structlog + tenacity | Structured JSON logging with mature retry library | ✓ Good |
| sqlite3 .backup() API | Safe online backups without exclusive locks | ✓ Good |
| Statistical health thresholds | Adapts to source variability with standard deviation-based alerting | ✓ Good |
| FTS5 with BM25 ranking | Fast full-text search with relevance ranking in SQLite | ✓ Good |
| Factiva as primary news source | Enterprise Dow Jones feed more reliable and comprehensive than web scraping | — Pending |
| Equity data inline (not separate section) | Price context alongside stories is more actionable than a dedicated market section | — Pending |
| Enterprise email with Graph fallback | Corporate API platform preferred, but Graph API proven and reliable as backup | — Pending |
| Client credentials grant for auth | Server-side cron pipeline, no user interaction needed | — Pending |
| Graceful fallback for all enterprise APIs | Production reliability requires fallback to proven v1.0 infrastructure | — Pending |

---
*Last updated: 2026-02-18 after v1.1 milestone start*
