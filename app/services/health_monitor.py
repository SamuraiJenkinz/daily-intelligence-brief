"""
Source health monitoring service for MDInsights.

Monitors source health by tracking article collection patterns and detecting anomalies
such as zero articles, below-baseline counts, or prolonged inactivity.
"""
from datetime import datetime, timedelta
from typing import Dict, List
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
                "total_runs": 0
            }

        # Calculate baseline metrics
        counts = [count.article_count for count in run_counts]
        baseline_avg = sum(counts) / len(counts)
        baseline_min = min(counts)
        latest_count = counts[-1]  # Most recent run
        total_runs = len(counts)

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
                reason=reason
            )
        elif latest_count < baseline_avg * 0.5:
            # Warning: Less than 50% of baseline
            status = "warning"
            reason = "below_baseline"
            alert = True
            self.logger.warning(
                "source_health_warning",
                source_name=source.name,
                latest_count=latest_count,
                baseline_avg=baseline_avg,
                threshold=baseline_avg * 0.5,
                reason=reason
            )
        else:
            # Healthy: At or above 50% of baseline
            status = "healthy"
            reason = None
            alert = False
            self.logger.info(
                "source_health_healthy",
                source_name=source.name,
                latest_count=latest_count,
                baseline_avg=baseline_avg
            )

        return {
            "source_name": source.name,
            "status": status,
            "reason": reason,
            "alert": alert,
            "latest_count": latest_count,
            "baseline_avg": baseline_avg,
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
