# Phase 12: Enterprise Email Delivery - Context

**Gathered:** 2026-02-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Send role-based HTML briefs via the MMC Core API email endpoint (`POST /coreapi/email/v1`) authenticated with JWT Bearer + X-Api-Key, with automatic fallback to the existing Microsoft Graph API delivery when the enterprise endpoint is unavailable. Delivery outcomes recorded per-send in the database.

</domain>

<decisions>
## Implementation Decisions

### Fallback Scope
- **degraded_auth=True skips enterprise entirely** — no JWT token means go straight to Graph API for all roles, no wasted attempts
- **When both enterprise and Graph fail, pipeline continues** — reports are archived, run status reflects delivery failure, but pipeline does not halt
- Claude's Discretion: per-role vs fail-fast fallback strategy, pipeline status reporting for mixed delivery outcomes, delivery path recording granularity

### Sender Identity
- **Different sender address for enterprise vs Graph API** — enterprise uses a separate email address from the existing Graph sender_email
- **New env var for enterprise sender** — add a config setting (e.g., MMC_SENDER_EMAIL) for the enterprise sender address; set on deployment
- **Display name configurable per path** — enterprise can have its own display name setting separate from Graph API's sender name
- Claude's Discretion: subject line format (keep consistent unless technical reason to change)

### Retry Patience
- **Immediate fallback on 401/403 auth errors** — auth errors won't resolve via retry; matches Phase 9 decision (no retry on 401/403); fall back to Graph immediately
- **When both paths fail, continue without email** — pipeline completes, reports archived, emails not sent, run status reflects 'completed with delivery failure'
- Claude's Discretion: retry count and backoff strategy for non-auth errors, ApiEvent logging pattern for fallback events (follow existing NEWS_FALLBACK/EQUITY_FALLBACK patterns)

### Claude's Discretion
- Fallback strategy: per-role independent fallback vs fail-fast to Graph on first enterprise failure
- Pipeline status reporting when mixed delivery occurs (enterprise for some roles, Graph for others)
- Delivery path recording granularity (per-role delivery method vs simple success/failure)
- Enterprise retry count and backoff timing for transient errors (5xx, timeouts)
- ApiEvent recording for EMAIL_SENT/EMAIL_FALLBACK events (follow existing patterns from Factiva/Equity)
- Subject line consistency across delivery paths

</decisions>

<specifics>
## Specific Ideas

- Enterprise sender address is separate from Graph sender — not the same mailbox; will be configured via new env var on deployment
- Auth error (401/403) = immediate fallback, no retry — consistent with Phase 9 token management decisions
- Pipeline should never halt on email failure — all other work (collection, classification, archiving) is already done by Step 8
- Enterprise email endpoint path (`/coreapi/email/v1`) needs validation against real API on deployment machine (same pattern as Factiva and Equity endpoints)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-enterprise-email-delivery*
*Context gathered: 2026-02-18*
