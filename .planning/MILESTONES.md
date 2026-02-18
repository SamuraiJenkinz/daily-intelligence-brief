# Project Milestones: MDInsights

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
