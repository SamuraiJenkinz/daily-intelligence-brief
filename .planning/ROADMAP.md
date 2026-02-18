# Roadmap: MDInsights

## Milestones

- [x] **v1.0 MVP** — Phases 1-8 (shipped 2026-02-08)
- [ ] **v1.1 Enterprise API Integration** — Phases 9-13 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-8) — SHIPPED 2026-02-08</summary>

- [x] Phase 1: Vertical Slice Foundation (5/5 plans) — completed 2026-02-06
- [x] Phase 2: News Collection at Scale (6/6 plans) — completed 2026-02-07
- [x] Phase 3: Advanced Classification Pipeline (3/3 plans) — completed 2026-02-07
- [x] Phase 4: Intelligence Report Generation (7/7 plans) — completed 2026-02-07
- [x] Phase 5: Automated Delivery System (4/4 plans) — completed 2026-02-07
- [x] Phase 6: Admin Dashboard (5/5 plans) — completed 2026-02-08
- [x] Phase 7: Production Hardening (5/5 plans) — completed 2026-02-08
- [x] Phase 8: Polish and Launch (4/4 plans) — completed 2026-02-08

See: `.planning/milestones/v1.0-ROADMAP.md` for full details.

</details>

### v1.1 Enterprise API Integration

**Milestone Goal:** Replace web scraping with Factiva as the primary news source, enrich briefs with inline equity price data, switch email delivery to the MMC Core API enterprise proxy, and surface API health in the admin dashboard — all with graceful fallback to the proven v1.0 infrastructure.

- [x] **Phase 9: OAuth2 Token Management** — Acquire and cache JWT tokens for the MMC Core API platform
- [x] **Phase 10: Factiva News Collection** — Factiva as primary news source with Apify/RSS fallback
- [ ] **Phase 11: Equity Price Enrichment** — Inline price data for tracked companies in the brief
- [ ] **Phase 12: Enterprise Email Delivery** — Send briefs via MMC Core API email with Graph API fallback
- [ ] **Phase 13: Admin Dashboard Enterprise Status** — API health, credential config, source attribution, fallback log

---

#### Phase 9: OAuth2 Token Management

**Goal**: The pipeline can authenticate to the MMC Core API platform, acquiring and refreshing JWT tokens automatically without human intervention. JWT is required for Email delivery (Phase 12); Factiva and Equity APIs use X-Api-Key only (no JWT). This phase builds the auth foundation that Phases 10-13 depend on.

**Depends on**: Phase 8 (existing production pipeline)

**Requirements**: AUTH-01, AUTH-02, AUTH-03

**Success Criteria** (what must be TRUE):
1. The pipeline acquires a valid JWT token from the Access Management API using client credentials on startup.
2. Tokens are cached in memory and automatically refreshed before expiry without restarting the pipeline.
3. When token acquisition fails, the pipeline logs the failure with structured context, sets a degraded-auth flag, and continues using v1.0 delivery (Graph API) rather than halting.
4. A standalone test command demonstrates successful token acquisition and refresh against the staging endpoint.

**Plans:** 2 plans

Plans:
- [x] 09-01-PLAN.md — TokenManager module, ApiEvent model, config extension, and auth test command
- [x] 09-02-PLAN.md — Integrate token manager into pipeline startup with degraded-auth flag and health check reporting

---

#### Phase 10: Factiva News Collection

**Goal**: The pipeline fetches insurance/reinsurance news from Factiva as its primary source each morning, with Apify/RSS running automatically as fallback when Factiva is unavailable, and article source stored per-article.

**Depends on**: Phase 9 (X-Api-Key auth for News API does not require JWT; Phase 9 still precedes to establish auth infrastructure)

**Requirements**: NEWS-01, NEWS-02, NEWS-03, NEWS-04, NEWS-05, NEWS-06, FALL-01

**Success Criteria** (what must be TRUE):
1. The morning pipeline run queries Factiva with configured insurance industry and company codes and returns articles with headline, snippet, plaintext, publication date, and source URL.
2. Factiva articles are deduplicated against the existing article store — no duplicates appear in the brief.
3. Factiva articles flow through the existing AI classification pipeline unchanged and appear in the generated brief exactly as Apify-sourced articles do.
4. When Factiva returns an error or is unreachable, the pipeline automatically collects from Apify/RSS instead, logs a structured fallback event, and the brief generates normally.
5. Each article record in the database carries a source field indicating whether it came from Factiva or Apify/RSS.

**Plans:** 3 plans

Plans:
- [x] 10-01-PLAN.md — FactivaCollector module, FactivaConfig model, collector_source field, startup migration
- [x] 10-02-PLAN.md — Pipeline integration with Factiva-primary/Apify-fallback, source attribution in reporter and templates
- [x] 10-03-PLAN.md — Admin Factiva config UI and staging endpoint validation

---

#### Phase 11: Equity Price Enrichment

**Goal**: Articles about tracked public companies appear in the brief with the company's current equity price and daily change displayed inline alongside the story, with no disruption to brief generation when price data is unavailable.

