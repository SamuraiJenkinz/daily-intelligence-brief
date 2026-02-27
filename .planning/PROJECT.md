# MDInsights

## What This Is

AI-powered daily intelligence brief for the global insurance and reinsurance market, replacing Marsh's outsourced "Daily Insights" product. The system collects news from Factiva/Dow Jones as its sole source via MMC Core API, uses GPT-4o to classify, prioritise, summarise, and route articles by audience role, enriches stories with inline equity price data for tracked companies, then generates and delivers tailored HTML briefs via MMC Core API enterprise email (with Graph API fallback) to Brokers, Leadership, Compliance, and Underwriting teams each morning before market open. Includes a full admin dashboard for source/recipient management, enterprise API health monitoring, credential configuration, and report archive.

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
- ✓ Factiva/Dow Jones as primary news source via MMC Core API Recent News endpoint — v1.1
- ✓ Equity price data inline with news stories via MMC Core API Equity Price endpoint — v1.1
- ✓ Enterprise email delivery via MMC Core API Email endpoint (with Graph API fallback) — v1.1
- ✓ OAuth2 client credentials token management for API authentication — v1.1
- ✓ Graceful fallback to Apify/RSS when Factiva is unavailable — v1.1
- ✓ Graceful fallback to Graph API when enterprise email is unavailable — v1.1
- ✓ Entity-to-ticker mapping for automatic equity price enrichment — v1.1
- ✓ Admin dashboard enterprise API health, credential config, source badges, fallback log — v1.1
- ✓ BrasilIntel FactivaCollector port with 3 bug fixes and 2 improvements — v1.2
- ✓ Factiva as sole news source (Apify collection layer and dependencies removed) — v1.2
- ✓ Single-path pipeline orchestration with inline article storage — v1.2
- ✓ English insurance/reinsurance Factiva query config with configurable date range — v1.2
- ✓ Factiva-only dashboard: binary health status, Factiva badges, simplified source UI — v1.2
- ✓ Dead code cleanup: 1,443 lines removed, 2 dependencies eliminated — v1.2

### Active

**Current Milestone: v2.0 Audio Intelligence Briefings**

**Goal:** Add per-role podcast-style audio briefings to the daily intelligence pipeline, delivered as MP3 attachments and streaming links alongside existing HTML emails.

**Target features:**
- AI podcast script generation from classified articles (GPT-4o) — natural narration style, 2-5 min per role
- Azure OpenAI TTS conversion of scripts to MP3 audio
- Per-role audio briefings (Brokers, Leadership, Compliance, Underwriting)
- Branded intro ("Good morning, this is your Marsh [Role] intelligence brief...") + sign-off
- MP3 file attachment on existing role-based emails
- Streaming link in email to play audio in-browser
- Audio archive and playback endpoint on admin dashboard
- Pipeline integration — audio generation runs after brief generation in daily pipeline

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
- Multiple collection sources / pluggable collector architecture — Factiva-only is sufficient
- Apify web scraping — replaced by enterprise Factiva feed in v1.2

## Context

**Business Context:**
- v1.0 shipped Feb 2026, replacing the outsourced 27-page "Marsh Daily Insights" with an AI-powered system
- v1.1 shipped Feb 2026, integrating MMC Core API platform for enterprise news, equity, and email
- v1.2 shipped Feb 2026, porting BrasilIntel's proven FactivaCollector and removing Apify infrastructure
- Prototype validated the concept with live data before development began
- System is production-ready with admin dashboard, automated delivery, monitoring, and enterprise API integration

**Sister Project:**
- BrasilIntel (v1.0 shipped) monitors 897 Brazilian insurers. MDInsights reuses the same architectural patterns and tech stack.
- BrasilIntel's FactivaCollector was ported to MDInsights in v1.2 with 3 bug fixes and 2 improvements.

