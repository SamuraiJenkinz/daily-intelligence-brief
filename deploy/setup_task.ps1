<#
.SYNOPSIS
    Creates Windows Task Scheduler task for MDInsights daily pipeline.

.DESCRIPTION
    Registers a scheduled task that runs the MDInsights pipeline daily at 06:00.
    Also registers a secondary monitoring task that runs at 09:00 to verify
    the pipeline completed successfully (detects scheduler-level failures).

.PARAMETER TaskName
    Name of the scheduled task (default: "MDInsights Daily Pipeline")

.PARAMETER TriggerTime
    Time to run daily (default: "06:00")

.PARAMETER MonitorTime
    Time to run monitoring check (default: "09:00")

.PARAMETER ProjectPath
    Path to MDInsights project root (default: auto-detect from script location)

.EXAMPLE
    .\setup_task.ps1
    Creates scheduled tasks with default settings (06:00 pipeline, 09:00 monitor)

.EXAMPLE
    .\setup_task.ps1 -TriggerTime "05:30"
    Creates pipeline task at 05:30 instead of default 06:00

.EXAMPLE
    .\setup_task.ps1 -TaskName "MDInsights Test" -TriggerTime "14:00"
    Creates test task with custom name running at 14:00
#>

param(
    [string]$TaskName = "MDInsights Daily Pipeline",
    [string]$TriggerTime = "06:00",
    [string]$MonitorTime = "09:00",
    [string]$ProjectPath = ""
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
Write-Host "Monitor time: $MonitorTime" -ForegroundColor Yellow
Write-Host ""

# Validate project structure
Write-Host "Validating project structure..." -ForegroundColor Gray

$BatchScript = Join-Path $ProjectPath "deploy\run_mdinsights.bat"
$VenvActivate = Join-Path $ProjectPath "venv\Scripts\activate.bat"
$AppMain = Join-Path $ProjectPath "app\main.py"
$MonitorScript = Join-Path $ProjectPath "deploy\check_last_run.py"
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
Write-Host "Monitor Task:" -ForegroundColor Cyan
Write-Host "  Name: $MonitorTaskName" -ForegroundColor White
Write-Host "  Trigger: Daily at $MonitorTime" -ForegroundColor White
Write-Host "  Script: $MonitorScript" -ForegroundColor White
Write-Host ""
Write-Host "Testing:" -ForegroundColor Cyan
Write-Host "  Run now: schtasks /run /tn `"$TaskName`"" -ForegroundColor White
Write-Host "  Check status: schtasks /query /tn `"$TaskName`" /v" -ForegroundColor White
Write-Host "  View logs: type `"$ProjectPath\data\logs\mdinsights_*.log`"" -ForegroundColor White
Write-Host ""
Write-Host "Task Scheduler features:" -ForegroundColor Cyan
Write-Host "  ✓ Runs as SYSTEM with highest privileges" -ForegroundColor White
Write-Host "  ✓ Runs whether user is logged on or not" -ForegroundColor White
Write-Host "  ✓ Starts when available (catches up if machine was off)" -ForegroundColor White
Write-Host "  ✓ Network required (needs Apify, Azure OpenAI, Graph API)" -ForegroundColor White
Write-Host "  ✓ 2-hour execution limit with 2 restart attempts" -ForegroundColor White
Write-Host "  ✓ Monitor task verifies pipeline ran (alerts admin if stale)" -ForegroundColor White
Write-Host ""