**Depends on**: Phase 10 (classified articles must exist to enrich; X-Api-Key auth for Equity API)

**Requirements**: EQTY-01, EQTY-02, EQTY-03, EQTY-04, FALL-03

**Success Criteria** (what must be TRUE):
1. An admin-configurable entity-to-ticker mapping associates company names (as extracted by AI classification) with exchange and ticker symbols.
2. After AI classification, articles mentioning tracked entities are automatically enriched with current price, daily change amount, and daily change percent before brief generation.
3. Enriched equity data appears inline alongside the relevant story in the HTML brief — not in a separate section.
4. When equity price lookup fails for any entity (API error, timeout, unmapped ticker), the brief generates normally with that story's equity fields absent and the failure logged.

**Plans**: TBD

Plans:
- [ ] 11-01: Build entity-to-ticker mapping store and Equity Price API client with fallback handling
- [ ] 11-02: Integrate equity enrichment step into the post-classification, pre-report pipeline stage
- [ ] 11-03: Update HTML brief template and Jinja2 context to render inline equity data alongside article entries

---

#### Phase 12: Enterprise Email Delivery

**Goal**: Role-based briefs are delivered via the MMC Core API email endpoint, authenticated with JWT Bearer token and X-Api-Key, sent from Kevin Taylor, with automatic fallback to Microsoft Graph API if the enterprise endpoint is unavailable.

**Depends on**: Phase 9 (JWT token required), Phase 11 (final brief content ready)

**Requirements**: MAIL-01, MAIL-02, MAIL-03, MAIL-04, FALL-02

**Success Criteria** (what must be TRUE):
1. The pipeline sends the HTML brief for each role via POST /coreapi/email/v1 with JWT Bearer and X-Api-Key authentication headers.
2. Recipient inboxes receive emails from Kevin Taylor as sender, with the HTML brief rendering correctly and completely.
3. When the enterprise email endpoint errors or is unreachable, the pipeline retries, then falls back to Microsoft Graph API delivery and logs a structured fallback event.
4. Each delivery attempt outcome (enterprise success, fallback triggered, complete failure) is stored per-send in the database.

**Plans**: TBD

Plans:
- [ ] 12-01: Implement enterprise email client (POST /coreapi/email/v1, JWT Bearer + X-Api-Key, sender impersonation, HTML body)
- [ ] 12-02: Integrate enterprise email client into delivery pipeline with Graph API fallback and outcome recording

---

#### Phase 13: Admin Dashboard Enterprise Status

**Goal**: Administrators can see real-time health of all enterprise API connections, configure credentials without touching config files, identify per-article whether the source was Factiva or Apify/RSS, and review a log of all fallback events — from the existing admin dashboard.

**Depends on**: Phase 12 (all enterprise APIs integrated and instrumented)

**Requirements**: ADMN-01, ADMN-02, ADMN-03, FALL-04

**Success Criteria** (what must be TRUE):
1. The admin dashboard displays a status panel showing healthy/degraded/offline for each enterprise API (Auth, News, Equity, Email), updated on each pipeline run.
2. An admin can update API keys and credentials for enterprise APIs through the dashboard and the pipeline uses the new values on the next run.
3. The report archive view shows a source badge per article (Factiva or Apify/RSS) without additional clicks.
4. A fallback event log in the dashboard lists each fallback trigger with the affected API, timestamp, and reason from structured log data.

**Plans**: TBD

Plans:
- [ ] 13-01: Add enterprise API status panel and credential configuration UI to admin dashboard
- [ ] 13-02: Add article source attribution display in report archive and fallback event log view

---

## Progress

**Execution Order:**
Phases execute in numeric order: 9 -> 10 -> 11 -> 12 -> 13

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Vertical Slice Foundation | v1.0 | 5/5 | Complete | 2026-02-06 |
| 2. News Collection at Scale | v1.0 | 6/6 | Complete | 2026-02-07 |
| 3. Advanced Classification Pipeline | v1.0 | 3/3 | Complete | 2026-02-07 |
| 4. Intelligence Report Generation | v1.0 | 7/7 | Complete | 2026-02-07 |
| 5. Automated Delivery System | v1.0 | 4/4 | Complete | 2026-02-07 |
| 6. Admin Dashboard | v1.0 | 5/5 | Complete | 2026-02-08 |
| 7. Production Hardening | v1.0 | 5/5 | Complete | 2026-02-08 |
| 8. Polish and Launch | v1.0 | 4/4 | Complete | 2026-02-08 |
| 9. OAuth2 Token Management | v1.1 | 2/2 | Complete | 2026-02-18 |
| 10. Factiva News Collection | v1.1 | 3/3 | Complete | 2026-02-18 |
| 11. Equity Price Enrichment | v1.1 | 0/3 | Not started | - |
| 12. Enterprise Email Delivery | v1.1 | 0/2 | Not started | - |
| 13. Admin Dashboard Enterprise Status | v1.1 | 0/2 | Not started | - |

**Total:** 44/51 plans complete (v1.0 done, v1.1 Phases 9-10 complete)
