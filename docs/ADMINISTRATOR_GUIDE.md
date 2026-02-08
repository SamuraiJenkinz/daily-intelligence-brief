# MDInsights Administrator Guide

**For:** Windows Server Administrators
**Purpose:** Daily operations, source management, recipient management, and troubleshooting
**Target Audience:** Non-developers with Windows Server admin skills

---

## 1. Quick Start (What MDInsights Does)

MDInsights is an automated intelligence system that collects news from 18+ insurance industry sources, classifies them by priority and audience role using AI, and delivers tailored intelligence briefs to four teams each morning:

- **Brokers** — Market-facing intelligence on rates, capacity, trends
- **Leadership** — Strategic insights, regulatory changes, major market shifts
- **Compliance** — Regulatory updates, legal changes, compliance requirements
- **Underwriting** — Risk intelligence, claims trends, catastrophe updates

### How to Access

Open your web browser and navigate to:
```
http://[server-address]:8001/admin
```

Replace `[server-address]` with your server's hostname or IP address. If accessing locally on the server itself, use:
```
http://localhost:8001/admin
```

### What Happens Automatically Each Day

MDInsights runs four scheduled tasks via Windows Task Scheduler:

| Time | Task | Purpose |
|------|------|---------|
| **06:00** | **Pipeline** | Collect articles, classify with AI, generate briefs, send emails |
| **07:00** | **Backup** | Database backup to Azure Blob Storage |
| **Monday 08:00** | **Drift Check** | AI classification quality check (weekly) |
| **09:00** | **Monitor** | Verifies pipeline ran successfully, sends alert if failed |

**On a normal day, you do nothing.** The system runs automatically.

### When Administrator Action is Needed

You'll receive an email alert when:

1. **Pipeline fails** — No report delivered, monitor task detects failure
2. **Source health issue** — A news source stops returning articles
3. **Drift alert** — AI classification quality has degraded (weekly check)
4. **Backup failure** — Database backup did not complete

All alerts are sent to the email address configured in `.env` as `ADMIN_EMAIL`.

---

## 2. Daily Operations

### Normal Day (No Action Required)

On a typical day:

1. **06:00** — Pipeline runs automatically
2. **06:05-06:30** — Articles collected from 18+ sources
3. **06:30-06:45** — AI classifies each article by priority and role
4. **06:45-06:50** — Reports generated and emailed to recipients
5. **07:00** — Database backup to Azure Blob Storage
6. **09:00** — Monitor verifies pipeline ran, no alert sent

You only need to act if you receive an alert email.

### Checking System Status

**Via Admin Dashboard:**

1. Open browser to `http://[server-address]:8001/admin`
2. Review the dashboard cards:
   - **Active Sources** — Number of enabled news sources (typically 18+)
   - **Total Sources** — All sources including disabled ones
   - **Articles Today** — Articles collected from today's date
   - **Last Run** — Status of most recent pipeline run (should show "completed")

3. Review the **Recent Runs** table:
   - **Status** column should show green "Completed" badges
   - **Collected** and **Classified** columns show article counts
   - **Error** column should be empty

**Via Task Scheduler:**

1. Press `Windows + R`, type `taskschd.msc`, press Enter
2. In Task Scheduler, navigate to **Task Scheduler Library**
3. Find these tasks:
   - `MDInsights Daily Pipeline`
   - `MDInsights Daily Pipeline - Backup`
   - `MDInsights Daily Pipeline - Drift Check`
   - `MDInsights Daily Pipeline - Monitor`
4. Check **Last Run Result** column — should show "The operation completed successfully (0x0)"

### Viewing Today's Reports

**Option 1: Via Email**

Recipients receive role-specific briefs in their inbox each morning at approximately 06:45.

**Option 2: Via Admin Dashboard**

1. Open browser to `http://[server-address]:8001/admin`
2. Click **Archive** in the left navigation menu
3. Find today's date in the list
4. Click the badge for the role you want to view (Brokers, Leadership, Compliance, Underwriting)
5. The report opens in a new browser tab

### Understanding Dashboard Statistics

**Dashboard Metrics:**

- **Active Sources** — News sources currently enabled for collection (typical: 18+)
  - If this number drops unexpectedly, a source may have been accidentally disabled

- **Total Sources** — All sources including disabled ones
  - Disabled sources remain in the database but are skipped during collection

- **Articles Today** — Total articles collected with today's published date
  - Typical range: 50-300 articles per day depending on news cycle
  - Zero articles indicates a pipeline failure

- **Last Run** — Most recent pipeline execution
  - **Status: Completed** (green) — Normal
  - **Status: Failed** (red) — Pipeline encountered an error
  - **Status: Running** (blue) — Pipeline currently executing

