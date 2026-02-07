# Roadmap: MDInsights

## Overview

MDInsights transforms global insurance news into actionable intelligence for Marsh stakeholders. The journey starts with a vertical slice proving end-to-end data flow, scales to comprehensive news collection and AI classification, builds sophisticated report generation with role-based intelligence, automates daily delivery, adds administrative control, and hardens for production reliability. Each phase delivers measurable value while maintaining the BrasilIntel architectural foundation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Vertical Slice Foundation** - Single source to single tabbed report with AI classification
- [ ] **Phase 2: News Collection at Scale** - 18+ sources with Apify actors and RSS feeds
- [ ] **Phase 3: Advanced Classification Pipeline** - Priority ranking, entity extraction, and comprehensive tagging
- [ ] **Phase 4: Intelligence Report Generation** - Tabbed HTML brief with executive summaries and analytics
- [ ] **Phase 5: Automated Delivery System** - Microsoft Graph email delivery with Task Scheduler automation
- [ ] **Phase 6: Admin Dashboard** - HTMX web interface for source and recipient management
- [ ] **Phase 7: Production Hardening** - Source health monitoring, backup, and reliability features
- [ ] **Phase 8: Polish and Launch** - Marsh branding refinement, documentation, and production deployment

## Phase Details

### Phase 1: Vertical Slice Foundation
**Goal**: Prove end-to-end architecture with minimal working pipeline from one source to HTML brief
**Depends on**: Nothing (first phase)
**Requirements**: COLL-01 (partial), COLL-05 (partial), CLSF-02, CLSF-05 (partial), REPT-01 (partial), REPT-02 (partial), REPT-09 (partial)
**Success Criteria** (what must be TRUE):
  1. System successfully scrapes articles from one test source via Apify
  2. Azure OpenAI GPT-4o assigns role tags to each article
  3. Single HTML brief renders with clickable role tabs showing filtered articles
  4. SQLite database stores articles with source metadata and classifications
  5. Administrator can manually trigger brief generation and view output
**Plans**: 5 plans

Plans:
- [ ] 01-01: Project scaffolding — FastAPI app structure, SQLite schema, Azure OpenAI + Apify SDK integration
- [ ] 01-02: Single-source Apify actor — scrape one test source, store raw articles in database
- [ ] 01-03: Basic AI classification — GPT-4o role tagging (Brokers/Leadership/Compliance/Underwriting)
- [ ] 01-04: Tabbed HTML brief prototype — Jinja2 template with role tabs, article cards, basic styling
- [ ] 01-05: Manual trigger endpoint — FastAPI route to run collection → classification → report generation

### Phase 2: News Collection at Scale
**Goal**: Expand from one source to 18+ global insurance news sources with robust collection
**Depends on**: Phase 1
**Requirements**: COLL-01, COLL-02, COLL-03, COLL-04, COLL-05
**Success Criteria** (what must be TRUE):
  1. System collects articles from 18+ global insurance/reinsurance sources daily
  2. Apify actors handle different source types (news sites, press release pages, wire services)
  3. RSS feed parser ingests articles from major publications as secondary source
  4. Content similarity algorithm deduplicates articles across sources with >85% accuracy
  5. Source health monitor alerts when a source returns zero articles for 24+ hours
**Plans**: 6 plans

