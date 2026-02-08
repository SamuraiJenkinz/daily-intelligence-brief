"""
Source health monitoring service for MDInsights.

Monitors source health by tracking article collection patterns and detecting anomalies
such as zero articles, below-baseline counts, or prolonged inactivity.
"""
from datetime import datetime, timedelta
from typing import Dict, List
import statistics
from sqlalchemy import func
from sqlalchemy.orm import Session
import structlog

from app.models import Source, NewsArticle, Run, RunStatus


class SourceHealthMonitor:
    """Monitor source health by tracking article collection patterns."""

    def __init__(self, lookback_days: int = 7):
        """
        Initialize health monitor.

        Args:
            lookback_days: Number of days to analyze for baseline calculation (default: 7)
        """
        self.lookback_days = lookback_days
        self.logger = structlog.get_logger().bind(service="health_monitor")

    def check_source_health(self, db: Session, source: Source) -> Dict:
        """
        Check health of a single source.

        Analyzes article collection patterns over the lookback period to establish
        a baseline and compares the most recent run against that baseline.

        Args:
            db: Database session
            source: Source to check

        Returns:
            Dict with keys:
                - source_name: str
                - status: "healthy" | "warning" | "critical" | "unknown"
                - alert: bool (True if action needed)
                - reason: str (if not healthy)
                - latest_count: int (article count from latest run)
                - baseline_avg: float (7-day moving average)
                - baseline_std: float (standard deviation of baseline)
                - threshold_value: float (calculated threshold for warning)
                - consecutive_low_runs: int (number of consecutive below-baseline runs)
                - total_runs: int (number of runs in lookback period)
        """
        cutoff = datetime.utcnow() - timedelta(days=self.lookback_days)

        # Query article counts per completed run for this source
        run_counts = (
            db.query(
                Run.id,
                Run.completed_at,
                func.count(NewsArticle.id).label('article_count')
            )
            .join(NewsArticle, NewsArticle.run_id == Run.id)
            .filter(
                NewsArticle.source_name == source.name,
                Run.completed_at >= cutoff,
                Run.status == RunStatus.COMPLETED
            )
            .group_by(Run.id, Run.completed_at)
            .order_by(Run.completed_at)
            .all()
        )

        # If no completed runs in lookback period, return unknown status
        if not run_counts:
            self.logger.info(
                "source_health_check_no_history",
                source_name=source.name,
                lookback_days=self.lookback_days
            )
            return {
                "source_name": source.name,
                "status": "unknown",
                "reason": "no_history",
                "alert": False,
                "latest_count": 0,
                "baseline_avg": 0.0,
                "baseline_std": 0.0,
                "threshold_value": 0.0,
                "consecutive_low_runs": 0,
                "total_runs": 0
            }

        # Calculate baseline metrics
        counts = [count.article_count for count in run_counts]
        baseline_avg = sum(counts) / len(counts)
        baseline_std = statistics.stdev(counts) if len(counts) > 1 else 0.0
        latest_count = counts[-1]  # Most recent run
        total_runs = len(counts)

        # Calculate threshold using standard deviation (more lenient of two approaches)
        # Warning threshold: baseline_avg - 2*std_dev OR 30% of baseline (whichever is more lenient)
        std_threshold = baseline_avg - (2 * baseline_std)
        pct_threshold = baseline_avg * 0.3
        threshold_value = max(std_threshold, pct_threshold)

        # Count consecutive low runs (below threshold)
        consecutive_low_runs = 0
        for count in reversed(counts):
            if count < threshold_value:
                consecutive_low_runs += 1
            else:
                break

        # Determine health status based on latest run vs baseline
        if latest_count == 0 and baseline_avg > 0:
            # Critical: Zero articles when we normally get some
            status = "critical"
            reason = "zero_articles"
            alert = True
            self.logger.warning(
                "source_health_critical",
                source_name=source.name,
                latest_count=latest_count,
                baseline_avg=baseline_avg,
                baseline_std=baseline_std,
                reason=reason
            )
        elif latest_count < threshold_value and latest_count > 0:
            # Warning: Below statistical threshold
            status = "warning"
            reason = "below_baseline"
            alert = True
            self.logger.warning(
                "source_health_warning",
                source_name=source.name,
                latest_count=latest_count,
                baseline_avg=baseline_avg,
                baseline_std=baseline_std,
                threshold_value=threshold_value,
                consecutive_low_runs=consecutive_low_runs,
                reason=reason
            )
        else:
            # Healthy: At or above threshold
            status = "healthy"
            reason = None
            alert = False
            self.logger.info(
                "source_health_healthy",
                source_name=source.name,
                latest_count=latest_count,
                baseline_avg=baseline_avg,
                baseline_std=baseline_std
            )

        return {
            "source_name": source.name,
            "status": status,
            "reason": reason,
            "alert": alert,
            "latest_count": latest_count,
            "baseline_avg": baseline_avg,
            "baseline_std": baseline_std,
            "threshold_value": threshold_value,
            "consecutive_low_runs": consecutive_low_runs,
            "total_runs": total_runs
        }

    def check_all_sources(self, db: Session) -> List[Dict]:
        """
        Check health of all enabled sources.

        Args:
            db: Database session

        Returns:
            List of health status dicts (one per enabled source)
        """
        # Query all enabled sources
        sources = db.query(Source).filter(Source.enabled == True).all()

        if not sources:
            self.logger.warning("check_all_sources_no_enabled_sources")
            return []

        # Check health for each source
        results = []
        for source in sources:
            health = self.check_source_health(db, source)
            results.append(health)

        # Log summary
        total_sources = len(results)
        alerts = [r for r in results if r["alert"]]
        alert_count = len(alerts)

        self.logger.info(
            "check_all_sources_complete",
            total_sources=total_sources,
            alerts_found=alert_count,
            critical=[r["source_name"] for r in alerts if r["status"] == "critical"],
            warning=[r["source_name"] for r in alerts if r["status"] == "warning"]
        )

        return results

    def get_alerts(self, db: Session) -> List[Dict]:
        """
        Get only sources with active alerts (critical or warning status).

        Convenience method for filtering sources that need attention.

        Args:
            db: Database session

        Returns:
            List of health status dicts with alert=True
        """
        all_health = self.check_all_sources(db)
        alerts = [health for health in all_health if health["alert"]]

        self.logger.info(
            "get_alerts_filtered",
            total_checked=len(all_health),
            alerts_found=len(alerts)
        )

        return alerts

    def format_alert_email(self, alerts: List[Dict]) -> str:
        """
        Format health alerts as HTML email for admin notification.

        Args:
            alerts: List of alert dicts from get_alerts()

        Returns:
            HTML string suitable for email delivery
        """
        now = datetime.utcnow()
        date_str = now.strftime("%d %B %Y")

        # Count critical vs warning
        critical_count = sum(1 for a in alerts if a["status"] == "critical")
        warning_count = sum(1 for a in alerts if a["status"] == "warning")

        # Build table rows
        rows = []
        for alert in alerts:
            # Color-code by status
            bg_color = "#dc3545" if alert["status"] == "critical" else "#fd7e14"
            text_color = "#ffffff"

            # Format reason
            reason_text = alert["reason"].replace("_", " ").title()

            # Add consecutive low runs info if > 1
            if alert.get("consecutive_low_runs", 0) > 1:
                reason_text += f" ({alert['consecutive_low_runs']} runs)"

            row = f"""
            <tr style="background-color: {bg_color}; color: {text_color};">
                <td style="padding: 10px; border: 1px solid #ddd;">{alert["source_name"]}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{alert["status"].upper()}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{alert["latest_count"]}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{alert["baseline_avg"]:.1f}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{reason_text}</td>
            </tr>
            """
            rows.append(row)

        rows_html = "\n".join(rows)

        # Build complete HTML email
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th {{ background-color: #343a40; color: white; padding: 12px; text-align: left; border: 1px solid #ddd; }}
                td {{ padding: 10px; border: 1px solid #ddd; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ color: #6c757d; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <h2>Source Health Alert - {date_str}</h2>

            <div class="summary">
                <p><strong>{len(alerts)} source(s) require attention</strong></p>
                <ul>
                    <li><strong>Critical:</strong> {critical_count} (zero articles)</li>
                    <li><strong>Warning:</strong> {warning_count} (below baseline)</li>
                </ul>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Source Name</th>
                        <th>Status</th>
                        <th>Latest Count</th>
                        <th>Baseline Avg</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <p class="footer">
                View detailed source health and manage sources at: <a href="http://localhost:8001/admin">MDInsights Admin Dashboard</a><br>
                This is an automated alert from MDInsights Source Health Monitor. Check logs for full details.
            </p>
        </body>
        </html>
        """

        return html

    def format_alert_summary(self, alerts: List[Dict]) -> str:
        """
        Format health alerts as plain text summary for log output.

        Args:
            alerts: List of alert dicts from get_alerts()

        Returns:
            Plain text one-liner summary
        """
        if not alerts:
            return "No health alerts"

        alert_parts = []
        for alert in alerts:
            status = alert["status"]
            source = alert["source_name"]
            reason = alert["reason"]
            alert_parts.append(f"{source} ({status}: {reason})")

        return f"{len(alerts)} alerts: {', '.join(alert_parts)}"
