"""
Standalone drift check script for Task Scheduler.

Monitors classification drift and sends email alerts when detected.
Exit codes:
  0 - No drift detected (OK)
  1 - Drift detected (alert sent)
  2 - Insufficient data for analysis
"""
import sys
import os
import asyncio
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.database import SessionLocal
from app.services.drift_monitor import ClassificationDriftMonitor
from app.services.emailer import GraphEmailService


def format_distribution(dist: dict) -> str:
    """Format distribution dict as human-readable string."""
    return ", ".join([f"{k}={v:.1%}" for k, v in sorted(dist.items())])


def main() -> int:
    """
    Run drift checks and send alert if needed.

    Returns:
        Exit code: 0 (no drift), 1 (drift detected), 2 (insufficient data)
    """
    settings = get_settings()
    drift_monitor = ClassificationDriftMonitor(baseline_days=14)

    print("MDInsights Classification Drift Check")
    print("=" * 50)
    print("Baseline: 14-day window (28 days ago to 14 days ago)")
    print("Recent: last 3 days")
    print()

    # Open database session
    db = SessionLocal()
    try:
        # Run all drift checks
        results = drift_monitor.run_all_checks(db)

        # Display results
        print("Priority Distribution Drift:")
        conf = results["confidence_drift"]
        if conf.get("reason") == "insufficient_data":
            print(f"  Status: INSUFFICIENT DATA")
            print(f"  Baseline count: {conf.get('baseline_count', 0)}")
            print(f"  Recent count: {conf.get('recent_count', 0)}")
        else:
            status = "DRIFT DETECTED" if conf["drift_detected"] else "OK"
            print(f"  Status: {status} (p={conf['p_value']:.2f})")
            print(
                f"  Baseline mean: {conf['baseline_mean']:.1f} | "
                f"Recent mean: {conf['recent_mean']:.1f}"
            )
        print()

        print("Role Distribution Drift:")
        role = results["role_distribution_drift"]
        if role.get("reason") == "insufficient_data":
            print(f"  Status: INSUFFICIENT DATA")
            print(f"  Baseline total: {role.get('baseline_total', 0)}")
            print(f"  Recent total: {role.get('recent_total', 0)}")
        else:
            status = "DRIFT DETECTED" if role["drift_detected"] else "OK"
            print(f"  Status: {status} (p={role['p_value']:.2f})")
            print(f"  Baseline: {format_distribution(role['baseline_distribution'])}")
            print(f"  Recent:   {format_distribution(role['recent_distribution'])}")
        print()

        print("Category Distribution Drift:")
        cat = results["category_distribution_drift"]
        if cat.get("reason") == "insufficient_data":
            print(f"  Status: INSUFFICIENT DATA")
            print(f"  Baseline total: {cat.get('baseline_total', 0)}")
            print(f"  Recent total: {cat.get('recent_total', 0)}")
        else:
            status = "DRIFT DETECTED" if cat["drift_detected"] else "OK"
            print(f"  Status: {status} (p={cat['p_value']:.2f})")
            # Only show top 3 categories for brevity
            baseline_sorted = sorted(
                cat["baseline_distribution"].items(), key=lambda x: x[1], reverse=True
            )[:3]
            recent_sorted = sorted(
                cat["recent_distribution"].items(), key=lambda x: x[1], reverse=True
            )[:3]
            print(f"  Baseline top 3: {format_distribution(dict(baseline_sorted))}")
            print(f"  Recent top 3:   {format_distribution(dict(recent_sorted))}")
        print()

        # Determine overall status
        any_drift = results["any_drift_detected"]

        # Check if all checks returned insufficient data
        all_insufficient = (
            conf.get("reason") == "insufficient_data"
            and role.get("reason") == "insufficient_data"
            and cat.get("reason") == "insufficient_data"
        )

        if all_insufficient:
            print("Overall: INSUFFICIENT DATA for drift detection")
            print("(This is expected for new systems - wait for more classification data)")
            return 2

        drift_count = sum([
            conf.get("drift_detected", False),
            role.get("drift_detected", False),
            cat.get("drift_detected", False),
        ])

        print(f"Overall: {drift_count} drift signal(s) detected")
        print()

        # Send email alert if drift detected and admin email configured
        if any_drift:
            if settings.admin_email and settings.is_graph_configured():
                print("Sending drift alert email...")
                email_service = GraphEmailService()
                alert_html = drift_monitor.format_drift_alert_email(results)

                asyncio.run(
                    email_service.send_email(
                        to_addresses=[settings.admin_email],
                        subject=f"[MDInsights] Classification Drift Alert - {date.today().strftime('%d %B %Y')}",
                        html_body=alert_html,
                    )
                )
                print(f"Alert email sent to {settings.admin_email}")
            else:
                print("Drift detected but email not configured - skipping alert")

            return 1  # Exit code 1 for drift detected

        return 0  # Exit code 0 for no drift

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
