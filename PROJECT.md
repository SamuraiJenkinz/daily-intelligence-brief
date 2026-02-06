# MDInsights — Global Intelligence Brief

## Overview

A standalone application that produces an AI-powered Global Intelligence Brief for the global insurance and reinsurance market. It replaces "Marsh Daily Insights" by leapfrogging it — delivering role-targeted, priority-classified, AI-summarised intelligence instead of a 27-page undifferentiated text dump.

## Built on the BrasilIntel Framework

Reuses the same architectural patterns as the existing BrasilIntel system:

- **FastAPI** web service
- **Apify + RSS** for news collection (targeting global insurance/reinsurance sources instead of Brazilian insurers)
- **GPT-4o** for classification, summarisation, and priority ranking
- **Jinja2** HTML report templates (based on the prototype already built in `RefChyt/prototype_daily_intelligence_brief.html`)
- **Microsoft Graph API** for email delivery
- **SQLite** for storage
- **Windows Task Scheduler** for automation

## The Leap: Role-Based Distribution

Instead of one 27-page dump for everyone, the system classifies each story by audience relevance and produces tailored briefs.

### Audience Roles

| Role | Receives | Example Stories |
|---|---|---|
| **Brokers** | Competitor moves, market positioning, pricing trends | Reinsurance rates down 20%, cyber rates down 32%, Howden $703M raise |
| **Leadership** | M&A activity, financial results, strategic signals | Zurich-Beazley bid, Chubb record results, $1.12T market forecast |
| **Compliance** | Regulatory developments, legal changes, coverage gaps | UK ransomware ban proposal, LMA war clause reform, FCA reform delays |
| **Underwriting** | Loss trends, cat events, reserve adequacy, rate movements | Winter Storm Fern $4-7B, US casualty reserve deficiency, market softening |

### How It Works

The AI does the routing — each article gets tagged with relevant roles during classification, and the system generates multiple versions of the brief from the same underlying data. Leadership gets 5 stories. Brokers get 7 different ones. Everyone gets only what matters to their decisions.

## Intelligence Features

Features demonstrated in the prototype (`RefChyt/prototype_daily_intelligence_brief.html`):

- **Priority Classification** — Critical / High / Medium / Monitor
- **Executive Summary** — AI-generated per role, highlighting what matters to that audience
- **Entity Tracking** — Companies mentioned across editions with frequency counts
- **Sector Heatmap** — Directional signals across market segments
- **"What to Watch"** — Forward-looking items with timeframes
- **Sentiment & Impact Tagging** — Per-story sentiment, impact level, business line, and region tags
- **Market Pulse Bar** — At-a-glance sector status indicators

## Pipeline

The core pipeline follows the same collect-classify-store-generate-deliver pattern as BrasilIntel:

```
[Apify + RSS Sources]
        |
        v
  [News Collection]  — Scrape/fetch from 18+ global insurance/reinsurance sources
        |
        v
  [AI Classification]  — GPT-4o: priority, role relevance, entities, sentiment, impact, category
        |
        v
  [SQLite Storage]  — Deduplicated, timestamped, fully classified articles
        |
        v
  [Report Generation]  — Jinja2 templates produce role-specific HTML briefs
        |
        v
  [Email Delivery]  — Microsoft Graph API sends tailored briefs to each audience
```

## What Stays the Same as BrasilIntel

- The pipeline pattern (collect → classify → store → generate → deliver)
- The deployment model (Windows server, Task Scheduler)
- The tech stack (Python, FastAPI, SQLite, Jinja2, Microsoft Graph)

## What's New

- **Global source set** — Bloomberg, Reuters, Insurance Journal, Reinsurance News, Business Insurance, The Insurer, Artemis, Insurance Business, GlobeNewsWire, and others
- **Role-based audience model** — Multiple distribution lists, each receiving a tailored brief
- **Multi-brief generation** — Single data set produces multiple role-specific reports
- **Richer AI classification** — Priority + role + entity + sentiment + impact + category + region + business line
- **Forward-looking intelligence** — "What to Watch" section with timeframes and strategic context

## Author

Kevin Taylor — Colleague Technology Services
