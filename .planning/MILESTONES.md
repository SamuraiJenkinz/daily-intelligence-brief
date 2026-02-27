# Project Milestones: MDInsights

## v1.2 Factiva Knowledge Integration (Shipped: 2026-02-27)

**Delivered:** Replaced Apify web scraping with BrasilIntel's proven FactivaCollector, making Factiva/Dow Jones the sole news source — removing 1,443 lines of dead code and 2 dependencies while simplifying the pipeline, dashboard, and admin UI.

**Phases completed:** 14-16 (8 plans total)

**Key accomplishments:**

- FactivaCollector port — Ported BrasilIntel's proven 456-line collector with 3 critical bug fixes (API params, URL encoding, keyword joining) and 2 improvements (configurable date range, is_configured delegation)
- Pipeline simplification — Replaced multi-source fallback with single Factiva collection path, inline article storage, clean run-record-at-start pattern
- Apify infrastructure removal — Deleted ApifyCollector class + 6 source implementations (1,443 lines), removed apify-client and feedparser dependencies
- Dashboard Factiva-only update — Binary health status (healthy/offline), Factiva-only badges, simplified 4-column source management UI
- Configuration alignment — Honest sole-source messaging, date_range_hours admin field, DB-compatible schema preservation

**Stats:**

- 35 files changed (+417 / -1,755 lines)
- ~11,900 lines of Python (down from ~14,200)
- 3 phases, 8 plans, 43 must-haves verified
- 2 days (Feb 26-27, 2026)
- 38 commits

**Git range:** `1b0e3db` → `c364697`

**Tech debt carried:** 3 items (all intentional DB compatibility decisions — SourceType.APIFY enum, collector_source default, NEWS_FALLBACK enum)

**What's next:** TBD — `/gsd:new-milestone` for next milestone planning

---

## v1.1 Enterprise API Integration (Shipped: 2026-02-19)

**Delivered:** Enterprise API integration replacing web scraping with Factiva as primary news source, adding inline equity price data to briefs, switching email delivery to MMC Core API enterprise proxy, and surfacing API health in the admin dashboard — all with graceful fallback to proven v1.0 infrastructure.

**Phases completed:** 9-13 (12 plans total)

**Key accomplishments:**

- OAuth2 token management — JWT client_credentials with 5-min proactive refresh, api_events observability table, degraded-auth graceful fallback
- Factiva news collection — Primary Dow Jones/Factiva news source via MMC Core API with insurance-focused Apify/RSS fallback and per-article source attribution
- Equity price enrichment — Admin-configurable entity-to-ticker mapping with inline equity chips (ticker, price, change%) in browser and email briefs
- Enterprise email delivery — Async EnterpriseEmailClient with JWT+API-Key auth, enterprise-first delivery with per-role Graph API fallback
- Admin dashboard enterprise status — Real-time API health panel, credential management UI, fallback event log, per-article source badges

**Stats:**

- 29 files created/modified
- ~4,400 lines added (Python + HTML templates)
- 5 phases, 12 plans
- 2 days (Feb 18-19, 2026)
- ~60 commits

**Git range:** `ac701dd` → `be01185`

**Tech debt carried:** 6 items (0 critical, 1 medium, 3 low, 2 info) — see v1.1-MILESTONE-AUDIT.md

**What's next:** TBD — `/gsd:new-milestone` for next milestone planning

---

## v1.0 MVP (Shipped: 2026-02-08)

**Delivered:** AI-powered daily intelligence brief system for Marsh, replacing the outsourced Daily Insights product with role-targeted, priority-ranked, AI-summarised news briefs.

**Phases completed:** 1-8 (39 plans total)

**Key accomplishments:**

- Multi-source news collection pipeline — 20+ insurance sources via Apify actors and RSS feeds with semantic deduplication
- AI classification with entity extraction — 9-dimension tagging via Azure OpenAI GPT-4o structured outputs
- Role-based intelligence reporting — tabbed HTML briefs with executive summaries, heatmaps, entity tracking, and forward-looking analysis
- Automated email delivery — Microsoft Graph API with per-role recipient routing and Windows Task Scheduler automation
- Full admin dashboard — Bootstrap 5 + HTMX interface for sources, recipients, archive browsing, and manual triggers
- Production hardening — structured logging, retry logic, database backup, source health monitoring, classification drift detection

**Stats:**

- 175 files created/modified
- 9,769 lines of Python
- 8 phases, 39 plans
- 9 days from start to ship (Feb 6-15, 2026)
- 167 commits

**Git range:** `d50cbe4` → `2898a36`

**What's next:** Enterprise API integration (MMC Core API platform — Recent News, Equity Price, Data, Email APIs)

---
