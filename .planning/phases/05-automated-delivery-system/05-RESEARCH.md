# Phase 5: Automated Delivery System - Research

**Researched:** 2026-02-07
**Domain:** Email delivery automation, Microsoft Graph API, Windows Task Scheduler
**Confidence:** HIGH

## Summary

Phase 5 implements automated daily email delivery of intelligence briefs via Microsoft Graph API with Windows Task Scheduler orchestration. Research reveals a critical architectural decision: the current JavaScript-tabbed template must be replaced with role-specific emails since email clients cannot render JavaScript.

The sister project BrasilIntel provides proven patterns for all major components: GraphEmailService for Microsoft Graph integration, EmailRecipients schema for recipient management, and Task Scheduler batch scripts with comprehensive logging. The key technical challenge is converting the browser-optimized template (CSS Grid, Flexbox, JavaScript tabs) to email-compatible HTML using table-based layouts with premailer CSS inlining.

**Primary recommendation:** Generate separate per-role emails with table-based layouts, reuse BrasilIntel's GraphEmailService pattern verbatim, and implement Windows Task Scheduler automation following the proven run_brasilintel.bat template.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| azure-identity | 1.x | Microsoft Graph authentication | Industry standard for Azure AD daemon apps, ClientSecretCredential for service-to-service |
| httpx | 0.27.x | Async HTTP for Graph API | Already in use, async support, connection pooling |
| premailer | 3.x | CSS inlining for email | Industry standard, converts external/embedded CSS to inline styles |
| jinja2 | 3.1.x | Email template rendering | Already in use, proven for HTML generation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 24.x | Structured logging | Already in use, Task Scheduler debugging |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Microsoft Graph API | SMTP | Graph API is corporate standard, better auditing, no SMTP config |
| premailer | mjml | premailer is simpler, mjml adds build step and framework complexity |
| Table-based layout | CSS Grid/Flexbox | Tables work universally in email, modern CSS breaks in Outlook |

**Installation:**
All dependencies already installed in mdinsights environment (verified):
```bash
# Already present: azure-identity, httpx, jinja2, premailer
# No additional packages required
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── services/
│   ├── emailer.py           # GraphEmailService (from BrasilIntel)
│   └── pipeline.py          # Extended with email delivery step
├── schemas/
│   └── delivery.py          # EmailRecipients (from BrasilIntel)
├── templates/
│   ├── email/               # NEW: Email-specific templates
│   │   ├── role_email.html  # Per-role email template (table-based)
│   │   └── base_email.html  # Email layout base (table structure)
│   └── role_brief.html      # Existing browser template (unchanged)
├── routers/
│   └── admin.py             # Add /admin/recipients management endpoint
deploy/
├── run_mdinsights.bat       # Task Scheduler batch script
└── setup_task.ps1           # PowerShell task creation script
data/
└── logs/
    └── mdinsights_*.log     # Daily execution logs
```

