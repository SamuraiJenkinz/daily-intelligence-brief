# Phase 9: OAuth2 Token Management - Context

**Gathered:** 2026-02-18
**Status:** Ready for planning

<domain>
## Phase Boundary

The pipeline can authenticate to the MMC Core API platform, acquiring and refreshing JWT tokens automatically without human intervention. JWT is required for Email delivery (Phase 12); Factiva and Equity APIs use X-Api-Key only (no JWT). This phase builds the auth foundation that Phases 10-13 depend on.

</domain>

<decisions>
## Implementation Decisions

### Credential management
- Secrets (client_id, client_secret, API keys) stored as environment variables
- `.env.example` template file committed to repo with variable names and comments, no actual secrets
- One set of credentials per deployment — swap values between staging and production at deploy time, no prefix namespacing
- Pipeline validates all required env vars exist and are non-empty on startup — fail fast with clear error message if missing
- Env vars only for Phase 9; Phase 13 will add DB-backed credential config layer (pipeline reads DB, falls back to env vars)
- Token manager built as a standalone module (e.g., `auth/token_manager.py`) importable by any part of the pipeline
- API base URLs, endpoints, and auth details extracted from PDF API docs on disk (NewsAPI.pdf, emailref.pdf, equityref.pdf, wtjref.pdf) during research

### Degraded-auth scope
- JWT failure only degrades Email delivery — Factiva and Equity APIs use X-Api-Key independently and should still be attempted
- Each enterprise API is treated as independently available/degraded — not all-or-nothing
- On JWT failure: set degraded-auth flag, complete the pipeline run with v1.0 Graph API fallback for email, try fresh token on next scheduled run
- No retry within the same run — fail once, flag it, move on
- Degraded-auth flag resets fresh each pipeline run (no persistence across runs)
- Recipients see identical emails regardless of delivery method — no visible difference between enterprise and Graph API delivery

### Auth status visibility
- Claude's Discretion: logging approach (structured logs, console output, or both) based on existing pipeline patterns
- Claude's Discretion: log detail level — balance debugging usefulness with security (never log tokens or secrets)
- Auth events (acquired, refreshed, failed) stored in a general `api_events` database table
- The `api_events` table designed for all enterprise API events (auth, news, equity, email) — Phase 9 creates the table and writes auth events, Phases 10-12 add their own event types, Phase 13 reads from this single table for the dashboard

### Test command experience
- JWT-only test scope — don't test X-Api-Key validity in Phase 9 (Phases 10-11 handle their own)
- Claude's Discretion: invocation method (flag on existing CLI vs separate script) based on project conventions
- Claude's Discretion: output format and detail level based on what's most useful for deployment validation
- Claude's Discretion: exit codes and CI/CD compatibility based on existing project conventions

</decisions>

<specifics>
## Specific Ideas

- PDF API docs on disk are the source of truth for endpoints, auth headers, and base URLs: NewsAPI.pdf, emailref.pdf, equityref.pdf, wtjref.pdf
- Staging environment: mmc-dallas-int-non-prod-ingress.mgti.mmc.com — validate auth against this in Phase 9
- Auth pattern from STATE.md: X-Api-Key for News/Equity, JWT Bearer + X-Api-Key for Email
- Client credentials grant only — no user interaction, server-side pipeline

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-oauth2-token-management*
*Context gathered: 2026-02-18*
