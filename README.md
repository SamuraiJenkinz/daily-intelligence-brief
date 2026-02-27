# MDInsights

MDInsights is an AI-powered intelligence briefing system built for the global insurance and reinsurance market. It replaces a manual 27-page daily report with role-targeted, priority-classified, AI-summarised briefs delivered directly to the people who need them.

## Purpose

The insurance market generates a high volume of news daily across dozens of sources. Different teams within an organisation care about different things: brokers need competitor intelligence, leadership needs M&A signals, compliance needs regulatory changes, and underwriting needs loss events and rate movements.

MDInsights solves this by collecting news from Factiva/Dow Jones via MMC Core API, using GPT-4o to classify each article by audience relevance, priority, sentiment, and category, then generating tailored HTML briefs and emailing them to the right teams automatically.

## How It Works

```
Factiva / Dow Jones (MMC Core API)
        |
   News Collection      Enterprise news feed with configurable industry/keyword queries
        |
   AI Classification    GPT-4o: priority, role relevance, entities, sentiment,
        |                impact, category, region, business line
   SQLite Storage       Deduplicated, timestamped, fully classified articles
        |
   Report Generation    Jinja2 templates produce role-specific HTML briefs
        |
   Email Delivery       MMC Core API enterprise email (Graph API fallback)
```

## Audience Roles

| Role | Receives | Examples |
|------|----------|----------|
| **Brokers** | Competitor moves, market positioning, pricing trends | Reinsurance rate changes, broker M&A, capacity shifts |
| **Leadership** | M&A activity, financial results, strategic signals | Zurich-Beazley bid, market forecasts, executive changes |
| **Compliance** | Regulatory developments, legal changes, coverage gaps | Ransomware ban proposals, FCA reforms, sanctions updates |
| **Underwriting** | Loss trends, cat events, reserve adequacy, rate movements | Winter storm losses, casualty reserve deficiency, market softening |

Each article can be assigned to multiple roles. Leadership gets 5 stories, Brokers gets 7 different ones. Everyone gets only what matters to their decisions.

## Intelligence Features

- **Priority Classification** -- Critical / High / Medium / Monitor
- **Executive Summary** -- AI-generated per role, highlighting what matters to that audience
- **Entity Tracking** -- Companies mentioned across editions with frequency counts
- **Sector Heatmap** -- Directional signals across market segments
- **What to Watch** -- Forward-looking items with timeframes
- **Sentiment and Impact Tagging** -- Per-story sentiment, impact level, business line, and region
- **Classification Drift Detection** -- Statistical monitoring (KS test, chi-square) to catch changes in AI behaviour over time

## Tech Stack

- **Python / FastAPI** -- Web framework and API
- **SQLAlchemy / SQLite** -- ORM and storage
- **Azure OpenAI (GPT-4o)** -- Article classification and summarisation
- **Factiva/Dow Jones** -- Sole news source via MMC Core API
- **MMC Core API** -- Enterprise API platform (news, equity, email)
- **httpx** -- HTTP client for API integration
- **Jinja2 / Premailer** -- HTML report generation with inlined CSS for email
- **Microsoft Graph API** -- Email delivery
- **sentence-transformers** -- Semantic deduplication
- **scipy** -- Statistical drift detection
- **HTMX / Bootstrap** -- Admin UI
- **Windows Task Scheduler** -- Automation

## Running the Application

### Web Server

```
.\venv\Scripts\activate
python -m app.main
```

The admin dashboard is available at `http://localhost:8001/admin`.

### Scheduled Pipeline

```powershell
.\deploy\setup_task.ps1
```

This registers four Windows Task Scheduler tasks:

| Task | Default Schedule |
|------|-----------------|
| Pipeline (collect, classify, email) | Daily at 06:00 |
| Database Backup | Daily at 07:00 |
| Classification Drift Check | Weekly on Monday at 08:00 |
| Pipeline Monitor | Daily at 09:00 |

### Configuration

All settings are managed via environment variables in `.env`:

- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` -- AI classification
- `MMC_API_BASE_URL`, `MMC_API_KEY` -- MMC Core API (Factiva news, equity prices)
- `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `SENDER_EMAIL` -- Email delivery
- `REPORT_RECIPIENTS_BROKERS`, `REPORT_RECIPIENTS_LEADERSHIP`, etc. -- Per-role email recipients
- `PORT` -- Web server port (default: 8001)

## Admin UI

The web-based admin interface provides:

- **Dashboard** -- System status, source counts, recent pipeline runs
- **Sources** -- CRUD management for news sources
- **Recipients** -- Per-role email recipient management with inline editing
- **Archive** -- Browse and view previously generated reports by date and role
- **Search** -- Full-text search (FTS5) across all collected articles with filters
- **Trigger** -- Manual pipeline execution with optional email delivery
- **Factiva Config** -- Factiva query parameters (industry codes, keywords, date range)
- **API Status** -- Enterprise API health monitoring and fallback event log

## Author

Kevin Taylor -- Colleague Technology Services
