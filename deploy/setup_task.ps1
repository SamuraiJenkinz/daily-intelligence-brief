<#
.SYNOPSIS
    Creates Windows Task Scheduler tasks for MDInsights pipeline and web server.

.DESCRIPTION
    Registers scheduled tasks for the MDInsights system:
    - Daily pipeline (collect, classify, email)
    - Daily database backup
    - Weekly classification drift check
    - Daily pipeline monitor
    - Web server (admin UI) running as a persistent service

.PARAMETER TaskName
    Name of the scheduled task (default: "MDInsights Daily Pipeline")

.PARAMETER TriggerTime
    Time to run daily (default: "06:00")

.PARAMETER MonitorTime
    Time to run monitoring check (default: "09:00")

.PARAMETER ProjectPath
    Path to MDInsights project root (default: auto-detect from script location)

.PARAMETER WebServerPort
    Port for the admin UI web server (default: 8001)

.EXAMPLE
    .\setup_task.ps1
    Creates all scheduled tasks with default settings

.EXAMPLE
    .\setup_task.ps1 -TriggerTime "05:30"
    Creates pipeline task at 05:30 instead of default 06:00

.EXAMPLE
    .\setup_task.ps1 -TaskName "MDInsights Test" -TriggerTime "14:00"
    Creates test task with custom name running at 14:00

.EXAMPLE
    .\setup_task.ps1 -WebServerPort 9000
    Runs the admin UI web server on port 9000 instead of default 8001
#>

param(
    [string]$TaskName = "MDInsights Daily Pipeline",
    [string]$TriggerTime = "06:00",
    [string]$MonitorTime = "09:00",
    [string]$BackupTime = "07:00",
    [string]$DriftDay = "Monday",
    [string]$DriftTime = "08:00",
    [string]$ProjectPath = "",
    [int]$WebServerPort = 8001
)

# Auto-detect project path from script location
if (-not $ProjectPath) {
    $ProjectPath = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}

Write-Host "MDInsights Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project path: $ProjectPath" -ForegroundColor Yellow
Write-Host "Task name: $TaskName" -ForegroundColor Yellow
Write-Host "Pipeline time: $TriggerTime" -ForegroundColor Yellow
Write-Host "Backup time: $BackupTime" -ForegroundColor Yellow
Write-Host "Drift check: $DriftDay at $DriftTime" -ForegroundColor Yellow
Write-Host "Monitor time: $MonitorTime" -ForegroundColor Yellow
Write-Host "Web server port: $WebServerPort" -ForegroundColor Yellow
Write-Host ""

# Validate project structure
Write-Host "Validating project structure..." -ForegroundColor Gray

$BatchScript = Join-Path $ProjectPath "deploy\run_mdinsights.bat"
$VenvActivate = Join-Path $ProjectPath "venv\Scripts\activate.bat"
$AppMain = Join-Path $ProjectPath "app\main.py"
$MonitorScript = Join-Path $ProjectPath "deploy\check_last_run.py"
$BackupScript = Join-Path $ProjectPath "scripts\backup_db.py"
$DriftScript = Join-Path $ProjectPath "scripts\check_drift.py"
$PythonExe = Join-Path $ProjectPath "venv\Scripts\python.exe"

if (-not (Test-Path $BatchScript)) {
    Write-Error "Batch script not found: $BatchScript"
    Write-Host "Please ensure deploy\run_mdinsights.bat exists" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $VenvActivate)) {
    Write-Error "Virtual environment not found: $VenvActivate"
    Write-Host "Please create virtual environment: python -m venv venv" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $AppMain)) {
    Write-Error "Application not found: $AppMain"
    Write-Host "Please ensure app\main.py exists" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $MonitorScript)) {
    Write-Error "Monitor script not found: $MonitorScript"
    Write-Host "Please ensure deploy\check_last_run.py exists" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python executable not found: $PythonExe"
    Write-Host "Please install dependencies: .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $BackupScript)) {
    Write-Error "Backup script not found: $BackupScript"
    Write-Host "Please ensure scripts\backup_db.py exists" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $DriftScript)) {
    Write-Error "Drift check script not found: $DriftScript"
    Write-Host "Please ensure scripts\check_drift.py exists" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Project structure validated" -ForegroundColor Green
Write-Host ""

# Create the main pipeline task
Write-Host "Creating main pipeline task..." -ForegroundColor Gray

$Action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatchScript`"" `
    -WorkingDirectory $ProjectPath

$Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 10)

$Principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Register the pipeline task (update if exists)
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Force `
        -ErrorAction Stop | Out-Null

    Write-Host "✓ Pipeline task registered: $TaskName" -ForegroundColor Green
} catch {
    Write-Error "Failed to register pipeline task: $_"
    exit 1
}

# Create the monitoring task
Write-Host "Creating monitoring task..." -ForegroundColor Gray

$MonitorAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$PythonExe`" `"$MonitorScript`"" `
    -WorkingDirectory $ProjectPath

$MonitorTrigger = New-ScheduledTaskTrigger -Daily -At $MonitorTime

$MonitorSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

# Register the monitoring task (update if exists)
$MonitorTaskName = "$TaskName - Monitor"

try {
    Register-ScheduledTask `
        -TaskName $MonitorTaskName `
        -Action $MonitorAction `
        -Trigger $MonitorTrigger `
        -Settings $MonitorSettings `
        -Principal $Principal `
        -Force `
        -ErrorAction Stop | Out-Null

    Write-Host "✓ Monitor task registered: $MonitorTaskName" -ForegroundColor Green
} catch {
    Write-Error "Failed to register monitor task: $_"
    exit 1
}

# Create the backup task
Write-Host "Creating backup task..." -ForegroundColor Gray

$BackupAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$PythonExe`" `"$BackupScript`"" `
    -WorkingDirectory $ProjectPath

$BackupTrigger = New-ScheduledTaskTrigger -Daily -At $BackupTime

$BackupSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# Register the backup task (update if exists)
$BackupTaskName = "$TaskName - Backup"

try {
    Register-ScheduledTask `
        -TaskName $BackupTaskName `
        -Action $BackupAction `
        -Trigger $BackupTrigger `
        -Settings $BackupSettings `
        -Principal $Principal `
        -Force `
        -ErrorAction Stop | Out-Null

    Write-Host "✓ Backup task registered: $BackupTaskName" -ForegroundColor Green
} catch {
    Write-Error "Failed to register backup task: $_"
    exit 1
}

# Create the drift check task
Write-Host "Creating drift check task..." -ForegroundColor Gray

$DriftAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$PythonExe`" `"$DriftScript`"" `
    -WorkingDirectory $ProjectPath

# Convert day name to day of week for trigger
$DriftTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DriftDay -At $DriftTime

$DriftSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

# Register the drift check task (update if exists)
$DriftTaskName = "$TaskName - Drift Check"

try {
    Register-ScheduledTask `
        -TaskName $DriftTaskName `
        -Action $DriftAction `
        -Trigger $DriftTrigger `
        -Settings $DriftSettings `
        -Principal $Principal `
        -Force `
        -ErrorAction Stop | Out-Null

    Write-Host "✓ Drift check task registered: $DriftTaskName" -ForegroundColor Green
} catch {
    Write-Error "Failed to register drift check task: $_"
    exit 1
}

# Create the web server task (persistent admin UI)
Write-Host "Creating web server task..." -ForegroundColor Gray

$WebServerAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$PythonExe`" -m app.main" `
    -WorkingDirectory $ProjectPath

# Trigger at system startup
$WebServerTrigger = New-ScheduledTaskTrigger -AtStartup

# Set PORT environment variable if non-default
if ($WebServerPort -ne 8001) {
    # Write port to .env if not already there
    $EnvFile = Join-Path $ProjectPath ".env"
    if (Test-Path $EnvFile) {
        $envContent = Get-Content $EnvFile -Raw -ErrorAction SilentlyContinue
        if ($envContent -notmatch "(?m)^PORT=") {
            Add-Content -Path $EnvFile -Value "PORT=$WebServerPort"
        }
    }
}

$WebServerSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Days 9999) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Disable the execution time limit (run indefinitely)
$WebServerSettings.ExecutionTimeLimit = "PT0S"

$WebServerTaskName = "$TaskName - Web Server"

try {
    Register-ScheduledTask `
        -TaskName $WebServerTaskName `
        -Action $WebServerAction `
        -Trigger $WebServerTrigger `
        -Settings $WebServerSettings `
        -Principal $Principal `
        -Force `
        -ErrorAction Stop | Out-Null

    Write-Host "✓ Web server task registered: $WebServerTaskName" -ForegroundColor Green
} catch {
    Write-Error "Failed to register web server task: $_"
    exit 1
}

Write-Host ""
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "===============" -ForegroundColor Green
Write-Host ""
Write-Host "Pipeline Task:" -ForegroundColor Cyan
Write-Host "  Name: $TaskName" -ForegroundColor White
Write-Host "  Trigger: Daily at $TriggerTime" -ForegroundColor White
Write-Host "  Script: $BatchScript" -ForegroundColor White
Write-Host "  Logs: $ProjectPath\data\logs\mdinsights_YYYY-MM-DD.log" -ForegroundColor White
Write-Host ""
Write-Host "Backup Task:" -ForegroundColor Cyan
Write-Host "  Name: $BackupTaskName" -ForegroundColor White
Write-Host "  Trigger: Daily at $BackupTime" -ForegroundColor White
Write-Host "  Script: $BackupScript" -ForegroundColor White
Write-Host ""
Write-Host "Drift Check Task:" -ForegroundColor Cyan
Write-Host "  Name: $DriftTaskName" -ForegroundColor White
Write-Host "  Trigger: Weekly on $DriftDay at $DriftTime" -ForegroundColor White
Write-Host "  Script: $DriftScript" -ForegroundColor White
Write-Host ""
Write-Host "Monitor Task:" -ForegroundColor Cyan
Write-Host "  Name: $MonitorTaskName" -ForegroundColor White
Write-Host "  Trigger: Daily at $MonitorTime" -ForegroundColor White
Write-Host "  Script: $MonitorScript" -ForegroundColor White
Write-Host ""
Write-Host "Web Server Task:" -ForegroundColor Cyan
Write-Host "  Name: $WebServerTaskName" -ForegroundColor White
Write-Host "  Trigger: At system startup" -ForegroundColor White
Write-Host "  Port: $WebServerPort" -ForegroundColor White
Write-Host "  URL: http://localhost:$WebServerPort/admin" -ForegroundColor White
Write-Host ""
Write-Host "Testing:" -ForegroundColor Cyan
Write-Host "  Run now: schtasks /run /tn `"$TaskName`"" -ForegroundColor White
Write-Host "  Start web server: schtasks /run /tn `"$WebServerTaskName`"" -ForegroundColor White
Write-Host "  Stop web server: schtasks /end /tn `"$WebServerTaskName`"" -ForegroundColor White
Write-Host "  Check status: schtasks /query /tn `"$TaskName`" /v" -ForegroundColor White
Write-Host "  View logs: type `"$ProjectPath\data\logs\mdinsights_*.log`"" -ForegroundColor White
Write-Host ""
Write-Host "Task Scheduler features:" -ForegroundColor Cyan
Write-Host "  ✓ 5 tasks registered: Web Server (startup), Pipeline (06:00), Backup (07:00), Drift (Mon 08:00), Monitor (09:00)" -ForegroundColor White
Write-Host "  ✓ Runs as SYSTEM with highest privileges" -ForegroundColor White
Write-Host "  ✓ Runs whether user is logged on or not" -ForegroundColor White
Write-Host "  ✓ Starts when available (catches up if machine was off)" -ForegroundColor White
Write-Host "  ✓ Web server runs indefinitely with auto-restart on failure (1 min delay, 3 retries)" -ForegroundColor White
Write-Host "  ✓ Network required for pipeline (Apify, Azure OpenAI, Graph API)" -ForegroundColor White
Write-Host "  ✓ 2-hour pipeline limit, 30-min backup limit, 10-min drift limit" -ForegroundColor White
Write-Host "  ✓ Monitor task verifies pipeline + backup ran (alerts admin if stale)" -ForegroundColor White
Write-Host ""
