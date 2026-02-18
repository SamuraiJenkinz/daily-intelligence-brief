# Requirements: MDInsights

**Defined:** 2026-02-18
**Core Value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.

## v1.1 Requirements

Requirements for enterprise API integration milestone. Each maps to roadmap phases.

### Authentication

- [ ] **AUTH-01**: System acquires JWT tokens via OAuth2 client credentials grant from Access Management API
- [ ] **AUTH-02**: System caches tokens and auto-refreshes before expiry
- [ ] **AUTH-03**: Token acquisition failures are logged and don't block the pipeline (fallback to v1.0 delivery)

### News Collection

- [ ] **NEWS-01**: System searches Factiva for insurance industry news via /coreapi/recent-news/v1/search
- [ ] **NEWS-02**: System uses Factiva industry and company codes for targeted insurance/reinsurance queries
- [ ] **NEWS-03**: System extracts article content (headline, snippet, plaintext, publication date, source URL)
- [ ] **NEWS-04**: System deduplicates Factiva articles against existing article store
- [ ] **NEWS-05**: Factiva articles flow through existing AI classification pipeline unchanged
- [ ] **NEWS-06**: Factiva is the primary news source; Apify/RSS run as secondary fallback

### Equity Enrichment

- [ ] **EQTY-01**: System maintains a configurable mapping of tracked entities to ticker symbols and exchanges
- [ ] **EQTY-02**: System fetches current equity prices for entities mentioned in classified articles
- [ ] **EQTY-03**: Equity data (price, change, percent) appears inline with relevant stories in the brief
- [ ] **EQTY-04**: Missing or failed equity lookups don't break the brief

### Email Delivery

- [ ] **MAIL-01**: System sends role-based briefs via POST /coreapi/email/v1
- [ ] **MAIL-02**: System authenticates to Email API with JWT Bearer token + X-Api-Key
- [ ] **MAIL-03**: HTML brief body renders correctly through enterprise email API
- [ ] **MAIL-04**: Sender configured as Kevin Taylor via impersonatedEmail or permittedEmailImpersonation

### Fallback & Reliability

- [ ] **FALL-01**: When Factiva API is unavailable, pipeline falls back to Apify + RSS collection
- [ ] **FALL-02**: When enterprise email API is unavailable, pipeline falls back to Graph API delivery
- [ ] **FALL-03**: When Equity Price API is unavailable, briefs generate without price data
- [ ] **FALL-04**: All fallback events are logged with structured logging and visible in admin dashboard

### Admin Dashboard

- [ ] **ADMN-01**: Admin can view enterprise API connection status (healthy/degraded/offline)
- [ ] **ADMN-02**: Admin can configure API keys and credentials for enterprise APIs
- [ ] **ADMN-03**: Admin can view which articles came from Factiva vs Apify/RSS

## v2 Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Data API

- **DATA-01**: System queries MMC Core Data API for additional market intelligence
- **DATA-02**: Data API content enriches classification and report generation

### Access Management (Full Scope)

- **ACMG-01**: Full user auth flow via Access Management API (authorization code grant with PKCE)
- **ACMG-02**: Per-user admin dashboard access with enterprise SSO

## Out of Scope

| Feature | Reason |
|---------|--------|
| coreapi-data integration | Deferred to future milestone, not needed for core brief enrichment |
| Full access-management features | Only client credentials grant needed; user auth deferred |
| Historical stock quotes | Equity Price API provides current quotes only; not designed for historical data |
| Dedicated equity market section | Equity data shown inline with stories per user preference |
| Real-time news alerts from Factiva | Daily batch collection aligns with existing brief cadence |
| Factiva saved searches | Using search API directly; saved search management adds complexity without value |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 9 | Pending |
| AUTH-02 | Phase 9 | Pending |
| AUTH-03 | Phase 9 | Pending |
| NEWS-01 | Phase 10 | Pending |
| NEWS-02 | Phase 10 | Pending |
| NEWS-03 | Phase 10 | Pending |
| NEWS-04 | Phase 10 | Pending |
| NEWS-05 | Phase 10 | Pending |
| NEWS-06 | Phase 10 | Pending |
| EQTY-01 | Phase 11 | Pending |
| EQTY-02 | Phase 11 | Pending |
| EQTY-03 | Phase 11 | Pending |
| EQTY-04 | Phase 11 | Pending |
| MAIL-01 | Phase 12 | Pending |
| MAIL-02 | Phase 12 | Pending |
| MAIL-03 | Phase 12 | Pending |
| MAIL-04 | Phase 12 | Pending |
| FALL-01 | Phase 10 | Pending |
| FALL-02 | Phase 12 | Pending |
| FALL-03 | Phase 11 | Pending |
| FALL-04 | Phase 13 | Pending |
| ADMN-01 | Phase 13 | Pending |
| ADMN-02 | Phase 13 | Pending |
| ADMN-03 | Phase 13 | Pending |

**Coverage:**
- v1.1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-02-18*
*Last updated: 2026-02-18 — traceability complete after roadmap creation*
