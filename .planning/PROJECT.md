# MDInsights

## What This Is

AI-powered daily intelligence brief for the global insurance and reinsurance market, replacing Marsh's outsourced "Daily Insights" product. The system scrapes news from 18+ global sources, uses GPT-4o to classify, prioritise, summarise, and route articles by audience role, then generates and delivers separate tailored HTML briefs to Brokers, Leadership, Compliance, and Underwriting teams each morning before market open.

## Core Value

Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] News collection from 18+ global insurance/reinsurance sources via Apify + web scraping
- [ ] AI classification of each article: priority level, audience roles, entities, sentiment, impact, category, region, business line
- [ ] Role-based brief generation: separate tailored HTML reports for Brokers, Leadership, Compliance, Underwriting
- [ ] AI-generated executive summary per role
- [ ] Priority classification: Critical / High / Medium / Monitor
- [ ] Entity tracking across editions with mention counts
- [ ] Sector heatmap with directional signals
- [ ] "What to Watch" forward-looking section with timeframes
- [ ] Sentiment and impact tagging per story
- [ ] Market pulse bar with at-a-glance sector indicators
- [ ] Daily morning email delivery via Microsoft Graph API (separate email per role)
- [ ] Full admin dashboard: manage sources, recipients, roles, view report history
- [ ] SQLite storage with deduplication
- [ ] Windows Task Scheduler automation for daily morning runs
- [ ] Author attribution: Kevin Taylor, Colleague Technology Services

### Out of Scope

- Real-time alerts — daily morning brief is sufficient for this audience
- Mobile app — HTML email is mobile-responsive by design
- Multi-tenant / SaaS — single Marsh deployment
- Brazilian insurer monitoring — that's BrasilIntel's domain
- Social media monitoring — traditional media and wire services only
- Historical trend analytics — build archive first, add analytics after 6+ months data
- PDF attachment — HTML email is the primary format (PDF can be v2)

## Context

**Business Context:**
- Current state: "Marsh Daily Insights" — a 27-page outsourced daily email with ~10 unranked articles from Bloomberg, Reuters, Business Insurance, The Insurer. No intelligence layer, no prioritisation, no role relevance, no summarisation.
- Target state: AI-powered brief that leapfrogs the current product — priority-classified, role-targeted, entity-tracked, forward-looking.
- Prototype exists: `RefChyt/prototype_daily_intelligence_brief.html` demonstrates the target output with live Feb 6, 2026 data.
- Assessment document exists: `RefChyt/Daily_Insights_Replacement_Analysis.html` — the business case for senior leadership.

**Sister Project:**
- BrasilIntel (v1.0 shipped) monitors 897 Brazilian insurers. MDInsights reuses the same architectural patterns and tech stack but targets global insurance/reinsurance news for a different audience.

**Technical Environment:**
- Corporate M365 Exchange Online (Graph API for email)
- Azure AD for authentication
- Azure OpenAI (corporate LLM deployment)
- Apify account for web scraping
- Windows Server on AWS (production)
- Windows 11 (development)

**Target Sources (from prototype):**
- Reinsurance News, Insurance Journal, Insurance Business, GlobeNewsWire, Bloomberg, Reuters, Business Insurance, The Insurer, Artemis, S&P Global, Moody's, Fitch Ratings, AM Best, Lloyd's List, and others

**Audience Roles:**

| Role | Receives | Examples |
|---|---|---|
| Brokers | Competitor moves, market positioning, pricing trends | Rate changes, capacity shifts, broker M&A |
| Leadership | M&A activity, financial results, strategic signals | Acquisitions, earnings, market forecasts |
| Compliance | Regulatory developments, legal changes, coverage gaps | FCA reform, ransomware bans, war clauses |
| Underwriting | Loss trends, cat events, reserve adequacy, rate movements | Storm losses, combined ratios, softening signals |

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
| Separate emails per role | Each audience gets only relevant content — core value proposition | — Pending |
| Reuse BrasilIntel tech stack | Proven patterns, reduced learning curve, shared deployment infrastructure | — Pending |
| Apify + web scraping for collection | Same method that produced the working prototype | — Pending |
| Full admin dashboard | Manage sources, recipients, roles, and report history via web UI | — Pending |
| Daily morning delivery only | Sufficient for senior management audience, avoids alert fatigue | — Pending |
| HTML email (no PDF for v1) | Mobile-responsive, faster to generate, prototype already demonstrates quality | — Pending |

---
*Last updated: 2026-02-06 after initialization*
