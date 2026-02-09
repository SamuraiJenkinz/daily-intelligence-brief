# MDInsights Deployment Guide

**Complete guide to deploying MDInsights on Windows Server from scratch.**

This guide walks through setting up MDInsights on a fresh Windows Server 2019+ installation, including all Azure service configurations, environment setup, and production validation.

**Target Environment**: Windows Server 2019 or later
**Estimated Total Time**: 90 minutes
**Skill Level**: Intermediate (basic PowerShell, Azure portal experience)

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation-15-min)
3. [Azure AD App Registration](#3-azure-ad-app-registration-20-min) ⚠️ **CRITICAL**
4. [Azure OpenAI Configuration](#4-azure-openai-configuration-10-min)
5. [Apify Configuration](#5-apify-configuration-5-min)
6. [Azure Blob Storage for Backups](#6-azure-blob-storage-for-backups-10-min)
7. [Database Initialization](#7-database-initialization-5-min)
8. [Task Scheduler Configuration](#8-task-scheduler-configuration-10-min)
9. [Web Server Configuration](#9-web-server-configuration-5-min)
10. [Validation](#10-validation-10-min)
11. [Production Checklist](#11-production-checklist)
12. [Maintenance Notes](#12-maintenance-notes)
13. [Appendix A: Environment Variable Reference](#appendix-a-environment-variable-reference)
14. [Appendix B: Troubleshooting Deployment Issues](#appendix-b-troubleshooting-deployment-issues)

---

## 1. Prerequisites

Before beginning, ensure you have:

### Server Requirements
- [ ] Windows Server 2019 or later
- [ ] Administrator access to the server
- [ ] Internet connectivity
- [ ] Minimum 4 GB RAM, 20 GB disk space
- [ ] PowerShell 5.1 or later

### Software Requirements
- [ ] Python 3.11+ installed ([python.org/downloads](https://www.python.org/downloads/))
  - Verify: `python --version` should show 3.11.x or higher
  - Add to PATH during installation
- [ ] Git for Windows ([git-scm.com](https://git-scm.com/download/win))
  - Verify: `git --version`

### Azure Subscriptions and Access
- [ ] Active Azure subscription
- [ ] Azure AD admin rights (to register applications and grant consent)
- [ ] Azure OpenAI service access (may require application approval)
- [ ] Storage account admin access

### External Services
- [ ] Apify account ([apify.com](https://apify.com/)) - Free tier available
- [ ] Valid Microsoft 365 tenant with mailbox for sender email

### Network Configuration
- [ ] Outbound HTTPS (443) allowed to:
  - `*.apify.com` (web scraping)
  - `*.openai.azure.com` (AI classification)
  - `graph.microsoft.com` (email delivery)
  - `*.blob.core.windows.net` (backup storage)

---

## 2. Installation (15 min)

### 2.1 Clone Repository

Open PowerShell as Administrator:

```powershell
# Navigate to installation directory
cd C:\

# Clone repository
git clone https://github.com/SamuraiJenkinz/daily-intelligence-brief.git
cd daily-intelligence-brief

# Verify files present
dir
```

**Expected output**: You should see directories: `app/`, `deploy/`, `scripts/`, `templates/`, and files: `requirements.txt`, `.env.example`

### 2.2 Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Verify activation (prompt should show (venv))
```

**Expected output**: Your PowerShell prompt should now start with `(venv)`

### 2.3 Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements (takes 3-5 minutes)
pip install -r requirements.txt

# Verify installation
pip list
```

**Expected output**: Should see packages including `fastapi`, `sqlalchemy`, `openai`, `apify-client`, `structlog`

### 2.4 Create Environment File

```powershell
# Copy template to .env
copy .env.example .env

# Open in notepad for editing
notepad .env
```

**DO NOT fill in values yet** - we'll configure each section in the following steps.

---

## 3. Azure AD App Registration (20 min)

⚠️ **CRITICAL SECTION** - Email delivery will NOT work without proper app registration and permissions.

This section configures Microsoft Graph API access for sending daily intelligence briefs via email.

### 3.1 Navigate to Azure AD Portal

1. Open browser and navigate to: **https://entra.microsoft.com/**
2. Sign in with Azure AD admin credentials
3. You should see the Microsoft Entra admin center

**IMPORTANT**: You MUST have Azure AD admin rights to complete this section. If you don't see "App registrations" in the menu, contact your Azure AD administrator.

### 3.2 Create New App Registration

1. In left sidebar, expand **Applications**
2. Click **App registrations**
3. Click **+ New registration** (top of page)

![App Registration Screenshot Location](https://learn.microsoft.com/en-us/entra/identity-platform/media/quickstart-register-app/portal-02-app-reg-01.png)

Configure the registration:

| Field | Value |
|-------|-------|
| **Name** | `MDInsights Email Service` |
| **Supported account types** | ☑️ Accounts in this organizational directory only (Single tenant) |
| **Redirect URI** | Leave blank (this is a daemon/service app) |

4. Click **Register**

### 3.3 Copy Application Identifiers

After registration completes, you'll see the **Overview** page.

**Copy these values to your .env file:**

| Portal Field | .env Variable | Example |
|--------------|---------------|---------|
| **Directory (tenant) ID** | `MICROSOFT_TENANT_ID` | `12345678-1234-1234-1234-123456789abc` |
| **Application (client) ID** | `MICROSOFT_CLIENT_ID` | `87654321-4321-4321-4321-abcdef123456` |

**Where to find them:**
- Both values are prominently displayed on the app's **Overview** page
- Directory (tenant) ID is in the "Essentials" section
- Application (client) ID is also in "Essentials" section

### 3.4 Create Client Secret

⚠️ **SECURITY CRITICAL** - The client secret is like a password for the application.

1. In left sidebar, click **Certificates & secrets**
2. Click **Client secrets** tab
3. Click **+ New client secret**

Configure the secret:

| Field | Value |
|-------|-------|
| **Description** | `MDInsights Production Secret` |
| **Expires** | **24 months** (recommended) |

4. Click **Add**

**IMMEDIATELY copy the VALUE (not the Secret ID):**
- The secret VALUE is displayed ONLY ONCE
- Copy it to `MICROSOFT_CLIENT_SECRET` in your .env file
- If you lose it, you must create a new secret

⚠️ **SET A CALENDAR REMINDER** for 23 months from now to rotate this secret BEFORE it expires.

**What the secret VALUE looks like:**
```
Example: xK8Q~abcdefghijklmnopqrstuvwxyz1234567890AB
         ^^^^
         Starts with random characters, ~40 characters long
```

### 3.5 Configure API Permissions

This grants the app permission to send emails on behalf of users.

1. In left sidebar, click **API permissions**
2. Click **+ Add a permission**
3. Click **Microsoft Graph** tile
4. Click **Application permissions** (NOT Delegated permissions)

**Search and add this permission:**

5. In the search box, type: `Mail.Send`
6. Expand **Mail** category
7. Check the box for **Mail.Send**
8. Click **Add permissions** at bottom

**Verify the permission was added:**
- You should see `Mail.Send` in the permissions list
- Status will show "Not granted for [Your Organization]"

### 3.6 Grant Admin Consent

⚠️ **REQUIRED** - The app will NOT work without admin consent.

**This step requires Global Administrator or Application Administrator role.**

1. On the **API permissions** page, click **Grant admin consent for [Your Organization]**
2. Click **Yes** in the confirmation dialog
3. Wait for the green checkmark

**Expected result:**
- Status column changes to: ✅ **Granted for [Your Organization]**

If you don't see the "Grant admin consent" button, you lack admin rights. Contact your Azure AD Global Administrator to grant consent.

### 3.7 Update .env File

Your .env file should now have these values filled in:

```ini
MICROSOFT_TENANT_ID=12345678-1234-1234-1234-123456789abc
MICROSOFT_CLIENT_ID=87654321-4321-4321-4321-abcdef123456
MICROSOFT_CLIENT_SECRET=xK8Q~abcdefghijklmnopqrstuvwxyz1234567890AB
SENDER_EMAIL=intelligence@yourcompany.com
```

**SENDER_EMAIL notes:**
- Must be a valid mailbox in your Microsoft 365 tenant
- Recommended: Create a dedicated mailbox (e.g., `intelligence@marsh.com`)
- Emails will appear to come FROM this address
- Recipients can reply to this address

### 3.8 Verify App Registration

Quick verification checklist:

- [ ] App created in Entra admin center
- [ ] Tenant ID copied to .env
- [ ] Client ID copied to .env
- [ ] Client secret created and VALUE copied to .env
- [ ] Mail.Send permission added (Application permission, not Delegated)
- [ ] Admin consent granted (green checkmark visible)
- [ ] Sender email configured (valid mailbox in tenant)

---

## 4. Azure OpenAI Configuration (10 min)

Azure OpenAI provides the GPT-4o model used for article classification and report generation.

### 4.1 Navigate to Azure OpenAI Service

1. Navigate to: **https://portal.azure.com/**
2. Search for: `Azure OpenAI` (top search bar)
3. Click **Azure OpenAI** service

If you don't see an Azure OpenAI resource:
- Azure OpenAI requires application approval
- Apply at: https://aka.ms/oai/access
- Approval typically takes 1-2 business days

### 4.2 Select Your Resource

1. Click your Azure OpenAI resource name
   - If you don't have one, click **+ Create** to provision a new resource
   - Region: Choose closest to your location
   - Pricing tier: Standard S0

### 4.3 Copy Keys and Endpoint

1. In left sidebar, click **Keys and Endpoint**
2. Copy these values to your .env file:

| Portal Field | .env Variable | Notes |
|--------------|---------------|-------|
| **Endpoint** | `AZURE_OPENAI_ENDPOINT` | Include trailing slash |
| **KEY 1** | `AZURE_OPENAI_API_KEY` | Either KEY 1 or KEY 2 works |

**Endpoint format:**
```
https://your-resource-name.openai.azure.com/
                                           ^
                                           Trailing slash REQUIRED
```

### 4.4 Verify Model Deployment

1. In left sidebar, click **Model deployments**
2. Click **Manage Deployments** (opens Azure OpenAI Studio)

**Check for existing deployment:**
- Look for a deployment using model `gpt-4o` or `gpt-4o-mini`
- Note the **Deployment name** (you chose this when deploying)

**If no deployment exists, create one:**

3. Click **+ Create new deployment**

| Field | Value |
|-------|-------|
| **Model** | `gpt-4o` (recommended) or `gpt-4o-mini` (cheaper) |
| **Deployment name** | `gpt-4o` (use this exact name for simplicity) |
| **Deployment type** | Standard |
| **Tokens per minute rate limit** | 60K (minimum recommended) |

4. Click **Create**

### 4.5 Update .env File

```ini
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=abc123def456ghi789jkl012mno345pq
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

**Notes:**
- API version `2024-08-01-preview` supports structured outputs (required)
- Don't change the API version unless you know it's compatible

---

## 5. Apify Configuration (5 min)

Apify provides web scraping infrastructure for collecting news articles.

### 5.1 Create Apify Account

1. Navigate to: **https://apify.com/**
2. Click **Sign up** (top right)
3. Create free account or sign in with Google/GitHub

**Free tier includes:**
- $5 USD monthly credit
- Sufficient for testing and small-scale production
- Production typically costs $20-50/month depending on source count

### 5.2 Get API Token

1. After sign in, navigate to: **https://console.apify.com/account/integrations**
   - Or: Click your profile → Settings → Integrations
2. Find **Personal API tokens** section
3. Copy the **Personal API token** value

### 5.3 Update .env File

```ini
APIFY_TOKEN=apify_api_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
```

**Token format:**
- Starts with `apify_api_`
- Followed by random alphanumeric characters

---

## 6. Azure Blob Storage for Backups (10 min)

Azure Blob Storage provides secure cloud backup for the SQLite database.

### 6.1 Create Storage Account (if needed)

1. Navigate to: **https://portal.azure.com/**
2. Search for: `Storage accounts`
3. Click **Storage accounts**

**If you already have a storage account**, skip to step 6.2.

**To create new storage account:**

4. Click **+ Create**

| Field | Value |
|-------|-------|
| **Subscription** | Your Azure subscription |
| **Resource group** | Create new or use existing |
| **Storage account name** | `mdinsightsbackup` (or your preference, must be globally unique) |
| **Region** | Same as your server location |
| **Performance** | Standard |
| **Redundancy** | LRS (Locally-redundant storage) - sufficient for backups |

5. Click **Review + create** → **Create**
6. Wait for deployment (1-2 minutes)

### 6.2 Get Connection String

1. Navigate to your storage account
2. In left sidebar, expand **Security + networking**
3. Click **Access keys**
4. Click **Show keys**
5. Under **key1**, click **Show** next to **Connection string**
6. Click the copy icon to copy the full connection string

### 6.3 Update .env File

```ini
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=mdinsightsbackup;AccountKey=abc123...;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER=mdinsights-backups
BACKUP_RETENTION_DAYS=30
```

**Notes:**
- Connection string is very long (~200 characters)
- Container `mdinsights-backups` will be created automatically on first backup
- `BACKUP_RETENTION_DAYS=30` means backups older than 30 days are auto-deleted

**Verify connection string format:**
```
DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net
```

---

## 7. Database Initialization (5 min)

Initialize the SQLite database and seed with news sources.

### 7.1 Create Data Directory

```powershell
# From project root (C:\daily-intelligence-brief)
mkdir data
mkdir data\logs
```

### 7.2 Run Database Seed Script

```powershell
# Ensure virtual environment is activated
.\venv\Scripts\activate

# Run seed script
python scripts\seed_sources.py
```

**Expected output:**
```
Seeding news sources...
   - Created: 20
   - Skipped (already exists): 0
```

**What this does:**
- Creates SQLite database at `data/mdinsights.db`
- Creates tables: `news_articles`, `sources`, `runs`, `insurers`
- Seeds 20 default news sources (Apify and RSS sources)
- Idempotent (safe to run multiple times)

### 7.3 Verify Database

```powershell
# Check database file exists
dir data\mdinsights.db

# Query source count
python -c "from app.database import SessionLocal; from app.models import Source; db = SessionLocal(); print(f'Sources: {db.query(Source).count()}'); db.close()"
```

**Expected output:**
```
Sources: 20
```

---

## 8. Task Scheduler Configuration (10 min)

Configure Windows Task Scheduler to run MDInsights pipeline daily and automated maintenance tasks.

### 8.1 Review Batch Script

The batch script `deploy\run_mdinsights.bat` wraps the pipeline execution:

```powershell
# View the script
type deploy\run_mdinsights.bat
```

**What it does:**
- Activates virtual environment
- Runs pipeline: `python -m app.main run-pipeline`
- Logs output to: `data\logs\mdinsights_YYYY-MM-DD.log`
- Returns exit code to Task Scheduler

### 8.2 Run Setup Script

The PowerShell script `deploy\setup_task.ps1` creates 4 scheduled tasks:

```powershell
# Run with Administrator privileges
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\deploy\setup_task.ps1
```

**Expected output:**
```
MDInsights Task Scheduler Setup
================================

Project path: C:\daily-intelligence-brief
Task name: MDInsights Daily Pipeline
Pipeline time: 06:00
Backup time: 07:00
Drift check: Monday at 08:00
Monitor time: 09:00

✓ Project structure validated
✓ Pipeline task registered: MDInsights Daily Pipeline
✓ Backup task registered: MDInsights Daily Pipeline - Backup
✓ Drift check task registered: MDInsights Daily Pipeline - Drift Check
✓ Monitor task registered: MDInsights Daily Pipeline - Monitor
```

### 8.3 Verify Tasks Created

```powershell
# List MDInsights tasks
schtasks /query /tn "MDInsights*" /fo LIST
```

**Expected tasks:**
1. **MDInsights Daily Pipeline** - Runs pipeline at 06:00 daily
2. **MDInsights Daily Pipeline - Backup** - Backs up database at 07:00 daily
3. **MDInsights Daily Pipeline - Drift Check** - Checks classification drift Mondays at 08:00
4. **MDInsights Daily Pipeline - Monitor** - Verifies pipeline/backup success at 09:00 daily

### 8.4 Test Manual Execution

```powershell
# Run pipeline task now (test execution)
schtasks /run /tn "MDInsights Daily Pipeline"

# Wait 2-3 minutes, then check status
schtasks /query /tn "MDInsights Daily Pipeline" /v /fo LIST

# Check log output
type "data\logs\mdinsights_*.log" | Select-Object -Last 50
```

**Expected results:**
- Task runs without errors
- Log file created in `data\logs\`
- Exit code 0 (success) in log file

**If errors occur**, see [Appendix B: Troubleshooting](#appendix-b-troubleshooting-deployment-issues)

### 8.5 Task Configuration Details

All tasks run with these settings:
- **User**: SYSTEM account (runs whether user logged on or not)
- **Privileges**: Highest (for network access and file operations)
- **Triggers**: Daily at specified time, starts when available if server was off
- **Network**: Required for pipeline task (external API calls)
- **Timeout**: 2 hours for pipeline, 30 minutes for backup, 10 minutes for drift/monitor
- **Restart**: Pipeline auto-restarts 2 times on failure (10-minute interval)

---

## 9. Web Server Configuration (5 min)

Configure the web admin interface to run as a Windows Service or via Task Scheduler.

### 9.1 Test Web Server Manually

```powershell
# Activate virtual environment
.\venv\Scripts\activate

# Start web server
python -m app.main web --host 0.0.0.0 --port 8001
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 9.2 Access Admin Interface

1. Open browser
2. Navigate to: **http://localhost:8001**

**Expected pages:**
- Dashboard (should show 0 runs initially)
- Sources management (should show 20 sources)
- Archive (empty initially)
- Search (functional search interface)
- Recipients configuration
- Manual trigger

3. Press **CTRL+C** to stop the server

### 9.3 Create Web Server Task (Optional)

To run the web server continuously:

```powershell
# Create web server task
$Action = New-ScheduledTaskAction -Execute "C:\daily-intelligence-brief\venv\Scripts\python.exe" -Argument "-m app.main web --host 0.0.0.0 --port 8001" -WorkingDirectory "C:\daily-intelligence-brief"
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName "MDInsights Web Server" -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force
```

**Alternative: NSSM (Non-Sucking Service Manager)**
- Download from: https://nssm.cc/download
- More robust for long-running web services
- See previous documentation if preferred

### 9.4 Firewall Configuration (if needed)

If accessing admin interface from other machines:

```powershell
# Add firewall rule for port 8001
New-NetFirewallRule -DisplayName "MDInsights Web Server" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```

---

## 10. Validation (10 min)

Validate complete deployment before going to production.

### 10.1 Configuration Check

Verify all .env variables are configured:

```powershell
# Check Azure OpenAI
python -c "from app.config import get_settings; s = get_settings(); print('Azure OpenAI:', 'OK' if s.is_azure_openai_configured() else 'MISSING')"

# Check Microsoft Graph
python -c "from app.config import get_settings; s = get_settings(); print('Microsoft Graph:', 'OK' if s.is_graph_configured() else 'MISSING')"

# Check Apify
python -c "from app.config import get_settings; s = get_settings(); print('Apify:', 'OK' if s.is_apify_configured() else 'MISSING')"

# Check Azure Storage
python -c "from app.config import get_settings; s = get_settings(); print('Azure Storage:', 'OK' if s.is_azure_storage_configured() else 'MISSING')"
```

**All should show OK** - if any show MISSING, return to that section and complete configuration.

### 10.2 Azure OpenAI Test

```powershell
python scripts\test_classification.py
```

**Expected output:**
```
Testing Azure OpenAI classification...
Classification result:
  Role: Brokers
  Priority: high
  Risk factors: 2
  Regulatory: True
  ✓ Azure OpenAI working
```

### 10.3 Apify Test

```powershell
python scripts\test_collection.py
```

**Expected output:**
```
Testing Apify collection...
Collected 15 articles from Reinsurance News
✓ Apify working
```

### 10.4 Email Test

Configure at least one recipient in .env first:

```ini
REPORT_RECIPIENTS_BROKERS=your.email@yourcompany.com
```

Then test email delivery:

```powershell
python scripts\test_report.py
```

**Expected output:**
```
Generating test report...
Sending to: your.email@yourcompany.com
✓ Email sent successfully
Check your inbox for "MDInsights Daily Brief - Brokers"
```

### 10.5 Full Pipeline Test

Run complete end-to-end pipeline:

```powershell
python -m app.main run-pipeline
```

**Expected output (takes 5-10 minutes):**
```
Pipeline started...
Step 1: Health check - 20 sources healthy
Step 2: Collection - Collected 150 articles
Step 3: Deduplication - 142 unique articles
Step 4: Classification - Classified 142 articles
Step 5: Report generation - 4 reports created
Step 6: Email delivery - 4 emails sent
✓ Pipeline completed successfully
```

**Check:**
- [ ] No errors in output
- [ ] Articles collected from multiple sources
- [ ] Reports generated for each role
- [ ] Emails received by configured recipients
- [ ] Log file created in `data\logs\`

### 10.6 Backup Test

```powershell
python scripts\backup_db.py
```

**Expected output:**
```
Backing up database...
Backup uploaded to Azure Blob Storage
✓ Backup completed: mdinsights_backup_2026-02-08_120000.db
```

Verify in Azure portal:
1. Navigate to your storage account
2. Click **Containers**
3. Click **mdinsights-backups**
4. Verify backup file appears

---

## 11. Production Checklist

**Complete this checklist before declaring production ready:**

### Environment Configuration
- [ ] All .env variables configured (no placeholder values)
- [ ] Azure OpenAI endpoint and key valid
- [ ] Azure AD app registration complete with admin consent granted
- [ ] Apify token valid
- [ ] Azure Storage connection string valid
- [ ] Sender email configured (valid mailbox)
- [ ] All recipient lists configured for production users

### Security
- [ ] .env file NOT committed to source control
- [ ] Azure AD client secret expires in 24 months (calendar reminder set)
- [ ] Storage account connection string secured
- [ ] Firewall rules configured (web server port restricted if needed)
- [ ] SYSTEM account has appropriate file system permissions

### Database
- [ ] Database initialized (mdinsights.db exists)
- [ ] 20 sources seeded
- [ ] FTS5 search index created
- [ ] Database backup working (tested in step 10.6)

### Scheduling
- [ ] 4 scheduled tasks created (Pipeline, Backup, Drift Check, Monitor)
- [ ] Pipeline task tested manually (successful execution)
- [ ] Monitor task configured with ADMIN_EMAIL
- [ ] Task Scheduler logs reviewed (no errors)

### Testing
- [ ] Azure OpenAI classification test passed
- [ ] Apify collection test passed
- [ ] Email delivery test passed
- [ ] Full pipeline test passed (end-to-end)
- [ ] Backup test passed (file in Azure Blob)

### Web Interface
- [ ] Admin interface accessible (http://localhost:8001)
- [ ] Dashboard loads correctly
- [ ] Sources management functional
- [ ] Archive search working
- [ ] Recipients configuration saving correctly
- [ ] Manual trigger functional

### Monitoring
- [ ] ADMIN_EMAIL configured for failure alerts
- [ ] Log directory writable (data\logs)
- [ ] Disk space sufficient (20+ GB free)
- [ ] Task Scheduler email notifications configured (optional)

### Documentation
- [ ] Deployment documented (dates, versions, configurations)
- [ ] Admin credentials documented securely
- [ ] Escalation contacts documented
- [ ] Maintenance schedule documented

### Production Readiness
- [ ] Stakeholders notified of go-live date
- [ ] First manual pipeline run scheduled for validation
- [ ] 24-hour monitoring plan in place
- [ ] Rollback plan documented

---

## 12. Maintenance Notes

### Regular Maintenance Tasks

#### Daily (Automated)
- 06:00 - Pipeline execution (collects, classifies, sends reports)
- 07:00 - Database backup to Azure Blob Storage
- 09:00 - Monitor check (verifies pipeline and backup succeeded)

#### Weekly (Automated)
- Monday 08:00 - Classification drift detection

#### Monthly (Manual)
- Review log files for errors or warnings
- Check disk space usage (`data\` directory)
- Verify email delivery rates (check bounce logs)
- Review source health metrics in admin dashboard

#### Quarterly (Manual)
- Review and update news sources (add/remove/disable)
- Analyze classification quality (review drift reports)
- Update recipient lists as team changes
- Test backup restore procedure

#### Annually (Manual - CRITICAL)
- Rotate Azure AD client secret (BEFORE 24-month expiry)
- Review and renew Azure service subscriptions
- Update Python dependencies (`pip install --upgrade -r requirements.txt`)
- Security audit of configured permissions

### Secret Expiry Management

⚠️ **Azure AD Client Secret expires every 24 months**

**90 days before expiry:**
1. Create new client secret in Azure AD app
2. Update .env with new secret
3. Restart scheduled tasks to pick up new config
4. Verify pipeline still works
5. After 24 hours, delete old secret

**If secret expires unexpectedly:**
- Email delivery will FAIL
- Admin will receive monitor alerts
- Follow steps above to create and deploy new secret

### Log Rotation

Logs automatically rotate daily:
- Location: `data\logs\mdinsights_YYYY-MM-DD.log`
- Retention: 30 days (configured in logging_config.py)
- Old logs auto-deleted

**Manual cleanup if needed:**
```powershell
# Delete logs older than 30 days
Get-ChildItem "C:\daily-intelligence-brief\data\logs" -Filter "mdinsights_*.log" | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} | Remove-Item
```

### Backup Retention

- Backups stored in Azure Blob Storage
- Retention: 30 days (configured in .env)
- Old backups auto-deleted by backup script
- Manual restore procedure:

```powershell
# Download backup from Azure portal
# Stop all scheduled tasks
# Replace database file
copy path\to\backup\file.db data\mdinsights.db

# Restart scheduled tasks
```

### Updating News Sources

Via admin web interface:
1. Navigate to http://localhost:8001
2. Click **Sources** in sidebar
3. Add new source / Edit / Disable existing source
4. Changes take effect on next pipeline run

### Performance Tuning

**If pipeline takes >30 minutes:**
- Reduce number of enabled sources
- Check source health (some may be timing out)
- Increase Azure OpenAI token rate limit
- Consider batching larger classification requests

**If email delivery fails:**
- Check Microsoft Graph API permissions (admin consent still granted?)
- Verify sender email mailbox still exists
- Check recipient email addresses (typos, deactivated accounts)
- Review Graph API throttling limits

---

## Appendix A: Environment Variable Reference

Complete reference of all .env variables:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| **Database** ||||
| `DATABASE_URL` | Yes | SQLite database path | `sqlite:///./data/mdinsights.db` |
| `DATA_DIR` | Yes | Data directory location | `./data` |
| **Azure OpenAI** ||||
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI endpoint URL | `https://myresource.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Yes | Azure OpenAI API key | `abc123...` |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Model deployment name | `gpt-4o` |
| `AZURE_OPENAI_API_VERSION` | Yes | API version | `2024-08-01-preview` |
| **Microsoft Graph** ||||
| `MICROSOFT_TENANT_ID` | Yes | Azure AD tenant ID | `12345678-1234-...` |
| `MICROSOFT_CLIENT_ID` | Yes | App registration client ID | `87654321-4321-...` |
| `MICROSOFT_CLIENT_SECRET` | Yes | Client secret value | `xK8Q~...` |
| `SENDER_EMAIL` | Yes | Email sender address | `intelligence@marsh.com` |
| **Apify** ||||
| `APIFY_TOKEN` | Yes | Apify API token | `apify_api_...` |
| **Azure Storage** ||||
| `AZURE_STORAGE_CONNECTION_STRING` | Yes | Storage account connection | `DefaultEndpointsProtocol=...` |
| `AZURE_STORAGE_CONTAINER` | Yes | Backup container name | `mdinsights-backups` |
| `BACKUP_RETENTION_DAYS` | Yes | Backup retention period | `30` |
| **Email Recipients** ||||
| `REPORT_RECIPIENTS_BROKERS` | No | Brokers TO list | `user1@marsh.com,user2@marsh.com` |
| `REPORT_RECIPIENTS_BROKERS_CC` | No | Brokers CC list | `manager@marsh.com` |
| `REPORT_RECIPIENTS_BROKERS_BCC` | No | Brokers BCC list | `archive@marsh.com` |
| *(repeat for LEADERSHIP, COMPLIANCE, UNDERWRITING)* ||||
| `ADMIN_EMAIL` | Yes | Admin for failure alerts | `admin@marsh.com` |
| **Application** ||||
| `DEBUG` | No | Enable debug mode | `false` |
| `LOG_LEVEL` | No | Logging verbosity | `INFO` |
| `HOST` | No | Web server host | `0.0.0.0` |
| `PORT` | No | Web server port | `8001` |
| `COMPANY_NAME` | No | Company name in reports | `Marsh` |

---

## Appendix B: Troubleshooting Deployment Issues

### Common Issues and Solutions

#### Issue: "Azure OpenAI endpoint not configured"

**Symptoms:**
- Classification test fails
- Pipeline Step 4 fails

**Solution:**
1. Verify `AZURE_OPENAI_ENDPOINT` in .env includes trailing slash
2. Verify `AZURE_OPENAI_API_KEY` is KEY 1 or KEY 2 from Azure portal
3. Verify deployment name matches actual deployment in Azure OpenAI Studio
4. Test with: `python scripts\test_classification.py`

#### Issue: "Microsoft Graph authentication failed"

**Symptoms:**
- Email test fails with 401 Unauthorized
- Pipeline Step 6 fails

**Solutions:**

**Check client secret:**
```powershell
# Verify secret hasn't expired
# Navigate to Azure AD → App registrations → Certificates & secrets
# Check expiration date
```

**Check admin consent:**
```powershell
# Navigate to Azure AD → App registrations → API permissions
# Verify Mail.Send has green checkmark "Granted for [Org]"
# If not, click "Grant admin consent for [Org]"
```

**Check sender mailbox:**
- Verify `SENDER_EMAIL` is valid mailbox in Microsoft 365
- Try sending test email manually from that mailbox

#### Issue: "Apify actor run failed"

**Symptoms:**
- Collection test fails
- Pipeline Step 2 collects 0 articles

**Solutions:**
1. Verify Apify token valid: https://console.apify.com/account/integrations
2. Check Apify account credit balance (free tier = $5/month)
3. Check source URLs are accessible (some sites block Apify IPs)
4. Review Apify run logs in console

#### Issue: "Task Scheduler task fails immediately"

**Symptoms:**
- Task shows "Failed" in Task Scheduler
- Exit code 1 or 0xC0000142

**Solutions:**

**Check batch script path:**
```powershell
schtasks /query /tn "MDInsights Daily Pipeline" /v /fo LIST | Select-String -Pattern "Task To Run"
# Verify path is correct: C:\daily-intelligence-brief\deploy\run_mdinsights.bat
```

**Check virtual environment:**
```powershell
# Verify venv exists
Test-Path "C:\daily-intelligence-brief\venv\Scripts\python.exe"
```

**Check SYSTEM account permissions:**
```powershell
# Grant SYSTEM full control
icacls "C:\daily-intelligence-brief" /grant "SYSTEM:(OI)(CI)F" /T
```

**Run batch script manually as SYSTEM:**
```powershell
# Install PsExec from Sysinternals
# Run as SYSTEM to debug
psexec -i -s cmd.exe
cd C:\daily-intelligence-brief
deploy\run_mdinsights.bat
```

#### Issue: "Database locked" errors

**Symptoms:**
- Pipeline fails with "database is locked"
- Multiple processes accessing database

**Solutions:**
1. Stop all scheduled tasks
2. Close any open database connections
3. Restart pipeline
4. If persists, check for hung Python processes:

```powershell
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Stop-Process
```

#### Issue: "Insufficient Azure OpenAI quota"

**Symptoms:**
- Classification fails with 429 Too Many Requests
- Pipeline Step 4 timeouts

**Solutions:**
1. Navigate to Azure OpenAI resource
2. Go to Quotas
3. Increase Tokens Per Minute (TPM) limit
4. Recommended: 60K TPM minimum for production
5. Request quota increase if needed (may take 1-2 days)

#### Issue: "Emails not received"

**Symptoms:**
- Pipeline succeeds but no emails received
- No errors in logs

**Solutions:**

**Check recipient configuration:**
```powershell
python -c "from app.config import get_settings; s = get_settings(); print(s.get_email_recipients('Brokers'))"
# Should show EmailRecipients(to=['...'], cc=[], bcc=[])
```

**Check spam/junk folder:**
- Emails may be filtered
- Add `SENDER_EMAIL` to safe senders list

**Check Microsoft 365 mail flow:**
- Navigate to Exchange Admin Center
- Check message trace for sender email
- Verify delivery status

#### Issue: "Backup upload fails"

**Symptoms:**
- Backup script fails
- "Azure Blob Storage connection failed"

**Solutions:**
1. Verify `AZURE_STORAGE_CONNECTION_STRING` is correct (very long string)
2. Check storage account exists in Azure portal
3. Check network connectivity to `*.blob.core.windows.net`
4. Verify storage account isn't behind firewall/private endpoint

---

## Getting Help

**Internal Support:**
- Admin Dashboard: http://localhost:8001
- Log Files: `C:\daily-intelligence-brief\data\logs\`
- Monitor Alerts: Check ADMIN_EMAIL inbox

**External Resources:**
- Azure OpenAI Docs: https://learn.microsoft.com/azure/ai-services/openai/
- Microsoft Graph Docs: https://learn.microsoft.com/graph/
- Apify Docs: https://docs.apify.com/

**Emergency Contacts:**
- Azure AD Admin: [Insert contact]
- Azure Subscription Admin: [Insert contact]
- Platform Administrator: [Insert contact]

---

**Document Version:** 1.0
**Last Updated:** 2026-02-08
**Maintained By:** MDInsights Platform Team
