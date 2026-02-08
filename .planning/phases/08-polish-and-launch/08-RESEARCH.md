# Phase 8: Polish and Launch - Research

**Researched:** 2026-02-08
**Domain:** Production deployment, documentation, branding, stakeholder handoff
**Confidence:** HIGH

## Summary

Phase 8 is the final phase focused on production readiness rather than new features. Research covers four key areas: brand guideline compliance for professional visual identity, administrator documentation for operational handoff, deployment documentation for Windows Server setup, and stakeholder approval processes for production launch.

The system is fully functional after Phase 7. This phase ensures it meets professional standards for production deployment in an enterprise insurance environment (Marsh).

**Primary recommendation:** Focus on refinement, clarity, and handoff — not new functionality. Success criteria are met when stakeholders approve the styling, documentation enables independent administration, and the system runs reliably in production.

## Standard Stack

### Core (Already Implemented in Phases 1-7)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.0 | Web framework | Industry standard for Python APIs, async support |
| Jinja2 | (via FastAPI) | HTML templating | Standard for Flask/FastAPI, template inheritance |
| Bootstrap | 5.3.3 | CSS framework | Already integrated in admin templates |
| Premailer | latest | Email CSS inlining | Standard for HTML email compatibility |

### Supporting Tools for Phase 8
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| Windows Task Scheduler | Built-in | Production automation | Already configured in Phase 7 |
| PowerShell | 5.1+ | Deployment scripts | Already implemented (setup_task.ps1) |
| Azure Blob Storage | via azure-identity | Database backups | Already integrated in Phase 7 |
| Microsoft Graph API | via azure-identity | Email delivery | Already integrated in Phase 2 |

### Documentation Tools (New for Phase 8)
| Tool | Purpose | Format |
|------|---------|--------|
| Markdown | Documentation format | .md files for README, guides |
| Browser screenshots | Visual documentation | .png for troubleshooting guides |
| Manual testing | Final validation | Checklist-based verification |

**Installation:**
No new Python dependencies required. All functionality for Phase 8 uses existing stack.

```bash
# No additional packages needed
# Phase 8 uses existing requirements.txt (44 lines, all dependencies installed)
```

## Architecture Patterns

### Current Project Structure (After Phase 7)
```
mdinsights/
├── app/
│   ├── main.py                    # FastAPI app + CLI
│   ├── config.py                  # Settings + email recipients
│   ├── logging_config.py          # Structured logging
│   ├── database.py                # SQLAlchemy setup
│   ├── models/                    # ORM models
│   ├── schemas/                   # Pydantic schemas
│   ├── services/                  # Business logic
│   ├── routers/                   # API routes
│   └── templates/                 # Jinja2 templates
│       ├── role_brief.html        # Browser version (JS, interactive)
│       ├── email/role_email.html  # Email version (tables, no JS)
│       └── admin/                 # Dashboard templates
├── deploy/
│   ├── run_mdinsights.bat         # Task Scheduler wrapper
│   ├── setup_task.ps1             # 4 tasks registration
│   └── check_last_run.py          # Monitoring script
├── scripts/
│   ├── seed_sources.py            # Initialize sources
│   ├── backup_db.py               # Azure Blob backup
│   └── check_drift.py             # Classification drift monitor
├── data/
│   ├── logs/                      # Daily JSON logs (30-day rotation)
│   └── mdinsights.db              # SQLite database
├── .env                           # Environment config (not in git)
├── requirements.txt               # Python dependencies
└── PROJECT.md                     # High-level overview
```

### Pattern 1: Brand Consistency Through CSS Variables
**What:** Centralized color palette using CSS custom properties
**When to use:** Already implemented in role_brief.html and email templates
**Example:**
```css
/* Source: RefChyt/prototype_daily_intelligence_brief.html (lines 8-17) */
:root {
    --marsh-blue: #00263e;
    --marsh-light-blue: #0077c8;
    --marsh-accent: #00a3e0;
    --alert-red: #dc3545;
    --alert-orange: #fd7e14;
    --alert-yellow: #ffc107;
    --success-green: #28a745;
    --neutral-gray: #6c757d;
    --bg-light: #f5f7fa;
}
```
**Current status:** Already implemented in both browser and email templates. Phase 8 Plan 01 will verify consistency with prototype.

