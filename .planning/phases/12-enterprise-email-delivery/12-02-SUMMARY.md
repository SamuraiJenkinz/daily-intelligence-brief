---
phase: 12-enterprise-email-delivery
plan: 02
subsystem: api
tags: [enterprise-email, graph-api, pipeline, fallback, jwt, structlog, delivery-path]

# Dependency graph
requires:
  - phase: 12-01
    provides: EnterpriseEmailClient with send_email(), is_configured(), Settings.is_mmc_email_configured()
  - phase: 09-enterprise-auth
    provides: TokenManager.get_token() for JWT acquisition
  - phase: 05-email-delivery
    provides: GraphEmailService as fallback delivery path
provides:
  - PipelineOrchestrator._send_with_fallback() method
  - Step 8 enterprise-first delivery with per-role Graph API fallback
  - Per-role delivery path tracking (path field: enterprise/graph_fallback/graph_primary/skipped/both_failed)
  - Pipeline status "completed_with_delivery_failure" for partial delivery outcomes
  - Token fetched once before per-role loop (not per-role)
affects:
  - 13-admin-dashboard (EMAIL_SENT/EMAIL_FALLBACK ApiEvents, delivery path data in result dict)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Enterprise-first delivery: attempt enterprise, fall back to Graph, track path per-role"
    - "Token fetched once before per-role loop to avoid N separate token calls"
    - "Per-role independent fallback: one role failure does not block others"
    - "delivery_failure_count drives status downgrade to completed_with_delivery_failure"
    - "Both paths result in path=both_failed, pipeline continues (reports already archived at Step 7)"

key-files:
  created: []
  modified:
    - app/services/pipeline.py

key-decisions:
  - "enterprise_attempted boolean computed once per call from degraded_auth + is_configured() + token — determines graph path label (graph_fallback vs graph_primary)"
  - "Token fetched once before per-role loop — if token fetch fails, all roles use graph_primary"
  - "delivery_failure_count tracked outside the per-role loop — drives single status check after loop"
  - "path=both_failed is the only path value that increments delivery_failure_count"
  - "Skipped roles (no recipients) get path=skipped, not counted in delivery_failure_count"

patterns-established:
  - "Step 8 uses _send_with_fallback() per role — delivery logic is isolated from loop control flow"
  - "pipeline_summary log now includes enterprise_sent, graph_fallback_sent, graph_primary_sent"
  - "Enterprise configuration logged at Step 8 start for operational visibility"

# Metrics
duration: 8min
completed: 2026-02-19
---

# Phase 12 Plan 02: Pipeline Email Delivery Integration Summary

**Enterprise-first email delivery wired into pipeline Step 8 with per-role Graph API fallback, delivery path tracking, and completed_with_delivery_failure status**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-19T02:20:53Z
- **Completed:** 2026-02-19T02:28:00Z
- **Tasks:** 2/2
- **Files modified:** 1 (pipeline.py)

## Accomplishments

- Added `_send_with_fallback()` async method to PipelineOrchestrator with enterprise-first decision tree
- Replaced legacy Graph-only Step 8 with enterprise-first per-role delivery loop
- JWT token fetched once before loop (not per-role) to avoid redundant token calls
- Per-role independent fallback: each role tries enterprise, falls back to Graph, never blocks others
- Pipeline status downgraded to "completed_with_delivery_failure" when any role has both paths fail
- Delivery path tracking (enterprise/graph_fallback/graph_primary/skipped/both_failed) per role in result dict
- Enterprise configuration status logged at Step 8 start for operational visibility
- pipeline_summary log extended with enterprise_sent/graph_fallback_sent/graph_primary_sent counts

## Task Commits

1. **Task 1: Add _send_with_fallback() method to PipelineOrchestrator** - `2453a82` (feat)
2. **Task 2: Replace Step 8 with enterprise-first delivery** - `3849fe6` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/services/pipeline.py` - Import EnterpriseEmailClient; add _send_with_fallback() method; replace Step 8 with enterprise-first per-role delivery loop; add status downgrade logic; extend pipeline_summary log

## Decisions Made

- **enterprise_attempted computed once per _send_with_fallback() call:** Rather than checking degraded_auth/is_configured/token inline at each branch, computed once as a boolean that also determines the graph path label (graph_fallback vs graph_primary). Clean, readable, consistent.
- **Token fetched once before per-role loop:** Avoids 4 separate TokenManager.get_token() calls (one per role). If token fetch fails, a warning is logged and all roles use graph_primary without re-trying per-role.
- **delivery_failure_count tracked outside loop, checked once after:** Clean separation — loop handles per-role delivery, post-loop logic handles status reporting. No conditional logic inside the loop for pipeline status.
- **path=both_failed is the only value incrementing delivery_failure_count:** Skipped roles (no recipients) are not failures. Graph API success after enterprise failure is graph_fallback (success), not a failure.
- **sync run_full_pipeline() unchanged:** It does not send emails; enterprise email delivery is email-pipeline only.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required beyond what Plan 01 documented.

Deployment validation still needed (from Plan 01):
- Validate FIELD_SENDER ("impersonatedEmail") against real /coreapi/email/v1 API
- Validate FIELD_HTML_BODY ("htmlBody"), FIELD_TO_RECIPIENTS ("toRecipients") field names
- Set MMC_SENDER_EMAIL to the enterprise mailbox to send from
- Staging credentials needed to run scripts/test_auth.py against real endpoint

## Next Phase Readiness

- Phase 12 is complete — enterprise email delivery fully wired into pipeline
- Phase 13 (Admin Dashboard) can use EMAIL_SENT/EMAIL_FALLBACK ApiEvents and per-role delivery path data
- result["emails_sent"][role]["path"] is available for dashboard reporting
- result["status"] = "completed_with_delivery_failure" can be surfaced in dashboard run history

---
*Phase: 12-enterprise-email-delivery*
*Completed: 2026-02-19*