**Recent Runs Table:**

- **ID** — Sequential run number
- **Status** — Completed / Failed / Running
- **Created** — Pipeline start time
- **Completed** — Pipeline end time (typically 30-45 minutes after start)
- **Collected** — Raw articles collected from sources
- **Classified** — Articles successfully classified by AI
- **Error** — Error message if pipeline failed (empty on success)

---

## 3. Source Management

MDInsights collects news from multiple sources including Apify scrapers and RSS feeds. You can view, add, edit, disable, and delete sources via the admin dashboard.

### Viewing Sources

1. Open browser to `http://[server-address]:8001/admin/sources`
2. Or click **Sources** in the left navigation menu
3. The sources table shows:
   - **Name** — Display name of the source
   - **Type** — `apify` (web scraper) or `rss` (RSS feed)
   - **URL** — Source website or feed URL
   - **Status** — Enabled (green) or Disabled (red)
   - **Actions** — Edit, Toggle, Delete buttons

**Filter and Search:**

- Use the search box to filter by name or URL (search updates as you type)
- Use the **Status** dropdown to filter by enabled/disabled sources

### Adding a New Source

**Prerequisites:**

- For Apify sources: You need the Apify Actor ID from the Apify platform
- For RSS sources: You need the RSS feed URL

**Steps:**

1. Navigate to **Sources** page (`/admin/sources`)
2. Click the **+ Add New Source** button (top right)
3. Fill in the form:
   - **Name** — Display name (e.g., "Insurance Journal")
   - **URL** — Website URL or RSS feed URL
   - **Type** — Select `apify` or `rss`
   - **Actor ID** — (Apify only) Enter the Apify Actor ID
   - **Enabled** — Check to enable immediately, uncheck to add as disabled
4. Click **Create Source**

**Form appears inline, replacing the button. If there are validation errors, they appear next to the fields.**

**Validation Rules:**

- Name must be unique (no duplicate source names)
- URL must be a valid HTTP/HTTPS URL
- Actor ID is required for Apify sources
- Actor ID must match format: `username/actor-name`

**After Successful Creation:**

- Form closes automatically
- New source appears in the table
- If enabled, it will be included in the next pipeline run

### Editing a Source

1. Navigate to **Sources** page
2. Find the source you want to edit
3. Click the **Edit** button (pencil icon) in the Actions column
4. The table row transforms into an edit form
5. Modify the fields as needed
6. Click **Save** to apply changes, or **Cancel** to discard

**Note:** Name must still be unique. If you try to rename to an existing name, you'll get a validation error.

### Disabling a Source Temporarily

**Use Case:** A source is broken or returning low-quality articles, but you want to keep it configured for future re-enabling.

**Steps:**

1. Navigate to **Sources** page
2. Find the source you want to disable
3. Click the **Toggle** button (toggle switch icon)
4. Status badge changes from green "Enabled" to red "Disabled"
5. Source will be skipped in future pipeline runs

**To Re-Enable:**

1. Click the **Toggle** button again
2. Status badge changes back to green "Enabled"

### Deleting a Source Permanently

**Warning:** Deletion is permanent. Historical articles from this source remain in the database, but the source configuration is removed.

**Steps:**

1. Navigate to **Sources** page
2. Find the source you want to delete
3. Click the **Delete** button (trash icon)
4. Browser prompts: "Are you sure you want to delete this source?"
5. Click **OK** to confirm deletion
6. The source row disappears from the table

**What Happens:**

- Source configuration is deleted from the database
- Past articles from this source are NOT deleted (archive remains intact)
- Source will not appear in future pipelines

### Monitoring Source Health

MDInsights automatically monitors each source's article collection patterns. If a source starts returning zero articles or significantly fewer than its baseline, you'll receive a health alert email.

**Health Alert Email:**

- **Subject:** `Source Health Alert - [Date]`
- **Sent to:** `ADMIN_EMAIL` from `.env`
- **Contents:** Table listing sources with issues

**Alert Types:**

- **Critical** — Source returned zero articles (normally returns some)
- **Warning** — Source returned articles but below statistical baseline

**Viewing Health Details via Dashboard:**

1. Navigate to `/admin` (dashboard)
2. If recent pipeline run triggered health alerts, you'll see:
   - Custom header `X-MDInsights-Health-Alerts` in HTTP response
   - Health information in structured logs

**What to Do:**

1. Check if the source website is down (visit URL in browser)
2. For Apify sources: Check Apify dashboard for actor run failures
3. For RSS sources: Validate RSS feed URL still works
4. If source is permanently down, disable it temporarily
5. If source changed structure, contact development team for scraper update

**Health Check Details:**