**Technical Environment:**
- Python 3.11+, FastAPI, SQLite, Jinja2
- Azure OpenAI GPT-4o for classification and summarisation
- Factiva/Dow Jones as sole news source via MMC Core API (ported from BrasilIntel)
- MMC Core API enterprise email (with Graph API fallback)
- Bootstrap 5.3.3 + HTMX 2.0.4 for admin dashboard
- structlog for structured logging, tenacity for retry logic
- Windows Server on AWS (production), Windows 11 (development)
- ~11,900 lines of Python across ~190 files (v1.0: 9,769 + v1.1: ~4,400 + v1.2: -1,338 net)

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

## Current State

v1.0 MVP, v1.1 Enterprise API Integration, and v1.2 Factiva Knowledge Integration all shipped. v2.0 Audio Intelligence Briefings in progress — adding podcast-style audio to the daily pipeline.

**Shipped milestones:**
- v1.0 MVP (Feb 2026) — AI-powered daily brief with 20+ sources, role-based delivery, admin dashboard
- v1.1 Enterprise API Integration (Feb 2026) — Factiva primary, equity enrichment, enterprise email, API health dashboard
- v1.2 Factiva Knowledge Integration (Feb 2026) — BrasilIntel FactivaCollector port, Apify removal, pipeline simplification

**Active milestone:** v2.0 Audio Intelligence Briefings

**Known tech debt:** 3 intentional DB compatibility items (SourceType.APIFY enum, collector_source default, NEWS_FALLBACK enum) + TD-01 (admin trigger missing TokenManager, medium severity)

**Deployment validation needed:** Staging API credentials required to validate Factiva industry codes, equity API paths, and enterprise email payload fields on deployment machine.

## Constraints

- **Tech Stack**: Python 3.11+, FastAPI, SQLite, Azure OpenAI SDK, Microsoft Graph SDK — matching BrasilIntel
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
| Factiva as primary news source | Enterprise Dow Jones feed more reliable and comprehensive than web scraping | ✓ Good |
| Equity data inline (not separate section) | Price context alongside stories is more actionable than a dedicated market section | ✓ Good |
| Enterprise email with Graph fallback | Corporate API platform preferred, but Graph API proven and reliable as backup | ✓ Good |
| Client credentials grant for auth | Server-side cron pipeline, no user interaction needed | ✓ Good |
| Graceful fallback for all enterprise APIs | Production reliability requires fallback to proven v1.0 infrastructure | ✓ Good |
| 5-min proactive token refresh margin | Access Management tokens expire in 1h; prevents mid-request expiry | ✓ Good |
| No retry on 401/403 auth errors | Invalid credentials won't resolve via retry; avoids account lockout | ✓ Good |
| ApiEventType enum with all 9 types upfront | Schema stability — avoids Alembic migration for new enum values | ✓ Good |
| Sync httpx for Factiva/Equity, async for Email | Matches each caller's execution context (sync pipeline vs async email) | ✓ Good |
| Transient ORM attributes for equity data | _equity_data on SQLAlchemy objects in-memory, never persisted — clean separation | ✓ Good |
| Port BrasilIntel FactivaCollector as foundation | Proven 456-line collector with pagination, retry, event tracking — avoid reinventing | ✓ Good |
| 48h default date range | BrasilIntel proven approach, admin-configurable, covers weekend gaps | ✓ Good |
| Correct API param names from BrasilIntel | BrasilIntel production validated: industry, company, query (not industryCodes etc.) | ✓ Good |
| Inline article storage in pipeline | Extract from ApifyCollector before deletion — pipeline owns full collection-to-storage | ✓ Good |
| Preserve DB schema compatibility | Keep SourceType.APIFY enum and defaults — removing breaks existing rows | ✓ Good |
| Binary news health status | No degraded state since no fallback exists — honest healthy/offline only | ✓ Good |
| Honest disable warning in FactivaConfig | "Stops all collection" not "fallback to Apify/RSS" — admins deserve truth | ✓ Good |

| Azure OpenAI TTS for audio | Same Azure stack as GPT-4o, no new vendor relationship needed | -- Pending |
| Per-role audio (not combined) | Matches core value — each audience hears only their intelligence | -- Pending |
| Admin dashboard serves streaming audio | Existing FastAPI server, no additional infrastructure | -- Pending |

---
*Last updated: 2026-02-27 after v2.0 milestone start*
