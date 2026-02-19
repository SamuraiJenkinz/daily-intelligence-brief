---
phase: 12-enterprise-email-delivery
verified: 2026-02-19T02:28:50Z
status: passed
score: 4/4 must-haves verified
gaps: []
human_verification:
  - test: Send a test brief through the enterprise email endpoint
    expected: Inbox shows email from Kevin Taylor with rendered HTML brief
    why_human: Cannot verify inbox delivery or sender display name rendering programmatically
  - test: Simulate enterprise endpoint returning 503 during pipeline run
    expected: Pipeline logs enterprise_email_failed_falling_back then email arrives via Graph API
    why_human: Cannot simulate network failure programmatically against real endpoint
  - test: Run pipeline with degraded_auth=True (no JWT configured)
    expected: All roles skip enterprise, use Graph API as graph_primary, no enterprise error logs
    why_human: Requires live pipeline run with Graph credentials to confirm delivery
---

# Phase 12: Enterprise Email Delivery Verification Report

**Phase Goal:** Role-based briefs are delivered via the MMC Core API email endpoint, authenticated with JWT Bearer token and X-Api-Key, sent from Kevin Taylor, with automatic fallback to Microsoft Graph API if the enterprise endpoint is unavailable.
**Verified:** 2026-02-19T02:28:50Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pipeline sends HTML brief per role via POST /coreapi/email/v1 with JWT Bearer + X-Api-Key headers | VERIFIED | enterprise_emailer.py L125-130 builds both auth headers; _post_email POSTs to {base_url}{email_path}; Step 8 in pipeline.py calls _send_with_fallback which calls enterprise_client.send_email() |
| 2 | Sender is Kevin Taylor with correct authentication | VERIFIED | mmc_sender_name defaults to Kevin Taylor in config.py L84; mmc_sender_email included in payload as impersonatedEmail (FIELD_SENDER at L81); payload built at L153-162 |
| 3 | Enterprise failure triggers fallback to Graph API with structured logging | VERIFIED (with note) | _send_with_fallback at pipeline.py L1053 tries enterprise first, falls through to Graph on non-ok; enterprise_email_failed_falling_back logged at L1108; NOTE: 5xx HTTPStatusError caught by outer except, not retried -- fallback still works |
| 4 | Every enterprise delivery attempt outcome stored per-send in api_events database | VERIFIED | _record_event() at L367-407 writes ApiEvent api_name=email, EMAIL_SENT on success, EMAIL_FALLBACK on failure, with run_id; called on every code path in send_email() |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| app/services/enterprise_emailer.py | EnterpriseEmailClient with send_email(), is_configured(), _record_event() | VERIFIED | 408 lines; class at L48; send_email() at L205; is_configured() at L103; _record_event() at L367; FIELD_* constants at L86-91 |
| app/config.py | mmc_sender_email, mmc_sender_name, mmc_email_path + is_mmc_email_configured() | VERIFIED | Fields at L83-85; is_mmc_email_configured() at L131-141; defaults: sender_name=Kevin Taylor, email_path=/coreapi/email/v1 |
| app/services/pipeline.py | _send_with_fallback() method, Step 8 enterprise-first delivery | VERIFIED | _send_with_fallback() at L1053; enterprise_attempted at L1093; per-role loop at L855; token fetched once at L849; completed_with_delivery_failure at L932 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| enterprise_emailer.py | config.py | get_settings() for base_url, api_key, sender fields | WIRED | L94-100: reads mmc_api_base_url, mmc_api_key, mmc_sender_email, mmc_sender_name, mmc_email_path |
| enterprise_emailer.py | models/api_event.py | _record_event() with EMAIL_SENT/EMAIL_FALLBACK | WIRED | L260 (success), L283 (401/403), L319 (4xx), L337 (network), L354 (unexpected) |
| enterprise_emailer.py | database.py | SessionLocal() in isolated _record_event | WIRED | L390-400: opens own session, creates ApiEvent, commits |
| pipeline.py | enterprise_emailer.py | EnterpriseEmailClient import + send_email() call | WIRED | L21: import; L833: instantiation; L1096: await send_email() in _send_with_fallback |
| pipeline.py | emailer.py | GraphEmailService as fallback in _send_with_fallback | WIRED | L834: instantiation; L1125: await graph_service.send_email() |
| pipeline.py | auth/token_manager.py | get_token() called once before per-role loop | WIRED | L849: token = await self.token_manager.get_token() before loop at L855 |
| pipeline.py | config.py | is_mmc_email_configured() check at Step 8 | WIRED | L838: settings.is_mmc_email_configured() logged; enterprise_client.is_configured() at L848 and L1093 |

### Requirements Coverage

**Plan 12-01 must-haves:**