Plans:
- [ ] 02-01-PLAN.md — Priority Apify scrapers (Insurance Journal, Business Insurance, Artemis, Lloyd's List)
- [ ] 02-02-PLAN.md — Generic RSS feed source class with feedparser integration
- [ ] 02-03-PLAN.md — Source integration wiring (collector routing, 18-source seed script)
- [ ] 02-04-PLAN.md — Semantic deduplication engine (sentence-transformers, 0.85 threshold)
- [ ] 02-05-PLAN.md — Source health monitoring (baseline tracking, anomaly detection)
- [ ] 02-06-PLAN.md — Collection orchestration (dedup + health wiring into pipeline)

### Phase 3: Advanced Classification Pipeline
**Goal**: Implement comprehensive AI classification beyond role tags for rich intelligence
**Depends on**: Phase 2
**Requirements**: CLSF-01, CLSF-03, CLSF-04, CLSF-05
**Success Criteria** (what must be TRUE):
  1. AI assigns priority tier (Critical/High/Medium/Monitor) to each article based on market impact
  2. AI extracts entities (companies, people, organizations) from article content
  3. AI tags each article with sentiment (positive/negative/neutral) and impact level
  4. AI assigns category, region, and business line to each article for filtering
  5. Classification uses GPT-4o with structured JSON output for consistent parsing
**Plans**: 5 plans

Plans:
- [ ] 03-01: Priority classification system — GPT-4o prompt for Critical/High/Medium/Monitor tiers with business logic
- [ ] 03-02: Entity extraction pipeline — identify and normalize companies, people, organizations from article text
- [ ] 03-03: Sentiment and impact analysis — positive/negative/neutral sentiment, impact level scoring
- [ ] 03-04: Categorical tagging system — category (M&A, regulatory, loss event), region, business line assignment
- [ ] 03-05: Structured output schema — Pydantic models with GPT-4o structured output mode for type safety

### Phase 4: Intelligence Report Generation
**Goal**: Generate production-quality tabbed HTML brief with executive summaries and analytics
**Depends on**: Phase 3
**Requirements**: REPT-01, REPT-02, REPT-03, REPT-04, REPT-05, REPT-06, REPT-07, REPT-08, REPT-09, REPT-10
**Success Criteria** (what must be TRUE):
  1. HTML brief has four clickable tabs (Brokers, Leadership, Compliance, Underwriting) showing only relevant articles
  2. Each role tab displays priority-ranked articles with top items appearing first
  3. AI generates tailored executive summary for each role tab based on that day's relevant articles
  4. Sector heatmap visualizes directional signals across insurance sectors
  5. Entity tracker shows mention counts for key companies/people across the edition
  6. "What to Watch" section provides forward-looking analysis with timeframes
  7. Market pulse bar displays at-a-glance sector indicators
  8. Each article card includes sentiment, impact, entity, region, and business line chips
  9. Report matches Marsh visual identity with professional styling
  10. Report attributes authorship to Kevin Taylor, Colleague Technology Services in footer
**Plans**: 10 plans

Plans:
- [ ] 04-01: Role-specific filtering — query logic to select articles per role, priority ranking algorithm
- [ ] 04-02: Executive summary generation — GPT-4o prompt per role tab, one-paragraph distillation of key themes
- [ ] 04-03: Sector heatmap component — aggregate articles by sector, calculate directional signals (up/down/neutral)
- [ ] 04-04: Entity tracker component — count entity mentions across edition, rank by prominence
- [ ] 04-05: "What to Watch" section — GPT-4o analysis of forward-looking stories with timeframes (this week/month/quarter)
- [ ] 04-06: Market pulse bar — visual indicator combining sector signals into overall market sentiment
- [ ] 04-07: Article card design — chips for sentiment/impact/entity/region/business line, priority badges
- [ ] 04-08: Marsh branding integration — CSS matching Marsh corporate identity, logo, color palette
- [ ] 04-09: Mobile-responsive template — ensure tabs and cards work on phone/tablet screens
- [ ] 04-10: Author attribution — footer with Kevin Taylor credit and Colleague Technology Services attribution

### Phase 5: Automated Delivery System
**Goal**: Automate daily email delivery via Microsoft Graph with Windows Task Scheduler
**Depends on**: Phase 4
**Requirements**: DELV-01, DELV-02, DELV-03
**Success Criteria** (what must be TRUE):
  1. System sends HTML brief via Microsoft Graph API to configured recipients
  2. Email renders properly in Outlook, Gmail, and mobile clients
  3. Windows Task Scheduler triggers collection → classification → report → email pipeline daily at 06:00
  4. Task Scheduler logs execution status and alerts on failures
  5. Email delivery includes proper headers, subject line, and sender attribution
**Plans**: 4 plans

Plans:
- [ ] 05-01: Microsoft Graph email integration — configure Azure AD app, implement send mail with HTML body
- [ ] 05-02: Email template optimization — inline CSS with premailer, test across email clients (Outlook/Gmail/mobile)
- [ ] 05-03: Windows Task Scheduler automation — create scheduled task for daily 06:00 execution
- [ ] 05-04: Delivery monitoring and alerting — log success/failure, email admin on pipeline failures

### Phase 6: Admin Dashboard
**Goal**: Provide web interface for source management, recipient configuration, and report archive
**Depends on**: Phase 5
**Requirements**: ADMN-01, ADMN-02, ADMN-03, ADMN-04, ADMN-05
**Success Criteria** (what must be TRUE):
  1. Admin can add, edit, disable, and delete news sources via web form
  2. Admin can manage recipient list with role assignments (Brokers/Leadership/Compliance/Underwriting)
  3. Admin can view report archive and search past articles by date, source, or keyword
  4. Admin can manually trigger brief generation on-demand for testing
  5. Dashboard uses HTMX for dynamic updates without page reloads
**Plans**: 5 plans

Plans:
- [ ] 06-01: Source management UI — HTMX forms for add/edit/disable sources, table view with inline editing
- [ ] 06-02: Recipient management UI — manage recipient list, assign roles, enable/disable recipients
- [ ] 06-03: Report archive browser — list past reports by date, view archived HTML briefs
- [ ] 06-04: Article search interface — search articles by keyword, filter by date/source/role/priority
- [ ] 06-05: Manual trigger controls — button to run pipeline on-demand, view logs, monitor progress

### Phase 7: Production Hardening
**Goal**: Add reliability features for production operation and long-term maintenance
**Depends on**: Phase 6
**Requirements**: COLL-04 (enhanced)
**Success Criteria** (what must be TRUE):
  1. Source health monitoring detects anomalies and emails alerts to administrator
  2. SQLite database has automated backup to Azure Blob Storage
  3. Classification accuracy monitoring tracks drift over time
  4. Pipeline includes comprehensive error handling with retry logic
  5. Structured logging provides observability for troubleshooting
**Plans**: 5 plans

Plans:
- [ ] 07-01: Enhanced source health monitoring — statistical baseline, anomaly detection, email alerts
- [ ] 07-02: Database backup automation — Litestream or scheduled backup to Azure Blob Storage
- [ ] 07-03: Classification drift monitoring — track classification patterns, alert on statistical anomalies
- [ ] 07-04: Error handling and retry logic — exponential backoff for Apify/Azure OpenAI/Graph API failures
- [ ] 07-05: Production logging — structured logs with JSON output, log aggregation for debugging

### Phase 8: Polish and Launch
**Goal**: Final refinements for production deployment and stakeholder handoff
**Depends on**: Phase 7
**Requirements**: REPT-09 (enhanced), REPT-10 (enhanced)
**Success Criteria** (what must be TRUE):
  1. Report styling matches Marsh brand guidelines precisely
  2. User documentation covers administrator workflows and troubleshooting
  3. Deployment documentation covers Windows Server setup and Azure configuration
  4. System is deployed to production environment with monitoring active
  5. Stakeholders have received sample briefs and provided approval
**Plans**: 4 plans

Plans:
- [ ] 08-01: Final Marsh branding review — refine CSS, logo placement, typography to match brand guidelines
- [ ] 08-02: User documentation — administrator guide covering source/recipient management and troubleshooting
- [ ] 08-03: Deployment documentation — Windows Server setup, Azure AD app registration, Task Scheduler configuration
- [ ] 08-04: Production deployment and handoff — deploy to production, configure monitoring, stakeholder sign-off

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Vertical Slice Foundation | 0/5 | Not started | - |
| 2. News Collection at Scale | 0/6 | Not started | - |
| 3. Advanced Classification Pipeline | 0/5 | Not started | - |
| 4. Intelligence Report Generation | 0/10 | Not started | - |
| 5. Automated Delivery System | 0/4 | Not started | - |
| 6. Admin Dashboard | 0/5 | Not started | - |
| 7. Production Hardening | 0/5 | Not started | - |
| 8. Polish and Launch | 0/4 | Not started | - |

**Total:** 0/44 plans complete across 8 phases