- Baseline calculated from last 7 days of article counts
- Warning threshold: Baseline average - 2 standard deviations, or 30% of baseline (whichever is more lenient)
- Consecutive low runs tracked (multiple days below baseline indicates systemic issue)

---

## 4. Recipient Management

MDInsights delivers role-specific intelligence briefs to four audiences via email. You can manage recipient lists for each role independently.

### Viewing Recipients

1. Open browser to `http://[server-address]:8001/admin/recipients`
2. Or click **Recipients** in the left navigation menu
3. You'll see four cards, one for each role:
   - **Brokers**
   - **Leadership**
   - **Compliance**
   - **Underwriting**

Each card shows:
- **TO** — Primary recipients (appear in To: field)
- **CC** — Carbon copy recipients (appear in Cc: field)
- **BCC** — Blind carbon copy recipients (hidden from other recipients)

### Editing Recipients for a Role

**Steps:**

1. Navigate to **Recipients** page (`/admin/recipients`)
2. Find the card for the role you want to edit (e.g., Brokers)
3. Click the **Edit** button on that card
4. The card transforms into an edit form with three text fields:
   - **TO:** — Enter comma-separated email addresses
   - **CC:** — Enter comma-separated email addresses (optional)
   - **BCC:** — Enter comma-separated email addresses (optional)
5. Click **Save** to apply changes, or **Cancel** to discard

**Email Format:**

- Use comma-separated format: `user1@marsh.com, user2@marsh.com, user3@marsh.com`
- Spaces after commas are optional (system trims whitespace automatically)
- Each email must be valid format (e.g., `name@domain.com`)

**Validation:**

- System validates each email address before saving
- If any email is invalid, you'll see an error message with the specific problematic address
- All emails must pass validation before changes are saved

**What Happens After Saving:**

- Changes are written to the `.env` file immediately
- Changes take effect on the **next pipeline run** (06:00 the following day)
- No server restart required

### Removing All Recipients for a Role

If you want to temporarily stop sending reports to a specific role:

1. Edit that role's recipients
2. Clear all three fields (TO, CC, BCC)
3. Click **Save**
4. Future pipeline runs will skip email delivery for that role (report still generated and archived)

**Note:** If you clear TO but leave CC or BCC populated, the email will still be sent (to CC/BCC recipients). Clear all three fields to fully disable email delivery.

### Testing Email Delivery

**Manual Pipeline Trigger (Recommended):**

1. Navigate to **Trigger** page (`/admin/trigger`)
2. Click **Trigger Pipeline** button
3. Pipeline runs immediately with current recipient configuration
4. Check recipient inboxes within 5-10 minutes

**Task Scheduler Manual Run:**

1. Open Task Scheduler (`taskschd.msc`)
2. Find `MDInsights Daily Pipeline` task
3. Right-click → **Run**
4. Check recipient inboxes within 5-10 minutes

**Troubleshooting Email Delivery:**

If recipients don't receive emails:

1. Check **Recent Runs** table on dashboard — ensure run status is "Completed"
2. Check log file for email delivery errors:
   - Location: `data\logs\mdinsights_[today's-date].log`
   - Search for: `"email_sent"` or `"email_failed"`
3. Verify Microsoft Graph credentials in `.env`:
   - `MICROSOFT_TENANT_ID`
   - `MICROSOFT_CLIENT_ID`
   - `MICROSOFT_CLIENT_SECRET`
   - `SENDER_EMAIL`
4. Verify recipient emails are correctly formatted (no typos)

---

## 5. Report Archive and Search

### Browsing Past Reports

1. Navigate to **Archive** page (`/admin/archive`)
2. Or click **Archive** in the left navigation menu
3. You'll see a date-grouped list of reports, newest first
4. Each date row shows four badges (one per role)
5. Click a badge to view that report in your browser

**Filters:**

- **Month** — Dropdown to filter by month (YYYY-MM format)
- **Role** — Dropdown to filter by specific role

**File Locations:**

Reports are stored on disk at:
```
data/reports/{role}/{YYYY-MM-DD}.html
```

Example:
```
data/reports/brokers/2026-02-08.html
data/reports/leadership/2026-02-08.html
```

### Searching Articles

The search page provides full-text search across all collected articles with advanced filtering.

**Accessing Search:**

1. Navigate to **Search** page (`/admin/search`)
2. Or click **Search** in the left navigation menu

**Search Fields:**

- **Keyword** — Full-text search across article title, description, and summary
  - Uses SQLite FTS5 (full-text search) with BM25 ranking
  - Searches are debounced (results update 300ms after you stop typing)

**Filters:**

- **Role** — Filter by target role (Brokers, Leadership, Compliance, Underwriting)
- **Priority** — Filter by priority level (Critical, High, Medium, Monitor)
- **Source** — Filter by source name (dropdown populated from database)
- **Date From** — Filter articles published on or after this date (YYYY-MM-DD)
- **Date To** — Filter articles published on or before this date (YYYY-MM-DD)

