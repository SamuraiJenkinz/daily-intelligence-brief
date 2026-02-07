# Requirements: MDInsights

**Defined:** 2026-02-06
**Core Value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.

## v1 Requirements

### Collection

- [ ] **COLL-01**: System scrapes 18+ global insurance/reinsurance news sources via Apify actors
- [ ] **COLL-02**: System ingests RSS feeds from major publications as secondary source
- [ ] **COLL-03**: System deduplicates articles across sources using content similarity
- [ ] **COLL-04**: System monitors source health and alerts when a source stops returning articles
- [ ] **COLL-05**: System stores collected articles in SQLite with timestamps and source metadata

### Classification

- [ ] **CLSF-01**: AI assigns priority tier to each article (Critical / High / Medium / Monitor)
- [ ] **CLSF-02**: AI tags each article with relevant audience roles (Brokers / Leadership / Compliance / Underwriting)
- [ ] **CLSF-03**: AI extracts entities (companies, people, organisations) from each article
- [ ] **CLSF-04**: AI assigns sentiment (positive / negative / neutral), impact level, category, region, and business line per article
- [ ] **CLSF-05**: Classification uses Azure OpenAI GPT-4o with structured output

### Report Generation

- [ ] **REPT-01**: System generates a single HTML brief with clickable role tabs (Brokers, Leadership, Compliance, Underwriting)
- [ ] **REPT-02**: Each role tab shows only articles relevant to that audience, priority-ranked
- [ ] **REPT-03**: AI generates a tailored executive summary per role tab
- [ ] **REPT-04**: Brief includes sector heatmap with directional signals
- [ ] **REPT-05**: Brief includes entity tracker with mention counts across the edition
- [ ] **REPT-06**: Brief includes "What to Watch" forward-looking section with timeframes
- [ ] **REPT-07**: Brief includes market pulse bar with at-a-glance sector indicators
- [ ] **REPT-08**: Brief includes sentiment, impact, entity, region, and business line chips per story
- [ ] **REPT-09**: Brief matches Marsh visual identity (prototype styling)
- [ ] **REPT-10**: Brief attributes authorship to Kevin Taylor, Colleague Technology Services

### Delivery

- [ ] **DELV-01**: System sends single HTML email per edition via Microsoft Graph API
- [ ] **DELV-02**: Email is delivered daily before market open (08:00 local)
- [ ] **DELV-03**: System runs on Windows Task Scheduler for automated daily execution

### Admin

- [ ] **ADMN-01**: Admin can add, edit, and disable news sources via web UI
- [ ] **ADMN-02**: Admin can manage recipients and their role assignments
- [ ] **ADMN-03**: Admin can view report archive and search past articles
- [ ] **ADMN-04**: Admin can manually trigger a brief generation on demand
- [ ] **ADMN-05**: Admin dashboard uses HTMX for SPA-like experience (matching BrasilIntel pattern)

## v2 Requirements

### Enhanced Intelligence

- **INTL-01**: Story continuity tracking across editions (developing stories linked)
- **INTL-02**: Historical trend analysis after 6+ months of data
- **INTL-03**: Automated competitive battlecards from accumulated intelligence
- **INTL-04**: PDF attachment option alongside HTML email

### Enhanced Distribution

- **DIST-01**: Configurable delivery schedule (twice daily option)
- **DIST-02**: Critical-priority real-time alerts outside daily brief
- **DIST-03**: Custom role definitions beyond the initial four

### Enhanced Admin

- **EADM-01**: Source scraping performance analytics dashboard
- **EADM-02**: AI classification accuracy monitoring and drift detection
- **EADM-03**: Recipient engagement tracking (open rates, click-through)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile app | HTML email is mobile-responsive by design |
| Multi-tenant / SaaS | Single Marsh deployment |
| Brazilian insurer monitoring | BrasilIntel's domain |
| Social media monitoring | Traditional media and wire services only for v1 |
| Real-time chat / collaboration | Email delivery sufficient for audience |
| Custom report designer | Templates fixed to Marsh branding |
| Portuguese language support | Global English-language sources |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COLL-01 | Phase 1 (partial), Phase 2 | Complete |
| COLL-02 | Phase 2 | Complete |
| COLL-03 | Phase 2 | Complete |
| COLL-04 | Phase 2, Phase 7 (enhanced) | Complete |
| COLL-05 | Phase 1 (partial), Phase 2 | Complete |
| CLSF-01 | Phase 3 | Complete |
| CLSF-02 | Phase 1 | Complete |
| CLSF-03 | Phase 3 | Complete |
| CLSF-04 | Phase 3 | Complete |
| CLSF-05 | Phase 1 (partial), Phase 3 | Complete |
| REPT-01 | Phase 1 (partial), Phase 4 | Pending |
| REPT-02 | Phase 1 (partial), Phase 4 | Pending |
| REPT-03 | Phase 4 | Pending |
| REPT-04 | Phase 4 | Pending |
| REPT-05 | Phase 4 | Pending |
| REPT-06 | Phase 4 | Pending |
| REPT-07 | Phase 4 | Pending |
| REPT-08 | Phase 4 | Pending |
| REPT-09 | Phase 1 (partial), Phase 4, Phase 8 (enhanced) | Pending |
| REPT-10 | Phase 4, Phase 8 (enhanced) | Pending |
| DELV-01 | Phase 5 | Pending |
| DELV-02 | Phase 5 | Pending |
| DELV-03 | Phase 5 | Pending |
| ADMN-01 | Phase 6 | Pending |
| ADMN-02 | Phase 6 | Pending |
| ADMN-03 | Phase 6 | Pending |
| ADMN-04 | Phase 6 | Pending |
| ADMN-05 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 23 (100%)
- Unmapped: 0

**Requirement Distribution by Phase:**
- Phase 1: 6 requirements (partial implementations for vertical slice)
- Phase 2: 5 requirements (full news collection)
- Phase 3: 5 requirements (advanced classification)
- Phase 4: 10 requirements (intelligence report generation)
- Phase 5: 3 requirements (delivery automation)
- Phase 6: 5 requirements (admin dashboard)
- Phase 7: 1 requirement (production hardening enhancement)
- Phase 8: 2 requirements (polish enhancements)

---
*Requirements defined: 2026-02-06*
*Last updated: 2026-02-06 after roadmap creation*