### Pattern 2: Documentation Hierarchy for Administrators
**What:** Layered documentation from quick start to deep troubleshooting
**When to use:** Administrator guide must support both daily operations and incident response
**Recommended structure:**
```markdown
# Administrator Guide

## Quick Start (5 minutes)
- What MDInsights does
- How to access admin dashboard
- Daily workflow (if any)

## Source Management (10 minutes)
- Adding/editing sources
- Monitoring source health
- Handling source failures

## Recipient Management (5 minutes)
- Managing email recipients
- Role-based distribution lists
- Testing email delivery

## Troubleshooting (Reference)
- Symptom: Pipeline didn't run
  - Check Task Scheduler status
  - Review logs in data/logs/
  - Verify .env configuration
- Symptom: Reports not sent
  - Check Graph API credentials
  - Verify recipient addresses
  - Review email service logs
- Symptom: Classification degraded
  - Review drift monitor alerts
  - Check OpenAI API status
  - Verify model configuration

## Maintenance Tasks (Weekly/Monthly)
- Review source health dashboard
- Archive old reports (optional)
- Check backup success
- Monitor drift alerts
```

**Evidence:** [IT Documentation Best Practices | NinjaOne](https://www.ninjaone.com/blog/it-documentation-best-practices/) recommends starting with symptoms users observe, decision tree format, and searchable structure.

### Pattern 3: Deployment Documentation for Windows Server
**What:** Step-by-step setup guide for production deployment
**When to use:** First-time deployment or disaster recovery
**Recommended structure:**
```markdown
# Deployment Guide

## Prerequisites
- Windows Server 2019+ or Windows 10/11
- Python 3.11+ installed
- Azure AD app registration (with permissions)
- Azure OpenAI access
- Apify account with API key

## Setup Steps

### 1. Clone and Configure (15 minutes)
- Clone repository
- Create virtual environment
- Install dependencies
- Configure .env file

### 2. Azure AD App Registration (20 minutes)
- Sign in to Entra admin center
- Create new app registration
- Configure API permissions (Mail.Send, User.Read)
- Generate client secret
- Add credentials to .env

### 3. Database Initialization (5 minutes)
- Seed sources: python scripts/seed_sources.py
- Verify schema: sqlite3 data/mdinsights.db ".schema"
- Configure recipients: Admin dashboard or config.py

### 4. Task Scheduler Configuration (10 minutes)
- Run setup_task.ps1 as Administrator
- Verify 4 tasks registered:
  - Pipeline (06:00)
  - Backup (07:00)
  - Drift Check (Mon 08:00)
  - Monitor (09:00)
- Test pipeline: schtasks /run /tn "MDInsights Daily Pipeline"

### 5. Monitoring Setup (5 minutes)
- Configure monitor email recipients
- Test health check endpoint: /api/health/sources
- Verify log rotation (30 days)

### 6. Backup Configuration (10 minutes)
- Create Azure Blob Storage container
- Add credentials to .env
- Test backup: python scripts/backup_db.py
- Verify retention (30 days)

## Production Checklist
- [ ] All .env variables configured
- [ ] Azure AD app permissions granted
- [ ] 4 Task Scheduler tasks registered
- [ ] Sources seeded and active
- [ ] Email recipients configured
- [ ] Backup container created
- [ ] Test pipeline run successful
- [ ] Test email delivery successful
- [ ] Monitoring alerts configured
```

**Evidence:** [How to register an app in Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app) provides official Microsoft documentation for Azure AD setup. [FastAPI Deployment Guide for 2026](https://www.zestminds.com/blog/fastapi-deployment-guide/) recommends worker configuration and environment setup validation.

### Pattern 4: Stakeholder Approval Process
**What:** Structured handoff with approval gates
**When to use:** Before production launch
**Recommended workflow:**
```
1. Sample Brief Generation (Phase 8, Plan 04)
   - Run pipeline with production sources
   - Generate sample briefs for all roles
   - Share with stakeholders via email or PDF

2. Stakeholder Review (1-2 days)
   - Review brand consistency
   - Verify content relevance
   - Test email delivery
   - Provide feedback

3. Refinement (if needed)
   - Address styling issues
   - Adjust role classifications
   - Fix delivery problems

4. Final Approval
   - Stakeholder sign-off documented
   - Production deployment authorized
   - Handoff to administrator

5. Go-Live
   - Task Scheduler enabled
   - Monitoring active
   - Documentation shared
   - Support contact established
```

**Evidence:** [Project Handover Checklist: A Comprehensive Guide](https://www.projectmanagertemplate.com/post/project-handover-checklist-a-comprehensive-guide) recommends early stakeholder engagement, approval workflows, and documented sign-off. [The Essential Release Checklist 2026](https://www.apwide.com/the-essential-release-checklist/) emphasizes stakeholder communication and approval gates.

### Anti-Patterns to Avoid
- **Adding new features in Phase 8:** This is polish, not development. All features complete in Phase 7.
- **Over-engineering documentation:** Administrators need practical guides, not exhaustive theory.
- **Skipping stakeholder approval:** Production deployment without stakeholder sign-off creates risk.
- **Manual CSS pixel-pushing:** Use existing Bootstrap classes and CSS variables, not inline styles.
- **Deployment without testing:** Must verify Task Scheduler, email delivery, and monitoring before go-live.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS framework | Custom grid system | Bootstrap 5.3.3 (already integrated) | Responsive, accessible, well-tested |
| Email CSS inlining | Manual style injection | Premailer (already integrated) | Handles Outlook/Gmail compatibility |
| Task scheduling | Custom scheduler service | Windows Task Scheduler (already configured) | Built-in, reliable, enterprise-standard |
| Documentation hosting | Custom wiki | Markdown files in repo | Simple, version-controlled, readable |
| Approval workflow | Custom sign-off system | Email + documented checklist | Lightweight, auditable, familiar |
| Backup automation | Manual backup scripts | Existing backup_manager.py | Already implemented with Azure Blob |
| Log rotation | Custom log cleanup | Existing logging_config.py | Already handles 30-day rotation |

**Key insight:** Phase 8 uses existing infrastructure from Phases 1-7. The only "new" deliverables are documentation files and final validation.

## Common Pitfalls

### Pitfall 1: Brand Guidelines Become Pixel-Perfect Design Project
**What goes wrong:** Team spends days adjusting fonts, spacing, and colors beyond the prototype reference
**Why it happens:** Desire for perfection instead of "matches brand guidelines precisely" (success criteria)
**How to avoid:** Use success criteria as threshold: "Report styling matches Marsh brand guidelines precisely" means CSS colors, fonts, and layout structure match prototype. Not pixel-perfect replication.
**Warning signs:** Multiple rounds of CSS adjustments, stakeholder requests for minor tweaks, bikeshedding on color shades

### Pitfall 2: Documentation Written for Developers, Not Administrators
**What goes wrong:** Guide assumes Python knowledge, Git familiarity, or technical debugging skills
**Why it happens:** Developer writes what they would want, not what administrator needs
**How to avoid:** Administrator guide should assume Windows Server admin skills only (Task Scheduler, IIS, PowerShell basics). No Python debugging. No Git commands. Focus on: "What do I do when X happens?"
**Warning signs:** Commands like `git pull origin main`, `pip install -r requirements.txt` without context, references to "virtual environments" without explanation

### Pitfall 3: Deployment Documentation Skips Azure AD Setup
**What goes wrong:** Deployment guide assumes Azure AD app registration already exists
**Why it happens:** Developer has existing credentials and forgets first-time setup
**How to avoid:** Deployment guide must include complete Azure AD app registration steps with screenshots or detailed instructions. This is the #1 blocker for production deployment.
**Warning signs:** .env.example has AZURE_CLIENT_ID and AZURE_CLIENT_SECRET but guide doesn't explain how to get them

### Pitfall 4: Production Deployment Without Stakeholder Samples
**What goes wrong:** System deployed to production without stakeholders seeing real output
**Why it happens:** Developer assumes system works as designed, skips approval step
**How to avoid:** Success criteria #5 requires "Stakeholders have received sample briefs and provided approval." Must generate real briefs from production sources before go-live.
**Warning signs:** Task Scheduler enabled before stakeholder review, no sample emails sent, no feedback documented

### Pitfall 5: Handoff Without Administrator Training
**What goes wrong:** Documentation created but administrator never trained, system runs unmonitored
**Why it happens:** Documentation delivery confused with knowledge transfer
**How to avoid:** Plan 08-04 should include administrator walkthrough: show admin dashboard, demonstrate source management, explain monitoring alerts, review troubleshooting steps.
**Warning signs:** Documentation sent via email without meeting, no Q&A session, administrator never logged into admin dashboard

### Pitfall 6: Monitoring Configured but Alerts Not Tested
**What goes wrong:** Monitor task runs daily but email alerts never verified
**Why it happens:** Monitoring setup confused with monitoring validation
**How to avoid:** Explicitly test monitoring failures: stop pipeline, verify monitor detects it, confirm alert email sent. Test all alert conditions before production.
**Warning signs:** Monitor task registered but never triggered alert, no test failures simulated, alert recipients not verified

## Code Examples

### Example 1: Brand Consistency Verification Script
**Purpose:** Automated verification that templates match brand guidelines
**Source:** Pattern derived from existing templates

```python
# scripts/verify_branding.py
"""
Verify MDInsights templates match Marsh brand guidelines.
"""
import re
from pathlib import Path

def check_css_colors(template_path: Path, required_colors: dict[str, str]) -> list[str]:
    """Check that template uses correct Marsh brand colors."""
    content = template_path.read_text(encoding='utf-8')
    issues = []

    for color_name, expected_hex in required_colors.items():
        # Check CSS variable definition
        pattern = f"--{color_name}:\\s*{expected_hex}"
        if not re.search(pattern, content):
            issues.append(f"Missing or incorrect CSS variable: --{color_name} should be {expected_hex}")

    return issues

def check_kevin_taylor_attribution(template_path: Path) -> list[str]:
    """Verify Kevin Taylor attribution present (REPT-10)."""
    content = template_path.read_text(encoding='utf-8')
    issues = []

    if "Kevin Taylor" not in content:
        issues.append("Missing Kevin Taylor attribution")
    if "Colleague Technology Services" not in content:
        issues.append("Missing Colleague Technology Services attribution")

    return issues

def verify_all_templates():
    """Run brand verification on all templates."""
    templates_dir = Path(__file__).parent.parent / "app" / "templates"

    required_colors = {
        "marsh-blue": "#00263e",
        "marsh-light-blue": "#0077c8",
        "marsh-accent": "#00a3e0",
    }

    all_issues = []

    # Check browser template
    browser_template = templates_dir / "role_brief.html"
    if browser_template.exists():
        print(f"Checking {browser_template.name}...")
        issues = check_css_colors(browser_template, required_colors)
        issues.extend(check_kevin_taylor_attribution(browser_template))
        all_issues.extend(issues)

    # Check email template
    email_template = templates_dir / "email" / "role_email.html"
    if email_template.exists():
        print(f"Checking {email_template.name}...")
        issues = check_css_colors(email_template, required_colors)
        issues.extend(check_kevin_taylor_attribution(email_template))
        all_issues.extend(issues)

    if all_issues:
        print("\n❌ Branding issues found:")
        for issue in all_issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n✅ All templates match brand guidelines")
        return True

if __name__ == "__main__":
    success = verify_all_templates()
    exit(0 if success else 1)
```

### Example 2: Stakeholder Approval Checklist Template
**Purpose:** Document stakeholder sign-off before production
**Source:** Derived from release management best practices

```markdown
# Stakeholder Approval Checklist

**Project:** MDInsights - Global Intelligence Brief
**Date:** [YYYY-MM-DD]
**Approvers:** [Names and roles]

## Sample Brief Review

### Branding (REPT-09)
- [ ] Logo placement correct
- [ ] Color scheme matches Marsh guidelines (blues: #00263e, #0077c8, #00a3e0)
- [ ] Typography matches brand standards (Segoe UI or equivalent)
- [ ] Layout structure matches prototype
- [ ] Kevin Taylor / Colleague Technology Services attribution present (REPT-10)

**Notes:** _______________________________________________

### Content Quality
- [ ] Executive summaries relevant to each role
- [ ] Priority classifications appropriate (Critical/High/Medium/Monitor)
- [ ] Entity tracking accurate
- [ ] Market pulse indicators meaningful
- [ ] "What to Watch" section actionable

**Notes:** _______________________________________________

### Email Delivery
- [ ] Test emails received by all roles
- [ ] Formatting correct in Outlook
- [ ] Formatting correct in Gmail
- [ ] Links functional
- [ ] Mobile rendering acceptable

**Notes:** _______________________________________________

## Production Readiness

### Technical Validation
- [ ] Task Scheduler configured (4 tasks)
- [ ] Database backup working (Azure Blob)
- [ ] Monitoring alerts configured
- [ ] Source health checks active
- [ ] Drift detection working

**Notes:** _______________________________________________

### Documentation
- [ ] Administrator guide complete
- [ ] Deployment guide complete
- [ ] Troubleshooting steps verified
- [ ] Contact information current

**Notes:** _______________________________________________

## Approval

**Production deployment approved:** [ ] YES  [ ] NO

**Approver signature:** _____________________
**Date:** _____________________

**Conditions (if any):** _______________________________________________
```

### Example 3: Production Deployment Validation Script
**Purpose:** Verify all production requirements before go-live
**Source:** Derived from deployment best practices

```python
# scripts/validate_production_ready.py
"""
Validate MDInsights is production-ready before deployment.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_environment_variables() -> list[str]:
    """Verify all required .env variables configured."""
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID",
        "APIFY_API_KEY",
        "EMAIL_FROM",
        "AZURE_BLOB_CONNECTION_STRING",
        "AZURE_BLOB_CONTAINER",
    ]

    issues = []
    for var in required_vars:
        if not os.getenv(var):
            issues.append(f"Missing environment variable: {var}")

    return issues

def check_task_scheduler() -> list[str]:
    """Verify Task Scheduler tasks registered."""
    import subprocess

    required_tasks = [
        "MDInsights Daily Pipeline",
        "MDInsights Daily Pipeline - Backup",
        "MDInsights Daily Pipeline - Drift Check",
        "MDInsights Daily Pipeline - Monitor",
    ]

    issues = []
    for task_name in required_tasks:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", task_name],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            issues.append(f"Task not registered: {task_name}")

    return issues

def check_database() -> list[str]:
    """Verify database exists and has sources."""
    import sqlite3

    issues = []
    db_path = Path(__file__).parent.parent / "data" / "mdinsights.db"

    if not db_path.exists():
        issues.append("Database not found: data/mdinsights.db")
        return issues

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check sources table has entries
    cursor.execute("SELECT COUNT(*) FROM sources WHERE enabled = 1")
    count = cursor.fetchone()[0]
    if count == 0:
        issues.append("No enabled sources in database (run scripts/seed_sources.py)")

    conn.close()
    return issues

def validate_all():
    """Run all production readiness checks."""
    print("MDInsights Production Readiness Validation")
    print("=" * 50)
    print()

    all_issues = []

    # Check environment
    print("Checking environment variables...")
    issues = check_environment_variables()
    if issues:
        all_issues.extend(issues)
    else:
        print("  ✅ All environment variables configured")

    # Check Task Scheduler
    print("Checking Task Scheduler...")
    issues = check_task_scheduler()
    if issues:
        all_issues.extend(issues)
    else:
        print("  ✅ All tasks registered")

    # Check database
    print("Checking database...")
    issues = check_database()
    if issues:
        all_issues.extend(issues)
    else:
        print("  ✅ Database initialized with sources")

    print()

    if all_issues:
        print("❌ Production readiness check FAILED:")
        for issue in all_issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ Production readiness check PASSED")
        print("\nSystem ready for deployment.")
        return True

if __name__ == "__main__":
    load_dotenv()
    success = validate_all()
    sys.exit(0 if success else 1)
```

## State of the Art

### Current Approach (2026)
| Area | Current Best Practice | MDInsights Status |
|------|----------------------|-------------------|
| CSS Framework | Bootstrap 5.3.3 with custom properties | ✅ Implemented in Phase 5 |
| Email CSS | Premailer for inline styles | ✅ Implemented in Phase 5 |
| Brand Guidelines | Design system with CSS variables | ✅ Prototype reference ready |
| Documentation | Markdown in repo, searchable | 🔄 Phase 8 deliverable |
| Deployment | PowerShell automation | ✅ Implemented in Phase 7 |
| Monitoring | Health checks + email alerts | ✅ Implemented in Phase 7 |
| Backup | Azure Blob with retention | ✅ Implemented in Phase 7 |
| Approval | Documented checklist + sign-off | 🔄 Phase 8 deliverable |

### Deprecated/Outdated
- **NSSM (Non-Sucking Service Manager):** Previously recommended for Windows service deployment, now replaced by Task Scheduler for simpler maintenance (BrasilIntel project history)
- **Manual CSS inlining:** Replaced by Premailer for email compatibility
- **Static PDFs for brand guidelines:** 2026 best practice is interactive, modular design systems (though static prototype sufficient for Phase 8 reference)

## Open Questions

### Question 1: Administrator Access Level
**What we know:** Administrator needs Task Scheduler, admin dashboard access, and .env file modification
**What's unclear:** Should administrator have database direct access (sqlite3) or only web dashboard?
**Recommendation:** Web dashboard only for normal operations. Database access documented for disaster recovery but not routine use. Keeps complexity lower.

### Question 2: Stakeholder Approval Format
**What we know:** Success criteria requires stakeholder approval before production
**What's unclear:** Formal sign-off document or email confirmation sufficient?
**Recommendation:** Email confirmation acceptable if it documents: (1) samples reviewed, (2) branding approved, (3) production deployment authorized. Formal document optional but not required for success criteria.

### Question 3: Logo File Source
**What we know:** Marsh logo placement mentioned in Plan 08-01
**What's unclear:** Is Marsh logo file available or just reference to logo placement pattern from prototype?
**Recommendation:** Plan 08-01 should verify if logo file needed. Prototype shows "Marsh Global Intelligence Brief" text treatment without logo image. Text-based header likely sufficient (matches email template).

### Question 4: Production Environment Location
**What we know:** Windows Server deployment documented
**What's unclear:** Is production server identified or TBD during handoff?
**Recommendation:** Deployment guide should be environment-agnostic. Server identification is stakeholder responsibility during Plan 08-04 handoff.

## Sources

### Primary (HIGH confidence)
- RefChyt/prototype_daily_intelligence_brief.html - Reference for Marsh brand guidelines (CSS colors, layout, typography)
- app/templates/role_brief.html - Current browser template implementation
- app/templates/email/role_email.html - Current email template implementation
- deploy/setup_task.ps1 - Existing Task Scheduler configuration
- PROJECT.md - Project overview and architecture

### Secondary (MEDIUM confidence)
- [FastAPI Deployment Guide for 2026 (Zestminds)](https://www.zestminds.com/blog/fastapi-deployment-guide/) - Production deployment best practices
- [IT Documentation Best Practices (NinjaOne)](https://www.ninjaone.com/blog/it-documentation-best-practices/) - Administrator guide structure
- [How to register an app in Microsoft Entra ID (Microsoft Learn)](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app) - Azure AD setup steps
- [The Essential Release Checklist 2026 (Apwide)](https://www.apwide.com/the-essential-release-checklist/) - Stakeholder approval workflow
- [Project Handover Checklist (ProjectManagerTemplate)](https://www.projectmanagertemplate.com/post/project-handover-checklist-a-comprehensive-guide) - Handoff best practices
- [The Ultimate Guide to Brand Guidelines (Kijo)](https://kijo.co.uk/blog/brand-guidelines/) - 2026 brand guideline characteristics
- [Design System Checklist (UXPin)](https://www.uxpin.com/studio/blog/launching-design-system-checklist/) - CSS design system fundamentals

### Tertiary (LOW confidence)
- [Server Health Monitoring (AttuneOps)](https://attuneops.io/server-health-monitoring/) - General Windows monitoring (already implemented in Phase 7)

## Metadata

**Confidence breakdown:**
- Brand guidelines: HIGH - Prototype exists as reference, templates already match pattern
- Documentation structure: HIGH - Administrator guide and deployment guide patterns well-established in 2026
- Azure AD setup: HIGH - Official Microsoft documentation provides authoritative steps
- Stakeholder approval: MEDIUM - Process well-documented but format flexibility acceptable
- Production environment: MEDIUM - Deployment guide structure clear, specific server TBD

**Research date:** 2026-02-08
**Valid until:** 2026-04-08 (60 days - stable patterns, minimal churn expected)