**Results:**

- **25 articles per page** (paginated)
- Articles display: Title, Source, Published Date, Priority, Roles
- Click article title to view full details
- Total result count shown above results

**Search Examples:**

| Goal | How to Search |
|------|---------------|
| All critical articles | Priority: Critical |
| Articles for brokers | Role: Brokers |
| Articles about cyber insurance | Keyword: cyber insurance |
| Articles from last week | Date From: 2026-02-01, Date To: 2026-02-08 |
| Articles from Insurance Journal | Source: Insurance Journal |

---

## 6. Manual Pipeline Trigger

**When to Use:**

- Testing after configuration changes (new source, new recipients)
- Re-running pipeline after a failure
- Generating reports outside the normal 06:00 schedule

**How to Trigger:**

**Option 1: Via Admin Dashboard (Recommended)**

1. Navigate to **Trigger** page (`/admin/trigger`)
2. Click **Trigger Pipeline** button
3. Wait 5-10 seconds (page will reload with report)
4. Browser displays the generated report for the Brokers role
5. Check dashboard to verify run status

**Option 2: Via Task Scheduler**

1. Press `Windows + R`, type `taskschd.msc`, press Enter
2. In Task Scheduler Library, find `MDInsights Daily Pipeline`
3. Right-click → **Run**
4. Task runs in background
5. Check dashboard after 5-10 minutes

**What Happens:**

1. **Collection** (5-20 minutes) — Fetch articles from all enabled sources
2. **Deduplication** (1-2 minutes) — Remove duplicate articles using semantic similarity
3. **Classification** (10-30 minutes) — AI classifies each article by priority and roles
4. **Report Generation** (1-2 minutes) — Generate HTML briefs for each role
5. **Email Delivery** (1-2 minutes) — Send briefs to configured recipients
6. **Archival** (10 seconds) — Save reports to `data/reports/`

**Total Time:** 20-45 minutes depending on article volume

**During Execution:**

- Dashboard shows run status as "Running" (blue badge)
- Recent Runs table updates in real-time
- Log file written to `data/logs/mdinsights_[today's-date].log`

**After Completion:**

- Dashboard shows run status as "Completed" (green badge)
- Articles appear in **Articles Today** count
- Reports available in **Archive** page
- Recipients receive emails (if configured)

---

## 7. Troubleshooting

This section covers common failure scenarios with symptom-based troubleshooting.

### Symptom: No Report Email Received

**Possible Causes:**

1. Pipeline did not run (Task Scheduler issue)
2. Pipeline ran but failed (error during execution)
3. Pipeline completed but email delivery failed
4. Email went to spam/junk folder

**Troubleshooting Steps:**

**Step 1: Check Pipeline Status**

1. Open dashboard: `http://[server-address]:8001/admin`
2. Look at **Last Run** card
3. Check status:
   - **Completed (green)** — Pipeline ran successfully, skip to Step 2
   - **Failed (red)** — Pipeline error, skip to Step 3
   - **No run today** — Task Scheduler issue, skip to Step 4

**Step 2: Check Email Delivery (Pipeline Completed)**

1. Open log file: `data\logs\mdinsights_[today's-date].log`
2. Search for `"email_sent"` — If found, emails were sent successfully
3. Search for `"email_failed"` — If found, email delivery failed
4. If `email_failed` found:
   - Check error message in log
   - Common causes:
     - **Microsoft Graph authentication failure** — Check `.env` credentials
     - **Invalid recipient email** — Check recipient list for typos
     - **Network error** — Verify server has internet access
     - **Sender email not configured** — Verify `SENDER_EMAIL` in `.env`

**Step 3: Check Pipeline Error (Pipeline Failed)**

1. Open log file: `data\logs\mdinsights_[today's-date].log`
2. Search for `"ERROR"` or `"error"` to find failure point
3. Common failure points:
   - **Collection failed** — Apify token invalid or source website down
   - **Classification failed** — Azure OpenAI API key invalid or quota exceeded
   - **Report generation failed** — Jinja2 template error or file permission issue

