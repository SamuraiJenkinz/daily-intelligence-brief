# Requirements: MDInsights

**Defined:** 2026-02-18
**Core Value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.

## v1.1 Requirements

Requirements for enterprise API integration milestone. Each maps to roadmap phases.

### Authentication

- [x] **AUTH-01**: System acquires JWT tokens via OAuth2 client credentials grant from Access Management API
- [x] **AUTH-02**: System caches tokens and auto-refreshes before expiry
- [x] **AUTH-03**: Token acquisition failures are logged and don't block the pipeline (fallback to v1.0 delivery)

### News Collection

- [x] **NEWS-01**: System searches Factiva for insurance industry news via /coreapi/recent-news/v1/search
- [x] **NEWS-02**: System uses Factiva industry and company codes for targeted insurance/reinsurance queries
- [x] **NEWS-03**: System extracts article content (headline, snippet, plaintext, publication date, source URL)
- [x] **NEWS-04**: System deduplicates Factiva articles against existing article store
- [x] **NEWS-05**: Factiva articles flow through existing AI classification pipeline unchanged
- [x] **NEWS-06**: Factiva is the primary news source; Apify/RSS run as secondary fallback

### Equity Enrichment

- [x] **EQTY-01**: System maintains a configurable mapping of tracked entities to ticker symbols and exchanges
- [x] **EQTY-02**: System fetches current equity prices for entities mentioned in classified articles
- [x] **EQTY-03**: Equity data (price, change, percent) appears inline with relevant stories in the brief
- [x] **EQTY-04**: Missing or failed equity lookups don't break the brief

### Email Delivery

- [x] **MAIL-01**: System sends role-based briefs via POST /coreapi/email/v1
- [x] **MAIL-02**: System authenticates to Email API with JWT Bearer token + X-Api-Key
- [x] **MAIL-03**: HTML brief body renders correctly through enterprise email API
- [x] **MAIL-04**: Sender configured as Kevin Taylor via impersonatedEmail or permittedEmailImpersonation

### Fallback & Reliability

- [x] **FALL-01**: When Factiva API is unavailable, pipeline falls back to Apify + RSS collection
- [x] **FALL-02**: When enterprise email API is unavailable, pipeline falls back to Graph API delivery
- [x] **FALL-03**: When Equity Price API is unavailable, briefs generate without price data
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
| AUTH-01 | Phase 9 | Complete |
| AUTH-02 | Phase 9 | Complete |
| AUTH-03 | Phase 9 | Complete |
| NEWS-01 | Phase 10 | Complete |
| NEWS-02 | Phase 10 | Complete |
| NEWS-03 | Phase 10 | Complete |
| NEWS-04 | Phase 10 | Complete |
| NEWS-05 | Phase 10 | Complete |
| NEWS-06 | Phase 10 | Complete |
| EQTY-01 | Phase 11 | Complete |
| EQTY-02 | Phase 11 | Complete |
| EQTY-03 | Phase 11 | Complete |
| EQTY-04 | Phase 11 | Complete |
| MAIL-01 | Phase 12 | Complete |
| MAIL-02 | Phase 12 | Complete |
| MAIL-03 | Phase 12 | Complete |
| MAIL-04 | Phase 12 | Complete |
| FALL-01 | Phase 10 | Complete |
| FALL-02 | Phase 12 | Complete |
| FALL-03 | Phase 11 | Complete |
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
*Last updated: 2026-02-19 — Phase 12 requirements (MAIL-01/02/03/04, FALL-02) marked Complete*
