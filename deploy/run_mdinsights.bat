@echo off
REM MDInsights Daily Pipeline Runner
REM Executed by Windows Task Scheduler daily at 06:00
REM Logs to: data\logs\mdinsights_YYYY-MM-DD.log
REM Exit codes: 0 = success, 1 = failure
REM
REM Setup: Run deploy\setup_task.ps1 to create the scheduled task

REM Get the directory where this script is located
SET SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\.."

REM Generate timestamp for log file
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/: " %%a in ('time /t') do (set mytime=%%a%%b)
set timestamp=%mydate%_%mytime%

REM Create log directory if it doesn't exist
if not exist "data\logs" mkdir "data\logs"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run MDInsights pipeline with output to log file
echo ============================================== >> "data\logs\mdinsights_%mydate%.log"
echo MDInsights Pipeline Run: %timestamp% >> "data\logs\mdinsights_%mydate%.log"
echo ============================================== >> "data\logs\mdinsights_%mydate%.log"
python -m app.main run-pipeline >> "data\logs\mdinsights_%mydate%.log" 2>&1

REM Capture exit code and log result
set exitcode=%errorlevel%
echo Exit code: %exitcode% >> "data\logs\mdinsights_%mydate%.log"
echo. >> "data\logs\mdinsights_%mydate%.log"

REM Exit with the same code as the Python script (Task Scheduler uses this)
exit /b %exitcode%
