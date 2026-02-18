---
phase: 10-factiva-news-collection
plan: 02
subsystem: api
tags: [factiva, pipeline, collector, apify, rss, news, attribution, jinja2, sqlalchemy]

# Dependency graph
requires:
  - phase: 10-01
    provides: FactivaCollector class, FactivaConfig ORM model, collector_source column on NewsArticle
  - phase: 09-02
    provides: Pipeline integration patterns, Step 0 auth prefix, run_full_pipeline_with_email structure

provides:
  - Factiva-primary pipeline Step 1 with Apify/RSS fallback scoped to INSURANCE_FALLBACK_SOURCES
  - source_name_filter param on ApifyCollector.collect_from_sources()
  - store_factiva_articles() method on ApifyCollector for Factiva article persistence
  - collector_source propagated through article lifecycle (storage -> reporter -> templates)
  - Factiva-first sort within each priority group in role briefs
  - Source badges ("via Factiva" / "via Apify/RSS") in browser brief and email templates
  - Admin dashboard Source column showing per-run Factiva vs Apify/RSS article counts
  - NEWS_FALLBACK ApiEvent recorded on Factiva failure

affects:
  - 10-03 (Factiva admin config UI — uses FactivaConfig and factiva_used flow)
  - 11 (Equity data inline — pipeline result dict now includes collection_source)
  - 13 (Admin dashboard enhancements — source breakdown data already wired)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Factiva-primary with scoped Apify/RSS fallback — INSURANCE_FALLBACK_SOURCES constant filters fallback to 4 focused sources
    - URL dedup against today's existing articles before Factiva storage — handles pipeline reruns
    - collector_source propagated as article dict field through storage, reporter, and templates
    - store_factiva_articles() creates its own Run record — Factiva collection is a first-class run
    - NEWS_FALLBACK ApiEvent on failure — audit trail for dashboard reporting in Phase 13

key-files:
  created: []
  modified:
    - app/services/pipeline.py
    - app/services/collector.py
    - app/services/reporter.py
    - app/templates/role_brief.html
    - app/templates/email/role_email.html
    - app/templates/admin/dashboard.html
    - app/routers/admin.py

key-decisions:
  - "INSURANCE_FALLBACK_SOURCES hardcoded list — 4 insurance-specific Apify/RSS sources run during fallback, general business sources excluded"
  - "Zero Factiva articles treated as failure and triggers fallback — not low-volume signal, indicates API or query breakage"
  - "store_factiva_articles() creates its own Run record — Factiva collection owns its run, not shared with Apify flow"
  - "URL dedup uses date(NewsArticle.created_at) == today — handles pipeline reruns within same day"
  - "collector_source=None in DB treated as 'Apify/RSS' in reporter via getattr fallback — backward-compatible for pre-Phase-10 articles"

patterns-established:
  - "Collector source attribution: article dicts carry collector_source from collection through storage to template rendering"
  - "Factiva-first secondary sort: sort key tuple (priority_order, 0 if Factiva else 1) — Factiva first within each priority group"
  - "Admin source breakdown: per-run group_by(collector_source) query surfaces Factiva vs Apify/RSS split in dashboard"

# Metrics
duration: 16min
completed: 2026-02-18
---

# Phase 10 Plan 02: Pipeline Integration Summary

**Factiva-primary Step 1 pipeline with insurance-focused Apify/RSS fallback, collector_source attribution through storage/reporter/templates, and per-run source breakdown in admin dashboard**

## Performance

- **Duration:** 16 min
- **Started:** 2026-02-18T18:55:25Z
- **Completed:** 2026-02-18T19:10:30Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Pipeline Step 1 now attempts FactivaCollector first in both run_full_pipeline() and run_full_pipeline_with_email(); falls back to insurance-focused Apify/RSS on any failure with NEWS_FALLBACK event recorded
- collector_source flows from article dict through _store_articles(), _prepare_articles(), and into both brief templates as "via Factiva" (blue badge) or "via Apify/RSS" (gray badge)
- Admin dashboard shows per-run source breakdown (e.g., "12 Factiva" or "15 Apify/RSS") via group_by query on collector_source per run

## Task Commits

Each task was committed atomically:

1. **Task 1: Pipeline restructure — Factiva primary with Apify/RSS fallback, dedup, and source attribution in storage** - `bae8cca` (feat)
2. **Task 2: Source attribution display — reporter sort, brief badges, admin dashboard source breakdown** - `efb3a18` (feat)

## Files Created/Modified

- `app/services/pipeline.py` - Added FactivaCollector imports, INSURANCE_FALLBACK_SOURCES constant, Factiva-primary Step 1 logic in both pipeline methods, collection_source in result dict and summary log
- `app/services/collector.py` - Added source_name_filter param to collect_from_sources(), collector_source field set in _store_articles(), new store_factiva_articles() method
- `app/services/reporter.py` - Added collector_source to _prepare_articles() dict, updated filter_articles_by_role() sort for Factiva-first within priority
- `app/templates/role_brief.html` - Added "via Factiva" / "via Apify/RSS" source badge after source-tag span in article cards
- `app/templates/email/role_email.html` - Added inline-styled source badges (email-compatible, no CSS classes)
- `app/templates/admin/dashboard.html` - Added Source column to recent runs table with Factiva/Apify/RSS badge display
- `app/routers/admin.py` - Added per-run source_breakdown query (group_by collector_source) in get_admin_dashboard()

## Decisions Made

- INSURANCE_FALLBACK_SOURCES is a hardcoded list of 4 sources (Reinsurance News, Insurance Journal, Artemis, Lloyd's List) — keeps fallback brief focused on insurance; general business sources excluded during fallback
- Zero Factiva articles triggers fallback — consistent with the design rationale that zero results signals API/query breakage, not low volume
- store_factiva_articles() creates its own Run record rather than sharing the ApifyCollector's Run — Factiva collection is independently traceable in the runs table
- URL dedup queries date(created_at) == today (not published_at) — avoids re-storing articles if pipeline is manually re-run within the same day
- collector_source=None in DB treated as 'Apify/RSS' via getattr fallback in reporter — all pre-Phase-10 articles get the correct badge without a DB migration

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. Factiva credentials are already set via mmc_api_base_url and mmc_api_key from Phase 10-01.

## Next Phase Readiness

- Pipeline integration complete — FactivaCollector is the primary news source when configured
- Fallback to insurance-focused Apify/RSS sources works transparently
- Phase 10-03 (Factiva admin config UI) can now surface FactivaConfig row editing since the pipeline reads from it
- Source attribution visible in all output surfaces (browser brief, email, admin dashboard)
- No blockers for Phase 11 (Equity data inline) — collection_source in result dict is already available

---
*Phase: 10-factiva-news-collection*
*Completed: 2026-02-18*