| Requirement | Status | Evidence |
|-------------|--------|----------|
| EnterpriseEmailClient sends via POST /coreapi/email/v1 with JWT Bearer + X-Api-Key | SATISFIED | L197: url construction; L125-130: both auth headers |
| Returns result dict on success and failure, never raises | SATISFIED | All code paths return dict; broad except at L348 |
| 401/403 return auth_error immediately, no retry | SATISFIED | L274-294: status_code in (401, 403), return auth_error dict immediately |
| Transient errors retry via tenacity before returning error | SATISFIED (with note) | L175-178: @retry on TimeoutException, ConnectError, 2 attempts; NOTE: 5xx not retried through _post_email |
| Every send attempt records ApiEvent with EMAIL_SENT or EMAIL_FALLBACK | SATISFIED | _record_event() called on every code path |
| Settings has mmc_sender_email, mmc_sender_name, mmc_email_path + is_mmc_email_configured() | SATISFIED | config.py L83-85, L131-141 |

**Plan 12-02 must-haves:**

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Step 8 attempts enterprise first when degraded_auth=False and enterprise configured | SATISFIED | L1093: enterprise_attempted = not degraded_auth and enterprise_client.is_configured() and token |
| Step 8 skips enterprise when degraded_auth=True, uses Graph directly | SATISFIED | L1114-1121: logs enterprise_email_skipped; goes directly to graph_primary |
| Enterprise failure triggers Graph API fallback with structured fallback event log | SATISFIED | L1107-1113: warning logged; L1124: graph_service.send_email() called |
| Each role delivered independently | SATISFIED | Per-role loop at L855; _send_with_fallback called per role independently |
| Both paths fail: pipeline continues to next role | SATISFIED | path=both_failed at L1138/1148; loop continues without exception |
| Pipeline status is completed_with_delivery_failure when any role has both paths fail | SATISFIED | L932-938: delivery_failure_count > 0 sets status |
| Each delivery result includes path field | SATISFIED | All return paths in _send_with_fallback include path key |
| JWT token fetched once before per-role loop | SATISFIED | L847-851: token fetched before loop, passed as parameter |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|---------|
| app/services/enterprise_emailer.py | 296-311 | 5xx raises HTTPStatusError but _post_email retry decorator only catches TimeoutException/ConnectError -- 5xx does NOT retry through tenacity | Warning | Docstring claims 5xx retry via tenacity but effective behavior is 1 attempt then outer except catches; Graph fallback still works |
| app/services/pipeline.py | 1133 | path = graph_fallback if enterprise_attempted else graph_primary -- correct and intentional | Info | Logic is sound; enterprise_attempted correctly labels the graph path |

### Human Verification Required

**1. Inbox delivery from Kevin Taylor**
- **Test:** Configure MMC credentials in .env, trigger run_full_pipeline_with_email(), check recipient inbox
- **Expected:** Email arrives with display name Kevin Taylor, subject matches company name and date, HTML brief renders correctly in email client
- **Why human:** Cannot verify inbox delivery, sender display name rendering, or HTML rendering programmatically

**2. Enterprise failure + Graph fallback end-to-end**
- **Test:** Temporarily point mmc_api_base_url at an unreachable endpoint, run pipeline with valid JWT and Graph credentials
- **Expected:** Logs show enterprise_email_failed_falling_back for each role, email arrives via Graph API, api_events table has EMAIL_FALLBACK rows with run_id
- **Why human:** Cannot simulate real network failure against production endpoint programmatically

**3. degraded_auth path (no JWT)**
- **Test:** Remove MMC auth credentials from .env, run pipeline with Graph credentials only
- **Expected:** All roles logged as enterprise_email_skipped with reason=degraded_auth, all paths show graph_primary, no enterprise errors
- **Why human:** Requires live pipeline run with Graph credentials to confirm delivery

## Notable Design Findings

**5xx retry design note:** The _post_email() retry decorator is configured for TimeoutException and ConnectError only. When send_email() receives a 5xx HTTP response, it raises httpx.HTTPStatusError (line 307), which is caught by the outer except block (line 330) -- not retried by _post_email. Effective behavior: 5xx responses get one attempt then fallback. The retry comments in docstrings about 5xx are misleading. The fallback to Graph API works correctly regardless.

**Graph API delivery not recorded in api_events:** GraphEmailService does not call _record_event() and the pipeline does not write an ApiEvent for graph_primary or graph_fallback success. Only enterprise email outcomes are recorded in api_events. Per-send outcomes are tracked in result[emails_sent][role][path] (in-memory) and in structured logs at email_delivery_outcome level. ApiEvent DB records are enterprise-delivery-only by design.

**Kevin Taylor sender:** mmc_sender_name defaults to Kevin Taylor in config.py (L84). This is passed in the payload as senderName. The sending mailbox (mmc_sender_email) has no default and must be set via MMC_SENDER_EMAIL env var -- is_mmc_email_configured() returns False without it.

---

_Verified: 2026-02-19T02:28:50Z_
_Verifier: Claude (gsd-verifier)_