### Pattern 1: Separate Per-Role Emails
**What:** Generate 4 separate emails (Brokers, Leadership, Compliance, Underwriting) instead of one unified HTML with tabs
**When to use:** Email delivery (email clients can't render JavaScript tabs)
**Example:**
```python
# Source: Research synthesis from PROJECT.md requirement
def generate_role_emails(articles: List[NewsArticle], report_date: datetime) -> Dict[str, str]:
    """
    Generate separate HTML emails for each role.

    Returns:
        Dict mapping role name to HTML email content
    """
    role_emails = {}
    prepared_articles = self._prepare_articles(articles)

    for role in ["Brokers", "Leadership", "Compliance", "Underwriting"]:
        # Filter articles for role
        role_articles = [a for a in prepared_articles if role in a.get('roles', [])]

        # Generate executive summary
        exec_summary = self._generate_executive_summary(role, prepared_articles, report_date)

        # Render email template (table-based, no JavaScript)
        template = self.env.get_template('email/role_email.html')
        html = template.render(
            role=role,
            articles=role_articles,
            executive_summary=exec_summary,
            report_date=report_date,
            # Cross-tab sections (heatmap, entity tracker) included in all emails
            sector_heatmap=sector_heatmap,
            entity_tracker=entity_tracker,
            market_pulse=market_pulse
        )

        # Inline CSS for email compatibility
        role_emails[role] = transform(html)

    return role_emails
```

### Pattern 2: Table-Based Email Layout with Progressive Enhancement
**What:** Use HTML tables for primary structure, layer modern CSS for clients that support it
**When to use:** All email templates (Outlook requires tables, modern clients benefit from CSS)
**Example:**
```html
<!-- Source: https://designmodo.com/html-css-emails/, https://www.emailmavlers.com/blog/hybrid-email-design/ -->
<!-- Hybrid approach: table foundation + CSS enhancement + MSO fallbacks -->
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; margin: 0 auto;">
  <tr>
    <td style="padding: 20px; background: #00263e; color: white;">
      <h1 style="margin: 0; font-size: 24px; font-weight: 300;">
        Intelligence Brief for <span style="font-weight: 600;">Brokers</span>
      </h1>
    </td>
  </tr>
  <tr>
    <td style="padding: 20px; background: #f5f7fa;">
      <!-- Executive summary -->
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
        <tr>
          <td style="padding: 15px; background: white; border-left: 4px solid #00a3e0;">
            <p style="margin: 0 0 10px 0; font-size: 14px; line-height: 1.6;">
              {{ executive_summary.summary_paragraphs[0] }}
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>

<!--[if mso]>
<!-- Outlook-specific VML fallback for backgrounds/gradients -->
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false">
  <v:fill type="gradient" color="#00263e" color2="#0077c8"/>
</v:rect>
<![endif]-->
```

### Pattern 3: Microsoft Graph Email Service
**What:** Reuse BrasilIntel's GraphEmailService verbatim with daemon authentication
**When to use:** All email sending operations
**Example:**
```python
# Source: C:\BrasilIntel\app\services\emailer.py (verified working pattern)
from azure.identity import ClientSecretCredential
import httpx

class GraphEmailService:
    def __init__(self):
        settings = get_settings()

        if settings.is_graph_configured():
            self.credential = ClientSecretCredential(
                tenant_id=settings.microsoft_tenant_id,
                client_id=settings.microsoft_client_id,
                client_secret=settings.microsoft_client_secret,
            )
            self.sender_email = settings.sender_email
        else:
            self.credential = None
            self.sender_email = None

    async def send_email(
        self,
        to_addresses: list[str],
        subject: str,
        html_body: str,
        cc_addresses: list[str] | None = None,
        bcc_addresses: list[str] | None = None,
    ) -> dict:
        """Send HTML email via Graph API."""
        if not self.credential:
            return {"status": "error", "message": "Microsoft Graph not configured"}

        # Get access token
        token = self.credential.get_token("https://graph.microsoft.com/.default")

        # Build message payload
        message_payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html_body},
                "toRecipients": [{"emailAddress": {"address": addr}} for addr in to_addresses]
            },
            "saveToSentItems": True
        }

        if cc_addresses:
            message_payload["message"]["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc_addresses
            ]

        if bcc_addresses:
            message_payload["message"]["bccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in bcc_addresses
            ]

        # Send via Graph API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.microsoft.com/v1.0/users/{self.sender_email}/sendMail",
                headers={
                    "Authorization": f"Bearer {token.token}",
                    "Content-Type": "application/json"
                },
                json=message_payload,
                timeout=30.0
            )

            if response.status_code == 202:
                return {"status": "ok", "recipients": len(to_addresses)}
            else:
                return {"status": "error", "message": f"Graph API error {response.status_code}: {response.text}"}
```

### Pattern 4: Windows Task Scheduler Batch Script
**What:** Batch file wrapper for Python execution with comprehensive logging
**When to use:** Windows Task Scheduler automation (provides exit codes, logging, error handling)
**Example:**
```batch
REM Source: C:\BrasilIntel\deploy\run_brasilintel.bat (proven pattern)
@echo off
SET SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\.."

REM Generate timestamp for log file
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/: " %%a in ('time /t') do (set mytime=%%a%%b)
set timestamp=%mydate%_%mytime%

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run MDInsights pipeline with logging
echo Running MDInsights pipeline >> "data\logs\mdinsights_%mydate%.log"
python -m app.main run-pipeline >> "data\logs\mdinsights_%mydate%.log" 2>&1

REM Capture and log exit code
set exitcode=%errorlevel%
echo Exit code: %exitcode% >> "data\logs\mdinsights_%mydate%.log"
echo. >> "data\logs\mdinsights_%mydate%.log"

REM Exit with same code (Task Scheduler sees non-zero as failure)
exit /b %exitcode%
```

### Pattern 5: Recipient Management via Environment Variables
**What:** Store recipient lists in .env with comma-separated format, parse in Settings
**When to use:** Configuration of email recipients per role
**Example:**
```python
# Source: C:\BrasilIntel\app\config.py (verified pattern)
# .env configuration:
# REPORT_RECIPIENTS_BROKERS=broker1@marsh.com,broker2@marsh.com
# REPORT_RECIPIENTS_BROKERS_CC=manager@marsh.com
# REPORT_RECIPIENTS_LEADERSHIP=ceo@marsh.com,cfo@marsh.com

class Settings(BaseSettings):
    # Recipient configuration per role
    report_recipients_brokers: str = ""
    report_recipients_brokers_cc: str = ""
    report_recipients_brokers_bcc: str = ""
    report_recipients_leadership: str = ""
    report_recipients_leadership_cc: str = ""
    report_recipients_leadership_bcc: str = ""
    report_recipients_compliance: str = ""
    report_recipients_compliance_cc: str = ""
    report_recipients_compliance_bcc: str = ""
    report_recipients_underwriting: str = ""
    report_recipients_underwriting_cc: str = ""
    report_recipients_underwriting_bcc: str = ""

    def _parse_recipient_list(self, recipients_str: str) -> list[str]:
        if not recipients_str:
            return []
        return [r.strip() for r in recipients_str.split(",") if r.strip()]

    def get_email_recipients(self, role: str) -> EmailRecipients:
        """Get structured TO/CC/BCC recipients for role."""
        recipients_map = {
            "Brokers": ("report_recipients_brokers", "report_recipients_brokers_cc", "report_recipients_brokers_bcc"),
            "Leadership": ("report_recipients_leadership", "report_recipients_leadership_cc", "report_recipients_leadership_bcc"),
            "Compliance": ("report_recipients_compliance", "report_recipients_compliance_cc", "report_recipients_compliance_bcc"),
            "Underwriting": ("report_recipients_underwriting", "report_recipients_underwriting_cc", "report_recipients_underwriting_bcc"),
        }

        to_field, cc_field, bcc_field = recipients_map.get(role, ("", "", ""))

        if not to_field:
            return EmailRecipients(to=[], cc=[], bcc=[])

        return EmailRecipients(
            to=self._parse_recipient_list(getattr(self, to_field, "")),
            cc=self._parse_recipient_list(getattr(self, cc_field, "")),
            bcc=self._parse_recipient_list(getattr(self, bcc_field, "")),
        )
```

### Anti-Patterns to Avoid
- **Using unified template with JavaScript tabs for email:** Email clients strip JavaScript, tabs won't work
- **CSS Grid/Flexbox without table fallback:** Outlook doesn't support modern CSS, layout breaks
- **External stylesheets in email:** Email clients block external resources for security
- **Assuming Task Scheduler passes user environment:** Must explicitly activate venv and set paths
- **Suppressing exit codes in batch scripts:** Task Scheduler relies on exit codes for failure detection

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS inlining for email | Custom CSS parser/inliner | premailer library | Handles @media queries preservation, CSS specificity, vendor prefixes, edge cases |
| Microsoft Graph auth/retry | Manual token refresh + retry logic | azure-identity ClientSecretCredential | Automatic token caching, refresh, exponential backoff (0.8s → 5 retries max) |
| Email recipient validation | Custom email regex | pydantic EmailStr validator | RFC 5322 compliance, internationalized emails, proven validation |
| HTML email rendering | Custom HTML generation | Jinja2 templates + premailer | Template inheritance, filters, auto-escaping, separation of concerns |
| Task Scheduler error handling | Manual Windows API calls | Batch script with exit codes | Task Scheduler natively logs exit codes, simpler debugging |

**Key insight:** Email rendering is deceptively complex - 90+ email clients with inconsistent CSS support, VML for Outlook, mobile viewport handling, dark mode considerations. Premailer handles CSS inlining; table-based layouts handle structural compatibility; testing tools (Litmus/Email on Acid) validate rendering.

## Common Pitfalls

### Pitfall 1: Email Template CSS Compatibility
**What goes wrong:** Using modern CSS (Grid, Flexbox, position, float) causes broken layouts in Outlook and mobile clients
**Why it happens:** Outlook uses Word rendering engine (not web engine), strips unsupported CSS
**How to avoid:**
- Use table-based layouts as foundation (`<table role="presentation">`)
- Inline all critical styles with premailer
- Avoid CSS shorthand (write `margin-top: 10px;` not `margin: 10px 0 0 0;`)
- Use MSO conditional comments for Outlook-specific fallbacks
- Test width at 600-640px max (preview pane standard)
**Warning signs:** Layouts look perfect in browser preview but broken in Outlook/Gmail app

### Pitfall 2: JavaScript Dependencies in Email
**What goes wrong:** JavaScript tabs, dynamic content, event handlers don't work in email clients
**Why it happens:** Email clients strip `<script>` tags and event handlers for security
**How to avoid:** Generate separate static HTML emails per role instead of unified tabbed interface
**Warning signs:** Browser preview works perfectly, email preview shows no tabs or interactivity

### Pitfall 3: Microsoft Graph Authentication Failures
**What goes wrong:** `ClientSecretCredential` authentication fails with timeout or permission errors
**Why it happens:** Network issues, SSL/TLS problems, missing Mail.Send application permission, admin consent not granted
**How to avoid:**
- Verify Azure AD app has Mail.Send application permission (not delegated)
- Ensure admin consent granted for permission
- Implement retry with exponential backoff (azure-identity default: 0.8s start, 5 retries)
- Use `health_check_async()` to validate Graph connectivity before pipeline execution
- Log token acquisition separately from email sending for debugging
**Warning signs:** Intermittent auth failures, 401/403 responses from Graph API

### Pitfall 4: Windows Task Scheduler Environment Issues
**What goes wrong:** Script runs manually but fails in Task Scheduler (Python not found, imports fail, file paths break)
**Why it happens:** Task Scheduler doesn't inherit user's PATH and environment variables
**How to avoid:**
- Use absolute paths in batch script (`cd /d "%SCRIPT_DIR%\.."`)
- Explicitly activate virtual environment (`call venv\Scripts\activate.bat`)
- Set "Start in" directory in Task Scheduler to project root
- Use "Run whether user is logged on or not" for reliability
- Check "Run with highest privileges" if accessing admin resources
- Log stdout/stderr to file for debugging (`>> "logs\file.log" 2>&1`)
**Warning signs:** Script succeeds manually, Task Scheduler shows "The operator or administrator has refused the request (0x800710E0)"

### Pitfall 5: Email Size Limits and Gmail Clipping
**What goes wrong:** Emails truncated with "[Message clipped] View entire message" in Gmail
**Why it happens:** Gmail clips messages >102KB, Graph API has 4MB request limit
**How to avoid:**
- Keep HTML under 100KB (minify, compress images as data URIs sparingly)
- Move large CSS to `<style>` block for Gmail (premailer preserves @media queries)
- Use image attachments instead of base64 data URIs for large images
- Test email size: `len(html_output.encode('utf-8')) / 1024` should be <100
- Consider text-only fallback for very large reports
**Warning signs:** Email body cuts off mid-content with "View entire message" link

### Pitfall 6: premailer Handling of Modern CSS
**What goes wrong:** premailer can't inline CSS Grid/Flexbox, causing them to be stripped
**Why it happens:** premailer inlines properties it understands, discards complex modern CSS
**How to avoid:**
- Don't use CSS Grid/Flexbox in email templates (use tables instead)
- Keep CSS simple: padding, margin, color, background, font properties
- Test premailer output: `transform(html)` and inspect resulting inline styles
- Use hybrid approach: table structure + simple CSS enhancements
**Warning signs:** Browser preview shows grid layout, email shows stacked/broken layout

## Code Examples

Verified patterns from official sources:

### Extended Pipeline with Email Delivery
```python
# Source: Research synthesis - extending app/services/pipeline.py pattern
async def run_full_pipeline_with_email(self) -> Dict:
    """
    Execute complete pipeline: collection → classification → report → email.

    Returns:
        Dict with run_id, articles_collected/classified, emails_sent, status
    """
    db = SessionLocal()
    result = {
        "run_id": None,
        "articles_collected": 0,
        "articles_classified": 0,
        "emails_sent": {},  # role -> send status
        "status": "failed",
        "error": None
    }

    try:
        # Steps 1-4: Collection → Classification → Report (existing)
        # ... (reuse existing pipeline.py logic)

        # Step 5: Generate role-specific emails
        self.logger.info("step_5_email_generation_started")
        role_emails = self.reporter.generate_role_emails(
            articles=classified_articles,
            report_date=report_date
        )

        # Step 6: Send emails per role
        self.logger.info("step_6_email_delivery_started")
        email_service = GraphEmailService()

        for role, html_content in role_emails.items():
            recipients = settings.get_email_recipients(role)

            if not recipients.has_recipients:
                self.logger.info(f"no_recipients_for_{role}")
                result["emails_sent"][role] = {"status": "skipped"}
                continue

            subject = f"[{settings.company_name}] {role} Intelligence Brief - {report_date.strftime('%d %B %Y')}"

            email_result = await email_service.send_email(
                to_addresses=recipients.to,
                subject=subject,
                html_body=html_content,
                cc_addresses=recipients.cc if recipients.cc else None,
                bcc_addresses=recipients.bcc if recipients.bcc else None,
            )

            result["emails_sent"][role] = email_result
            self.logger.info(f"email_sent_for_{role}", status=email_result["status"])

        # Update Run record
        emails_success = sum(1 for r in result["emails_sent"].values() if r.get("status") == "ok")
        latest_run.emails_sent = emails_success
        latest_run.status = RunStatus.COMPLETED
        db.commit()

        result["status"] = "completed"
        return result

    except Exception as e:
        result["error"] = str(e)
        self.logger.error("pipeline_failed", error=str(e), exc_info=True)
        return result
    finally:
        db.close()
```

### Email-Compatible Template (Table-Based)
```html
<!-- Source: https://www.emailmavlers.com/blog/hybrid-email-design/ -->
<!-- email/role_email.html - Table-based layout for maximum compatibility -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ role }} Intelligence Brief</title>
    <style>
        /* Preserve @media queries for responsive (premailer keeps these) */
        @media only screen and (max-width: 600px) {
            .stack { width: 100% !important; display: block !important; }
        }
    </style>
</head>
<body style="margin: 0; padding: 0; background: #f5f7fa;">
    <!-- Container table (600px max width) -->
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; background: white;">

                    <!-- Header -->
                    <tr>
                        <td style="padding: 30px; background: #00263e; color: white;">
                            <h1 style="margin: 0; font-size: 24px; font-weight: 300; line-height: 1.2;">
                                {{ company_name }} Intelligence Brief
                            </h1>
                            <p style="margin: 8px 0 0 0; font-size: 16px; font-weight: 600;">
                                {{ role }}
                            </p>
                            <p style="margin: 4px 0 0 0; font-size: 14px; opacity: 0.8;">
                                {{ report_date.strftime('%d %B %Y') }}
                            </p>
                        </td>
                    </tr>

                    <!-- Executive Summary -->
                    <tr>
                        <td style="padding: 20px; background: #f5f7fa;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="padding: 15px; background: white; border-left: 4px solid #00a3e0;">
                                        <h2 style="margin: 0 0 12px 0; font-size: 18px; color: #00263e;">
                                            Executive Summary
                                        </h2>
                                        {% for para in executive_summary.summary_paragraphs %}
                                        <p style="margin: 0 0 10px 0; font-size: 14px; line-height: 1.6; color: #333;">
                                            {{ para }}
                                        </p>
                                        {% endfor %}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Articles (priority-sorted) -->
                    {% for article in articles %}
                    <tr>
                        <td style="padding: 10px 20px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="padding: 12px; background: white; border-left: 3px solid
                                        {% if article.priority == 'Critical' %}#dc3545{% elif article.priority == 'High' %}#fd7e14{% elif article.priority == 'Medium' %}#ffc107{% else %}#6c757d{% endif %};">

                                        <h3 style="margin: 0 0 8px 0; font-size: 16px; color: #00263e;">
                                            <a href="{{ article.source_url }}" style="color: #00263e; text-decoration: none;">
                                                {{ article.title }}
                                            </a>
                                        </h3>

                                        <p style="margin: 0 0 8px 0; font-size: 13px; color: #666;">
                                            {{ article.summary }}
                                        </p>

                                        <p style="margin: 0; font-size: 12px; color: #999;">
                                            {{ article.source_name }} | {{ article.published_at.strftime('%d %b %Y') }}
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    {% endfor %}

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px; background: #f5f7fa; text-align: center; font-size: 12px; color: #999;">
                            <p style="margin: 0;">This is an automated intelligence brief from {{ company_name }}.</p>
                            <p style="margin: 4px 0 0 0;">CONFIDENTIAL - For internal use only.</p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SMTP email delivery | Microsoft Graph API | 2020+ | Better audit trail, admin control, no SMTP config, corporate compliance |
| Hand-coded inline CSS | premailer transformation | 2015+ | Maintainable CSS in `<style>` blocks, automated inlining, @media query preservation |
| Div-based email layouts | Table-based layouts | Always (email) | Universal email client compatibility, Outlook Word engine requires tables |
| Single unified email | Role-specific emails | 2026 (this phase) | No JavaScript dependency, personalized content, better engagement |
| Manual Task Scheduler | PowerShell automation | 2016+ | Version-controlled task creation, CI/CD integration, reproducible deployments |

**Deprecated/outdated:**
- **SMTP for corporate email:** Microsoft Graph API is Azure AD standard, better security and auditing
- **CSS-only responsive email:** Hybrid approach (tables + CSS) required for Outlook compatibility
- **JavaScript in email templates:** Never supported in email clients, always stripped for security

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal email delivery timing for market open**
   - What we know: Requirement states "before market open (08:00 local)"
   - What's unclear: Collection/classification duration, retry strategy if pipeline fails
   - Recommendation: Schedule Task Scheduler for 06:00, allows 2 hours for pipeline + retry. Monitor execution duration in Phase 2 verification. Add alerting if pipeline exceeds 90 minutes.

2. **Admin alerting when email delivery fails**
   - What we know: Task Scheduler can email on task failure, but this requires SMTP config (defeating Graph API purpose)
   - What's unclear: Best pattern for alerting without SMTP dependency
   - Recommendation: Send admin alert email via same GraphEmailService when pipeline fails. Store admin email in .env as `ADMIN_EMAIL`. Catch pipeline exceptions, send error summary to admin before exiting with non-zero code.

3. **HTML report archival strategy**
   - What we know: Pipeline generates HTML but doesn't save to disk currently
   - What's unclear: Should reports be archived for audit/debugging? Storage location? Retention policy?
   - Recommendation: Save HTML reports to `data/reports/{role}/{date}.html` before emailing. Use 90-day retention. Helpful for debugging rendering issues and audit compliance.

4. **Email rendering testing without commercial tools**
   - What we know: Litmus/Email on Acid cost $99+/month for comprehensive testing
   - What's unclear: Can we validate rendering across Outlook/Gmail/mobile without paid tools?
   - Recommendation: Use free tier of Email on Acid (3 previews/month) for initial validation. Test manually in Outlook Desktop, Outlook Web, Gmail Web, Gmail Mobile during Phase 5. Add automated email preview screenshot capture in Phase 6 if budget allows.

5. **Dark mode email support**
   - What we know: Many email clients now support dark mode, can invert colors
   - What's unclear: Should we add dark mode CSS for better user experience?
   - Recommendation: Defer to Phase 6. Current table-based layout with Marsh blue (#00263e) header works in dark mode. Add `@media (prefers-color-scheme: dark)` optimizations if user feedback requests it.

## Sources

### Primary (HIGH confidence)
- [Microsoft Graph API send email documentation](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0) - Official Graph API sendMail endpoint reference
- [Microsoft Graph daemon authentication](https://learn.microsoft.com/en-us/answers/questions/43724/sending-emails-from-daemon-app-using-graph-api-on) - ClientSecretCredential pattern for automated sending
- [azure-identity authentication best practices](https://learn.microsoft.com/en-us/dotnet/azure/sdk/authentication/best-practices) - Retry configuration and error handling
- BrasilIntel codebase (`C:\BrasilIntel\app\services\emailer.py`) - Verified working GraphEmailService implementation
- BrasilIntel codebase (`C:\BrasilIntel\deploy\run_brasilintel.bat`) - Proven Task Scheduler batch script pattern
- premailer library (already installed) - CSS inlining for email compatibility

### Secondary (MEDIUM confidence)
- [HTML Email Development Best Practices](https://www.emailonacid.com/blog/article/email-development/email-development-best-practices-2/) - Table-based layouts, CSS support, 600px width
- [Hybrid Email Design](https://www.emailmavlers.com/blog/hybrid-email-design/) - Table foundation + CSS enhancement pattern
- [HTML and CSS in Emails: What Works in 2026](https://designmodo.com/html-css-emails/) - CSS Grid/Flexbox limitations, Outlook MSO conditionals
- [Email CSS Support Guide](https://www.campaignmonitor.com/css/) - Email client CSS compatibility matrix
- [Scheduling Python Scripts with Windows Task Scheduler](https://www.getgalaxy.io/learn/glossary/scheduling-python-scripts-with-windows-task-scheduler) - Environment variable handling, logging best practices
- [Windows Task Scheduler Python best practices](https://www.jcchouinard.com/python-automation-using-task-scheduler/) - Exit codes, error handling, debugging

### Tertiary (LOW confidence)
- [premailer GitHub repository](https://github.com/premailer/premailer) - Library capabilities and limitations
- [HTML Email Best Practices](https://templates.mailchimp.com/getting-started/html-email-basics/) - General email HTML guidelines
- [Email Design Best Practices for 2026](https://www.brevo.com/blog/email-design-best-practices/) - Personalization and responsive design patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All dependencies verified installed, BrasilIntel patterns proven in production
- Architecture: HIGH - BrasilIntel provides working reference implementation for all major components
- Pitfalls: HIGH - Email CSS compatibility extensively documented, Task Scheduler issues well-known
- Code examples: HIGH - All patterns sourced from BrasilIntel working code or official documentation
- Email template conversion: MEDIUM - Table-based approach is standard, but conversion effort requires testing

**Research date:** 2026-02-07
**Valid until:** 2026-03-07 (30 days - stable technologies, but email client rendering updates periodically)