**Step 4: Check Task Scheduler (Pipeline Didn't Run)**

1. Open Task Scheduler: `taskschd.msc`
2. Find `MDInsights Daily Pipeline` task
3. Check **Last Run Result**:
   - **0x0** — Success (but pipeline may have failed internally, see Step 3)
   - **0x1** — Task exited with error code 1
   - **0x41303** — Task did not run because user was not logged on (should not happen with SYSTEM account)
4. Check **Last Run Time** — Should be 06:00 today
5. If task didn't run:
   - Right-click task → **Properties** → **Triggers** tab
   - Verify trigger is enabled and set to Daily at 06:00
   - Check **History** tab for detailed error messages

**Step 5: Check Email Client (Spam/Junk)**

1. Check recipient's spam/junk folder
2. Check email client rules (may be auto-filing to folder)
3. Verify sender address (`SENDER_EMAIL` from `.env`) is whitelisted

**Resolution:**

- If Task Scheduler issue: Re-run setup: `.\deploy\setup_task.ps1`
- If pipeline error: Check logs, verify credentials in `.env`
- If email delivery error: Verify Microsoft Graph credentials and sender email
- If spam issue: Whitelist sender address in email client

### Symptom: Pipeline Ran But Reports Are Empty

**Possible Causes:**

1. All sources disabled
2. All sources returned zero articles
3. Article collection failed for all sources
4. Classification service failed

**Troubleshooting Steps:**

**Step 1: Check Source Status**

1. Navigate to **Sources** page (`/admin/sources`)
2. Check **Active Sources** count on dashboard
3. If zero active sources:
   - Enable at least one source
   - Run pipeline manually to test

**Step 2: Check Article Collection**

1. Open log file: `data\logs\mdinsights_[today's-date].log`
2. Search for `"articles_collected"`
3. If count is zero:
   - All sources failed to return articles
   - Check source health (see Source Health Alert section)
   - Check Apify dashboard for actor run failures
   - Verify `APIFY_TOKEN` in `.env` is valid

**Step 3: Check Classification**

1. Open log file: `data\logs\mdinsights_[today's-date].log`
2. Search for `"articles_classified"`
3. If count is zero but collection succeeded:
   - Azure OpenAI classification failed
   - Check `AZURE_OPENAI_API_KEY` in `.env`
   - Check Azure OpenAI quota (may be exhausted)
   - Check Azure OpenAI deployment status in Azure Portal

**Resolution:**

- If sources disabled: Enable sources and re-run pipeline
- If collection failed: Check Apify token, check source websites
- If classification failed: Check Azure OpenAI credentials and quota

### Symptom: Health Alert Email Received

**Email Subject:** `Source Health Alert - [Date]`

**Meaning:** One or more news sources are not returning articles as expected.

**Troubleshooting Steps:**

**Step 1: Review Alert Email**

The email lists sources with issues and their status:

- **Critical** — Source returned zero articles (normally returns some)
- **Warning** — Source returned articles but below statistical baseline

**Step 2: Check Source Website**

1. Open the source URL in a browser
2. Verify website is online and accessible
3. Check if website structure changed (may break scraper)

**Step 3: Check Source Type**

**For Apify Sources:**

1. Log into Apify dashboard: https://console.apify.com
2. Navigate to **Actors** → Find the actor for this source
3. Check **Last Run** status:
   - **Succeeded** — Actor ran but found zero results (website changed)
   - **Failed** — Actor crashed (configuration issue or website change)
4. Review actor run log for errors

**For RSS Sources:**

1. Open the RSS feed URL in browser
2. Verify feed is valid XML
3. Check if feed contains recent items (within last 24 hours)

**Step 4: Decide Action**

| Scenario | Action |
|----------|--------|
| Website temporarily down | Wait 24 hours, check if auto-recovers |
| Website permanently down | Disable source via admin dashboard |
| Website changed structure | Contact development team for scraper update |
| Apify actor broken | Check Apify console, contact development team |
| RSS feed URL changed | Update source URL via admin dashboard |

**Step 5: Monitor for Recovery**

1. Health check runs automatically after each pipeline execution
2. If source recovers (returns articles above threshold), alerts stop
3. If source remains below baseline for 3+ consecutive days, consider disabling

**Resolution:**

- Temporary issue: Wait for auto-recovery
- Permanent issue: Disable source
- Scraper broken: Contact development team with actor name and error details

### Symptom: Drift Alert Email Received

**Email Subject:** `Classification Drift Alert - [Date]`

**Meaning:** AI classification quality has degraded based on statistical analysis.

**When Sent:** Every Monday at 08:00 (after weekly drift check task)

**What is Drift:**

Drift occurs when AI classification patterns shift over time, potentially indicating:

- Changes in article content types
- Changes in AI model behavior (Azure OpenAI updates)
- Changes in news source quality

**Troubleshooting Steps:**

**Step 1: Review Alert Email**

Email includes:

- **Kolmogorov-Smirnov Test** results (distribution comparison)
- **Chi-Square Test** results (category proportion comparison)
- Specific metrics that failed thresholds

**Step 2: Review Recent Reports**

1. Navigate to **Archive** page
2. Review last 3-5 days of reports
3. Check if article quality or relevance has declined
4. Check if priority assignments seem appropriate

**Step 3: Check Classification Logs**

1. Open recent log files: `data\logs\mdinsights_*.log`
2. Search for `"classification_result"`
3. Review a sample of classifications:
   - Are articles being assigned appropriate priorities?
   - Are roles correctly identified?
   - Are summaries coherent and relevant?

**Step 4: Decide Action**

| Drift Type | Likely Cause | Action |
|------------|--------------|--------|
| Minor drift (p=0.04-0.05) | Normal variation | Monitor, no action needed |
| Moderate drift (p=0.01-0.04) | Content shift or model change | Review reports, monitor |
| Severe drift (p<0.01) | Systemic issue | Contact development team |

**Resolution:**

- Minor drift: No immediate action, monitoring continues
- Moderate drift: Review and monitor, may self-correct
- Severe drift: Contact development team with drift report details

### Symptom: Task Scheduler Errors

**Error Code 0x1 (Exit Code 1)**

**Meaning:** Batch script or Python script exited with error code 1

**Troubleshooting:**

1. Check log file: `data\logs\mdinsights_[date].log`
2. Look for error messages near the end of the file
3. Common causes:
   - Missing `.env` file (check project root)
   - Invalid credentials in `.env`
   - Missing Python dependencies (run: `.\venv\Scripts\pip install -r requirements.txt`)
   - Database locked (another process using it)

**Error Code 0x41303**

**Meaning:** Task did not run because user was not logged on (should not happen with SYSTEM account)

**Troubleshooting:**

1. Open Task Scheduler → Right-click task → **Properties**
2. Check **General** tab:
   - Should say "Run whether user is logged on or not"
   - Should show account: `SYSTEM`
3. If incorrect, re-run setup: `.\deploy\setup_task.ps1`

**Task Shows "Running" But Never Completes**

**Meaning:** Task hung, likely due to network timeout or process deadlock

**Troubleshooting:**

1. Open Task Manager
2. Find `python.exe` process (may show as "Python" or "MDInsights")
3. Check CPU and memory usage:
   - High CPU — Process is working (wait longer)
   - Zero CPU for >5 minutes — Process hung (kill it)
4. If hung:
   - Right-click process → **End Task**
   - Check log file for last operation before hang
   - Re-run pipeline manually to test

**Resolution:**

- Check logs for specific error
- Verify `.env` configuration
- Re-run setup script if task properties incorrect
- Kill hung processes and re-run manually

---

## 8. Task Scheduler Reference

MDInsights uses four Windows Task Scheduler tasks for automation.

### Task 1: MDInsights Daily Pipeline

**Trigger:** Daily at 06:00
**Script:** `deploy\run_mdinsights.bat`
**Purpose:** Full pipeline execution (collect, classify, report, email)
**Timeout:** 2 hours
**Retry:** 2 attempts, 10 minutes apart

**Task Properties:**

- Runs as: **SYSTEM** (highest privileges)
- Run whether user is logged on or not
- Start when available (catches up if machine was off)
- Network required: Yes (Apify, Azure OpenAI, Microsoft Graph)
- Allow on-demand start: Yes

**Logs:**

- Location: `data\logs\mdinsights_YYYY-MM-DD.log`
- Format: JSON structured logs (one JSON object per line)
- Rotation: Daily, retained 30 days

### Task 2: MDInsights Daily Pipeline - Backup

**Trigger:** Daily at 07:00 (1 hour after pipeline)
**Script:** `venv\Scripts\python.exe scripts\backup_db.py`
**Purpose:** Database backup to Azure Blob Storage
**Timeout:** 30 minutes

**Task Properties:**

- Runs as: **SYSTEM**
- Backs up `data/mdinsights.db` to Azure Blob Storage
- Local backup copy: `data/backups/mdinsights_YYYY-MM-DD_HHMMSS.db`
- Retention: 30 days (configurable via `BACKUP_RETENTION_DAYS` in `.env`)

**What Gets Backed Up:**

- All news articles
- All sources
- All pipeline runs
- Full-text search index

**Backup Verification:**

1. Check `data/backups/` directory for local backup files
2. Check Azure Blob Storage container (configurable via `AZURE_STORAGE_CONTAINER` in `.env`)
3. Monitor task sends alert if backup is >36 hours old

### Task 3: MDInsights Daily Pipeline - Drift Check

**Trigger:** Weekly on Monday at 08:00 (2 hours after pipeline)
**Script:** `venv\Scripts\python.exe scripts\check_drift.py`
**Purpose:** AI classification quality monitoring (statistical drift detection)
**Timeout:** 10 minutes

**Task Properties:**

- Runs as: **SYSTEM**
- Compares last 14 days of classifications against 14-day baseline
- Uses Kolmogorov-Smirnov test and Chi-Square test
- Sends alert email if p-value < 0.05 (statistically significant drift)

**What is Checked:**

- Priority distribution (Critical, High, Medium, Monitor)
- Role assignment patterns
- Summary length consistency

**Alert Threshold:**

- p-value < 0.05 — Statistically significant drift detected
- Email sent to `ADMIN_EMAIL` with detailed report

### Task 4: MDInsights Daily Pipeline - Monitor

**Trigger:** Daily at 09:00 (3 hours after pipeline)
**Script:** `venv\Scripts\python.exe deploy\check_last_run.py`
**Purpose:** Verify pipeline ran successfully, send alert if failed
**Timeout:** 5 minutes

**Task Properties:**

- Runs as: **SYSTEM**
- Checks four independent signals:
  1. Database Run record from today with COMPLETED status
  2. Log file exists for today
  3. Archived reports exist for today (one per role)
  4. Database backup is recent (<36 hours old)
- Exit code 0 if all checks pass (no alert)
- Exit code 1 if any check fails (triggers Task Scheduler alert, sends email)

**What This Catches:**

- Task Scheduler failures (task didn't run)
- Batch script crashes (process killed)
- Machine offline during scheduled time
- Pipeline ran but reports not generated
- Database corruption

**Alert Email:**

Sent to `ADMIN_EMAIL` with:
- List of failed checks
- Instructions on what to check (Task Scheduler, logs, database, Event Viewer)

### Managing Tasks

**View Tasks:**
```
Open Task Scheduler: taskschd.msc
Navigate to: Task Scheduler Library
```

**Run Task Manually:**
```
Right-click task → Run
```

**View Task History:**
```
Right-click task → Properties → History tab
```

**Disable Task Temporarily:**
```
Right-click task → Disable
```

**Re-Enable Task:**
```
Right-click task → Enable
```

**Delete All Tasks:**
```powershell
schtasks /delete /tn "MDInsights Daily Pipeline" /f
schtasks /delete /tn "MDInsights Daily Pipeline - Backup" /f
schtasks /delete /tn "MDInsights Daily Pipeline - Drift Check" /f
schtasks /delete /tn "MDInsights Daily Pipeline - Monitor" /f
```

**Recreate Tasks:**
```powershell
cd C:\BrasilIntel\mdinsights
.\deploy\setup_task.ps1
```

---

## 9. Configuration Reference

All configuration is stored in `.env` file in the project root.

### Critical Configuration (Required for System to Work)

**Azure OpenAI** (for AI classification):
```
AZURE_OPENAI_ENDPOINT=https://[your-resource].openai.azure.com/
AZURE_OPENAI_API_KEY=[your-api-key]
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

**Microsoft Graph** (for email delivery):
```
MICROSOFT_TENANT_ID=[your-tenant-id]
MICROSOFT_CLIENT_ID=[your-client-id]
MICROSOFT_CLIENT_SECRET=[your-client-secret]
SENDER_EMAIL=mdinsights@marsh.com
```

**Apify** (for web scraping):
```
APIFY_TOKEN=[your-apify-token]
```

**Admin Email** (for failure alerts):
```
ADMIN_EMAIL=admin@marsh.com
```

### Email Recipients (Configurable via Admin Dashboard)

**Brokers:**
```
REPORT_RECIPIENTS_BROKERS=broker1@marsh.com,broker2@marsh.com
REPORT_RECIPIENTS_BROKERS_CC=
REPORT_RECIPIENTS_BROKERS_BCC=
```

**Leadership:**
```
REPORT_RECIPIENTS_LEADERSHIP=ceo@marsh.com,cfo@marsh.com
REPORT_RECIPIENTS_LEADERSHIP_CC=
REPORT_RECIPIENTS_LEADERSHIP_BCC=
```

**Compliance:**
```
REPORT_RECIPIENTS_COMPLIANCE=compliance@marsh.com
REPORT_RECIPIENTS_COMPLIANCE_CC=
REPORT_RECIPIENTS_COMPLIANCE_BCC=
```

**Underwriting:**
```
REPORT_RECIPIENTS_UNDERWRITING=underwriting@marsh.com
REPORT_RECIPIENTS_UNDERWRITING_CC=
REPORT_RECIPIENTS_UNDERWRITING_BCC=
```

**Note:** These can also be edited via the admin dashboard at `/admin/recipients`

### Optional Configuration

**Database:**
```
DATABASE_URL=sqlite:///./data/mdinsights.db
DATA_DIR=./data
```

**Application:**
```
DEBUG=False
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8001
```

**Backup:**
```
AZURE_STORAGE_CONNECTION_STRING=[connection-string]
AZURE_STORAGE_CONTAINER=mdinsights-backups
BACKUP_RETENTION_DAYS=30
```

**Company Branding:**
```
COMPANY_NAME=Marsh
```

### Editing Configuration

**Method 1: Text Editor (Recommended)**

1. Open File Explorer, navigate to: `C:\BrasilIntel\mdinsights`
2. Right-click `.env` → **Edit with Notepad**
3. Make changes
4. Save file
5. **No restart required** — Changes take effect on next pipeline run

**Method 2: Admin Dashboard (Recipients Only)**

1. Navigate to `/admin/recipients`
2. Edit recipients inline
3. Changes saved to `.env` automatically

**After Editing `.env`:**

- Changes take effect on next scheduled pipeline run (06:00)
- To apply immediately: Trigger pipeline manually via `/admin/trigger`

---

## 10. Contact and Support

### When to Contact Development Team

Contact the development team when:

1. **Source scrapers broken** — Website structure changed, Apify actor failing
2. **Severe classification drift** — AI quality degraded significantly (p<0.01)
3. **System errors** — Python exceptions, database corruption, unrecoverable errors
4. **Feature requests** — Need new source, new report format, new role

**Do NOT contact development for:**

- Recipient list changes (use admin dashboard)
- Source enable/disable (use admin dashboard)
- Task Scheduler basic troubleshooting (use this guide)
- Email delivery issues (check Microsoft Graph credentials first)

### Information to Provide When Reporting Issues

**For Source Issues:**

- Source name
- Source URL
- Error message from Apify dashboard or log file
- Date/time of failure

**For Classification Issues:**

- Drift report email (if received)
- Sample articles that were mis-classified
- Expected vs. actual priority/role assignments
- Date range of affected articles

**For System Errors:**

- Log file: `data\logs\mdinsights_[date].log`
- Error message (search for "ERROR" in log)
- Task Scheduler history (screenshot if available)
- Date/time of error

### Log File Locations

**Pipeline logs:**
```
data\logs\mdinsights_YYYY-MM-DD.log
```

**Database:**
```
data\mdinsights.db
```

**Archived reports:**
```
data\reports\{role}\YYYY-MM-DD.html
```

**Database backups:**
```
data\backups\mdinsights_YYYY-MM-DD_HHMMSS.db
```

### Useful Commands for Support

**Check Python version:**
```powershell
.\venv\Scripts\python --version
```

**Check installed packages:**
```powershell
.\venv\Scripts\pip list
```

**View recent log entries:**
```powershell
Get-Content data\logs\mdinsights_*.log | Select-Object -Last 50
```

**Check database size:**
```powershell
Get-Item data\mdinsights.db | Select-Object Name, Length
```

---

## Appendix: Quick Reference

### Daily Schedule

| Time | Task | What Happens |
|------|------|--------------|
| 06:00 | Pipeline | Collect articles, classify, generate reports, send emails |
| 07:00 | Backup | Database backup to Azure Blob Storage |
| Monday 08:00 | Drift Check | AI classification quality check (weekly) |
| 09:00 | Monitor | Verify pipeline ran, send alert if failed |

### Admin Dashboard URLs

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/admin` | System status overview |
| Sources | `/admin/sources` | Manage news sources |
| Recipients | `/admin/recipients` | Manage email recipients |
| Archive | `/admin/archive` | Browse past reports |
| Search | `/admin/search` | Search articles |
| Trigger | `/admin/trigger` | Manual pipeline run |

### Common Tasks

| Task | How To |
|------|--------|
| Add source | `/admin/sources` → + Add New Source |
| Disable source | `/admin/sources` → Toggle button |
| Edit recipients | `/admin/recipients` → Edit button |
| View today's report | `/admin/archive` → Today's date → Role badge |
| Trigger pipeline manually | `/admin/trigger` → Trigger Pipeline button |
| Search articles | `/admin/search` → Enter keywords, apply filters |

### File Locations

| Item | Path |
|------|------|
| Logs | `data\logs\mdinsights_YYYY-MM-DD.log` |
| Database | `data\mdinsights.db` |
| Backups | `data\backups\` |
| Reports | `data\reports\{role}\YYYY-MM-DD.html` |
| Config | `.env` |
| Batch script | `deploy\run_mdinsights.bat` |

### Alert Email Types

| Subject | Frequency | Meaning |
|---------|-----------|---------|
| Pipeline Monitor Alert | As needed | Pipeline failed or didn't run |
| Source Health Alert | As needed | Source returning zero or low articles |
| Classification Drift Alert | Weekly (Mon) | AI quality degraded |

---

**Document Version:** 1.0
**Last Updated:** 2026-02-08
**For:** MDInsights Phase 8 (Polish and Launch)
