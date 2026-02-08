"""
MDInsights Pipeline Monitoring Script

Checks if today's pipeline run completed successfully.
Detects scheduler-level failures (batch crash, machine offline, Task Scheduler error).

Run by Windows Task Scheduler daily at 09:00 (3 hours after pipeline at 06:00).
Exit codes: 0 = OK, 1 = issues detected (triggers Task Scheduler alert).
"""
import asyncio
import sys
import os
from datetime import datetime, date

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Run, RunStatus
from app.services.emailer import GraphEmailService
from app.config import get_settings


def check_backup_status():
    """
    Check if database backups are recent.

    Returns:
        list[str]: Issues detected (empty if OK)
    """
    issues = []
    backup_dir = "data/backups"

    if not os.path.isdir(backup_dir):
        issues.append(f"Backup directory {backup_dir}/ does not exist")
        return issues

    # Find most recent backup file
    backup_files = [
        f for f in os.listdir(backup_dir)
        if f.startswith("mdinsights_") and f.endswith(".db")
    ]

    if not backup_files:
        issues.append("No backup files found in data/backups/")
        return issues

    # Get most recent backup
    backup_paths = [os.path.join(backup_dir, f) for f in backup_files]
    latest_backup = max(backup_paths, key=os.path.getmtime)
    backup_age_hours = (datetime.now().timestamp() - os.path.getmtime(latest_backup)) / 3600

    # Allow 36 hours (1.5 days) for timing variance
    if backup_age_hours > 36:
        issues.append(
            f"Latest backup is {backup_age_hours:.1f} hours old (expected <36h): {os.path.basename(latest_backup)}"
        )

    return issues


def check_last_run():
    """
    Check if today's pipeline run completed successfully.

    Checks four independent signals:
    1. Database Run record from today with COMPLETED status
    2. Log file exists for today
    3. Archived reports exist for today
    4. Database backup is recent (<36h old)

    Returns:
        list[str]: Issues detected (empty if OK)
    """
    settings = get_settings()
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    issues = []

    # Check 1: Database run record
    db = SessionLocal()
    try:
        latest_run = db.query(Run).order_by(Run.id.desc()).first()
        if latest_run is None:
            issues.append("No pipeline runs found in database")
        elif latest_run.started_at.date() != today:
            issues.append(
                f"Latest run is from {latest_run.started_at.date()}, not today ({today})"
            )
        elif latest_run.status != RunStatus.COMPLETED:
            issues.append(
                f"Latest run status: {latest_run.status.value} (expected: completed)"
            )
    finally:
        db.close()

    # Check 2: Log file exists
    log_dir = "data/logs"
    if os.path.isdir(log_dir):
        # Log files use format: mdinsights_YYYY-MM-DD.log
        # Date format in batch script uses %%c-%%a-%%b which is YYYY-MM-DD
        today_logs = [
            f for f in os.listdir(log_dir)
            if today_str in f and f.startswith("mdinsights_")
        ]
        if not today_logs:
            issues.append(f"No log file found for {today_str} in {log_dir}/")
    else:
        issues.append(f"Log directory {log_dir}/ does not exist")

    # Check 3: Archived reports exist
    # Check one report per role - if any are missing, flag it
    roles = ["brokers", "leadership", "compliance", "underwriting"]
    for role in roles:
        report_path = f"data/reports/{role}/{today_str}.html"
        if not os.path.isfile(report_path):
            issues.append(f"Missing report: {report_path}")
            break  # One missing report is enough to flag

    # Check 4: Backup freshness
    backup_issues = check_backup_status()
    issues.extend(backup_issues)

    return issues


async def send_alert(issues):
    """
    Send alert email listing issues.

    Args:
        issues: List of issue descriptions
    """
    settings = get_settings()
    if not settings.admin_email:
        print("No admin_email configured, cannot send alert")
        return

    email_service = GraphEmailService()
    subject = f"[MDInsights] Pipeline Monitor Alert - {date.today().strftime('%d %B %Y')}"
    issues_html = "".join(f"<li>{issue}</li>" for issue in issues)
    html_body = f"""
    <html>
    <body>
    <h2>MDInsights Pipeline Monitor Alert</h2>
    <p>The daily pipeline monitoring check detected the following issues:</p>
    <ul>{issues_html}</ul>
    <p>Please investigate. This may indicate the scheduled task failed to run,
    the batch script crashed, or the machine was offline.</p>
    <p><strong>What to check:</strong></p>
    <ul>
        <li>Task Scheduler: Open Task Scheduler and check "MDInsights Daily Pipeline" task status</li>
        <li>Logs: Check data\\logs\\ directory for today's log file</li>
        <li>Database: Query Run table for today's entries</li>
        <li>Reports: Check data\\reports\\[role]\\{date.today().strftime('%Y-%m-%d')}.html files</li>
        <li>Event Viewer: Check Windows Event Viewer for Task Scheduler errors</li>
    </ul>
    <p><small>Sent by deploy/check_last_run.py at {datetime.utcnow().strftime('%H:%M UTC')}</small></p>
    </body>
    </html>
    """
    await email_service.send_email(
        to_addresses=[settings.admin_email],
        subject=subject,
        html_body=html_body
    )


if __name__ == "__main__":
    print("MDInsights Pipeline Monitor")
    print("============================")
    print(f"Checking pipeline run for {date.today().strftime('%Y-%m-%d')}...")
    print("")

    issues = check_last_run()

    if issues:
        print(f"ALERT: {len(issues)} issue(s) detected:")
        for issue in issues:
            print(f"  - {issue}")
        print("")
        print("Sending alert email to admin...")

        asyncio.run(send_alert(issues))
        print("Alert sent.")
        sys.exit(1)
    else:
        print("OK: Pipeline ran successfully today")
        print("")
        print("Checks passed:")
        print("  ✓ Database Run record from today with COMPLETED status")
        print("  ✓ Log file exists for today")
        print("  ✓ Archived reports exist for today")
        print("  ✓ Database backup is recent (<36h old)")
        sys.exit(0)
