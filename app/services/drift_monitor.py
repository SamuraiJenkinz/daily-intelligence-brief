"""
Classification drift monitoring service for MDInsights.

Detects changes in AI classification patterns over time using statistical tests:
- Kolmogorov-Smirnov test for priority distribution drift (proxy for confidence)
- Chi-square test for role distribution drift
- Chi-square test for category distribution drift

Compares recent outputs (last 3 days) against a baseline period (14 days ago).
"""
import json
from datetime import datetime, timedelta
from typing import Any

import structlog
from scipy.stats import ks_2samp, chisquare
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import NewsArticle

logger = structlog.get_logger(__name__)


class ClassificationDriftMonitor:
    """
    Monitor for detecting drift in AI classification behavior.

    Uses statistical tests to compare recent classification outputs
    against a baseline period, alerting when significant changes occur.
    """

    # Priority to numeric mapping (proxy for confidence)
    PRIORITY_SCORES = {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Monitor": 1,
    }

    # All possible categories
    CATEGORIES = [
        "M&A",
        "Regulatory",
        "Loss Event",
        "Financial Results",
        "Market Trends",
        "Product Launch",
        "Executive Change",
        "Other",
    ]

    # All possible roles
    ROLES = ["Brokers", "Leadership", "Compliance", "Underwriting"]

    def __init__(self, baseline_days: int = 14):
        """
        Initialize drift monitor.

        Args:
            baseline_days: Number of days in baseline period (default 14)
                          Baseline window: (baseline_days*2) to (baseline_days) days ago
                          Recent window: last 3 days
        """
        self.baseline_days = baseline_days
        self.log = logger.bind(service="drift_monitor")

    def check_confidence_drift(
        self, db: Session, threshold: float = 0.05
    ) -> dict[str, Any]:
        """
        Check for drift in priority distribution (confidence proxy).

        Since Azure OpenAI structured outputs don't return explicit confidence scores,
        we use priority distribution as a proxy. Significant shifts indicate
        classification behavior changes.

        Args:
            db: Database session
            threshold: P-value threshold for drift detection (default 0.05)

        Returns:
            Dict with drift_detected, p_value, statistics, and counts
        """
        # Define time windows
        now = datetime.utcnow()
        baseline_end = now - timedelta(days=self.baseline_days)
        baseline_start = now - timedelta(days=self.baseline_days * 2)
        recent_start = now - timedelta(days=3)

        # Query baseline period articles
        baseline_articles = (
            db.query(NewsArticle)
            .filter(NewsArticle.created_at >= baseline_start)
            .filter(NewsArticle.created_at < baseline_end)
            .filter(NewsArticle.priority.isnot(None))
            .all()
        )

        # Query recent period articles
        recent_articles = (
            db.query(NewsArticle)
            .filter(NewsArticle.created_at >= recent_start)
            .filter(NewsArticle.priority.isnot(None))
            .all()
        )

        # Convert priorities to numeric scores
        baseline_scores = [
            self.PRIORITY_SCORES.get(a.priority, 2) for a in baseline_articles
        ]
        recent_scores = [
            self.PRIORITY_SCORES.get(a.priority, 2) for a in recent_articles
        ]

        # Check for insufficient data
        if len(baseline_scores) < 30 or len(recent_scores) < 10:
            result = {
                "drift_detected": False,
                "reason": "insufficient_data",
                "baseline_count": len(baseline_scores),
                "recent_count": len(recent_scores),
                "threshold": threshold,
            }
            self.log.info(
                "confidence_drift_check_skipped",
                reason="insufficient_data",
                baseline_count=len(baseline_scores),
                recent_count=len(recent_scores),
            )
            return result

        # Perform Kolmogorov-Smirnov test
        ks_statistic, p_value = ks_2samp(baseline_scores, recent_scores)

        # Calculate statistics
        import statistics

        baseline_mean = statistics.mean(baseline_scores)
        baseline_std = statistics.stdev(baseline_scores) if len(baseline_scores) > 1 else 0
        recent_mean = statistics.mean(recent_scores)
        recent_std = statistics.stdev(recent_scores) if len(recent_scores) > 1 else 0

        drift_detected = p_value < threshold

        result = {
            "drift_detected": drift_detected,
            "p_value": p_value,
            "ks_statistic": ks_statistic,
            "baseline_mean": baseline_mean,
            "baseline_std": baseline_std,
            "recent_mean": recent_mean,
            "recent_std": recent_std,
            "baseline_count": len(baseline_scores),
            "recent_count": len(recent_scores),
            "threshold": threshold,
        }

        if drift_detected:
            self.log.warning(
                "confidence_drift_detected",
                p_value=p_value,
                ks_statistic=ks_statistic,
                baseline_mean=baseline_mean,
                recent_mean=recent_mean,
            )
        else:
            self.log.info(
                "confidence_drift_check_passed",
                p_value=p_value,
                baseline_mean=baseline_mean,
                recent_mean=recent_mean,
            )

        return result

    def check_role_distribution_drift(
        self, db: Session, threshold: float = 0.05
    ) -> dict[str, Any]:
        """
        Check for drift in role assignment distribution.

        Args:
            db: Database session
            threshold: P-value threshold for drift detection (default 0.05)

        Returns:
            Dict with drift_detected, p_value, chi2_statistic, and distributions
        """
        # Define time windows
        now = datetime.utcnow()
        baseline_end = now - timedelta(days=self.baseline_days)
        baseline_start = now - timedelta(days=self.baseline_days * 2)
        recent_start = now - timedelta(days=3)

        # Query baseline period articles
        baseline_articles = (
            db.query(NewsArticle)
            .filter(NewsArticle.created_at >= baseline_start)
            .filter(NewsArticle.created_at < baseline_end)
            .filter(NewsArticle.roles.isnot(None))
            .all()
        )

        # Query recent period articles
        recent_articles = (
            db.query(NewsArticle)
            .filter(NewsArticle.created_at >= recent_start)
            .filter(NewsArticle.roles.isnot(None))
            .all()
        )

        # Count role frequencies
        baseline_counts = {role: 0 for role in self.ROLES}
        recent_counts = {role: 0 for role in self.ROLES}

        for article in baseline_articles:
            try:
                roles = json.loads(article.roles)
                for role in roles:
                    if role in baseline_counts:
                        baseline_counts[role] += 1
            except (json.JSONDecodeError, TypeError):
                continue

        for article in recent_articles:
            try:
                roles = json.loads(article.roles)
                for role in roles:
                    if role in recent_counts:
                        recent_counts[role] += 1
            except (json.JSONDecodeError, TypeError):
                continue

        # Check for insufficient data
        baseline_total = sum(baseline_counts.values())
        recent_total = sum(recent_counts.values())

        if baseline_total < 30 or recent_total < 10:
            result = {
                "drift_detected": False,
                "reason": "insufficient_data",
                "baseline_total": baseline_total,
                "recent_total": recent_total,
                "threshold": threshold,
            }
            self.log.info(
                "role_drift_check_skipped",
                reason="insufficient_data",
                baseline_total=baseline_total,
                recent_total=recent_total,
            )
            return result

        # Calculate distributions (proportions)
        baseline_distribution = {
            role: count / baseline_total if baseline_total > 0 else 0
            for role, count in baseline_counts.items()
        }
        recent_distribution = {
            role: count / recent_total if recent_total > 0 else 0
            for role, count in recent_counts.items()
        }

        # Compute expected frequencies for recent data based on baseline distribution
        expected_recent = [
            max(baseline_distribution[role] * recent_total, 0.1) for role in self.ROLES
        ]
        observed_recent = [recent_counts[role] for role in self.ROLES]

        # Perform chi-square test
        chi2_statistic, p_value = chisquare(observed_recent, expected_recent)

        drift_detected = p_value < threshold

        result = {
            "drift_detected": drift_detected,
            "p_value": p_value,
            "chi2_statistic": chi2_statistic,
            "baseline_distribution": baseline_distribution,
            "recent_distribution": recent_distribution,
            "baseline_total": baseline_total,
            "recent_total": recent_total,
            "threshold": threshold,
        }

        if drift_detected:
            self.log.warning(
                "role_distribution_drift_detected",
                p_value=p_value,
                chi2_statistic=chi2_statistic,
                baseline_distribution=baseline_distribution,
                recent_distribution=recent_distribution,
            )
        else:
            self.log.info(
                "role_distribution_drift_check_passed",
                p_value=p_value,
                baseline_distribution=baseline_distribution,
                recent_distribution=recent_distribution,
            )

        return result

    def check_category_distribution_drift(
        self, db: Session, threshold: float = 0.05
    ) -> dict[str, Any]:
        """
        Check for drift in category assignment distribution.

        Detects prompt drift where categories become skewed.

        Args:
            db: Database session
            threshold: P-value threshold for drift detection (default 0.05)

        Returns:
            Dict with drift_detected, p_value, chi2_statistic, and distributions
        """
        # Define time windows
        now = datetime.utcnow()
        baseline_end = now - timedelta(days=self.baseline_days)
        baseline_start = now - timedelta(days=self.baseline_days * 2)
        recent_start = now - timedelta(days=3)

        # Query baseline period articles
        baseline_articles = (
            db.query(NewsArticle)
            .filter(NewsArticle.created_at >= baseline_start)
            .filter(NewsArticle.created_at < baseline_end)
            .filter(NewsArticle.category.isnot(None))
            .all()
        )

        # Query recent period articles
        recent_articles = (
            db.query(NewsArticle)
            .filter(NewsArticle.created_at >= recent_start)
            .filter(NewsArticle.category.isnot(None))
            .all()
        )

        # Count category frequencies
        baseline_counts = {cat: 0 for cat in self.CATEGORIES}
        recent_counts = {cat: 0 for cat in self.CATEGORIES}

        for article in baseline_articles:
            if article.category in baseline_counts:
                baseline_counts[article.category] += 1

        for article in recent_articles:
            if article.category in recent_counts:
                recent_counts[article.category] += 1

        # Check for insufficient data
        baseline_total = sum(baseline_counts.values())
        recent_total = sum(recent_counts.values())

        if baseline_total < 30 or recent_total < 10:
            result = {
                "drift_detected": False,
                "reason": "insufficient_data",
                "baseline_total": baseline_total,
                "recent_total": recent_total,
                "threshold": threshold,
            }
            self.log.info(
                "category_drift_check_skipped",
                reason="insufficient_data",
                baseline_total=baseline_total,
                recent_total=recent_total,
            )
            return result

        # Calculate distributions (proportions)
        baseline_distribution = {
            cat: count / baseline_total if baseline_total > 0 else 0
            for cat, count in baseline_counts.items()
        }
        recent_distribution = {
            cat: count / recent_total if recent_total > 0 else 0
            for cat, count in recent_counts.items()
        }

        # Compute expected frequencies for recent data based on baseline distribution
        expected_recent = [
            max(baseline_distribution[cat] * recent_total, 0.1) for cat in self.CATEGORIES
        ]
        observed_recent = [recent_counts[cat] for cat in self.CATEGORIES]

        # Perform chi-square test
        chi2_statistic, p_value = chisquare(observed_recent, expected_recent)

        drift_detected = p_value < threshold

        result = {
            "drift_detected": drift_detected,
            "p_value": p_value,
            "chi2_statistic": chi2_statistic,
            "baseline_distribution": baseline_distribution,
            "recent_distribution": recent_distribution,
            "baseline_total": baseline_total,
            "recent_total": recent_total,
            "threshold": threshold,
        }

        if drift_detected:
            self.log.warning(
                "category_distribution_drift_detected",
                p_value=p_value,
                chi2_statistic=chi2_statistic,
                baseline_distribution=baseline_distribution,
                recent_distribution=recent_distribution,
            )
        else:
            self.log.info(
                "category_distribution_drift_check_passed",
                p_value=p_value,
                baseline_distribution=baseline_distribution,
                recent_distribution=recent_distribution,
            )

        return result

    def run_all_checks(self, db: Session) -> dict[str, Any]:
        """
        Run all drift checks and return combined results.

        Args:
            db: Database session

        Returns:
            Dict with timestamp, any_drift_detected, and all check results
        """
        confidence_drift = self.check_confidence_drift(db)
        role_drift = self.check_role_distribution_drift(db)
        category_drift = self.check_category_distribution_drift(db)

        any_drift = (
            confidence_drift.get("drift_detected", False)
            or role_drift.get("drift_detected", False)
            or category_drift.get("drift_detected", False)
        )

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "any_drift_detected": any_drift,
            "confidence_drift": confidence_drift,
            "role_distribution_drift": role_drift,
            "category_distribution_drift": category_drift,
        }

        self.log.info(
            "drift_check_completed",
            any_drift_detected=any_drift,
            confidence_drift=confidence_drift.get("drift_detected", False),
            role_drift=role_drift.get("drift_detected", False),
            category_drift=category_drift.get("drift_detected", False),
        )

        return results

    def format_drift_alert_email(self, results: dict[str, Any]) -> str:
        """
        Format drift check results as HTML email.

        Args:
            results: Output from run_all_checks()

        Returns:
            HTML string for email body
        """
        sections = []

        # Header
        header = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                h1 { color: #d9534f; }
                h2 { color: #5bc0de; margin-top: 20px; }
                .section { margin-bottom: 30px; padding: 15px; background: #f9f9f9; border-left: 4px solid #d9534f; }
                .stats { margin: 10px 0; }
                .stats table { border-collapse: collapse; width: 100%; }
                .stats th, .stats td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                .stats th { background: #f2f2f2; }
                .recommendation { background: #fff3cd; padding: 10px; margin-top: 10px; border-left: 4px solid #ffc107; }
                .info { background: #d9edf7; padding: 10px; margin-top: 10px; border-left: 4px solid #5bc0de; }
            </style>
        </head>
        <body>
            <h1>🚨 MDInsights Classification Drift Alert</h1>
            <p><strong>Timestamp:</strong> {timestamp}</p>
            <p>The AI classification system has detected statistically significant changes in behavior patterns.</p>
        """.format(timestamp=results["timestamp"])

        sections.append(header)

        # Confidence drift section
        conf = results["confidence_drift"]
        if conf.get("drift_detected"):
            sections.append(self._format_confidence_section(conf))
        elif conf.get("reason") == "insufficient_data":
            sections.append(
                """
                <div class="info">
                    <strong>Priority Distribution Check:</strong> Insufficient data
                    (baseline: {baseline}, recent: {recent})
                </div>
                """.format(
                    baseline=conf.get("baseline_count", 0),
                    recent=conf.get("recent_count", 0),
                )
            )

        # Role drift section
        role = results["role_distribution_drift"]
        if role.get("drift_detected"):
            sections.append(self._format_role_section(role))
        elif role.get("reason") == "insufficient_data":
            sections.append(
                """
                <div class="info">
                    <strong>Role Distribution Check:</strong> Insufficient data
                    (baseline: {baseline}, recent: {recent})
                </div>
                """.format(
                    baseline=role.get("baseline_total", 0),
                    recent=role.get("recent_total", 0),
                )
            )

        # Category drift section
        cat = results["category_distribution_drift"]
        if cat.get("drift_detected"):
            sections.append(self._format_category_section(cat))
        elif cat.get("reason") == "insufficient_data":
            sections.append(
                """
                <div class="info">
                    <strong>Category Distribution Check:</strong> Insufficient data
                    (baseline: {baseline}, recent: {recent})
                </div>
                """.format(
                    baseline=cat.get("baseline_total", 0),
                    recent=cat.get("recent_total", 0),
                )
            )

        # Footer
        footer = """
            <hr style="margin-top: 30px;">
            <p style="color: #666; font-size: 0.9em;">
                This alert was generated by the MDInsights drift monitoring system.
                Drift detection uses statistical tests (KS test for priority, chi-square for distributions)
                with p-value threshold of 0.05.
            </p>
        </body>
        </html>
        """
        sections.append(footer)

        return "".join(sections)

    def _format_confidence_section(self, conf: dict[str, Any]) -> str:
        """Format priority distribution drift section."""
        return """
        <div class="section">
            <h2>Priority Distribution Drift Detected</h2>
            <p><strong>P-value:</strong> {p_value:.4f} (threshold: {threshold})</p>
            <p><strong>KS Statistic:</strong> {ks_statistic:.4f}</p>
            <div class="stats">
                <table>
                    <tr>
                        <th>Period</th>
                        <th>Mean Priority</th>
                        <th>Std Dev</th>
                        <th>Sample Size</th>
                    </tr>
                    <tr>
                        <td>Baseline</td>
                        <td>{baseline_mean:.2f}</td>
                        <td>{baseline_std:.2f}</td>
                        <td>{baseline_count}</td>
                    </tr>
                    <tr>
                        <td>Recent</td>
                        <td>{recent_mean:.2f}</td>
                        <td>{recent_std:.2f}</td>
                        <td>{recent_count}</td>
                    </tr>
                </table>
            </div>
            <div class="recommendation">
                <strong>Recommendation:</strong> Review recent articles to determine if priority assignments
                have legitimately shifted (e.g., due to major market events) or if the classification
                model is behaving inconsistently. Consider reviewing the classification prompt.
            </div>
        </div>
        """.format(**conf)

    def _format_role_section(self, role: dict[str, Any]) -> str:
        """Format role distribution drift section."""
        baseline = role["baseline_distribution"]
        recent = role["recent_distribution"]

        rows = []
        for r in self.ROLES:
            rows.append(
                """
                <tr>
                    <td>{role}</td>
                    <td>{baseline:.1%}</td>
                    <td>{recent:.1%}</td>
                    <td>{change:+.1%}</td>
                </tr>
                """.format(
                    role=r,
                    baseline=baseline.get(r, 0),
                    recent=recent.get(r, 0),
                    change=recent.get(r, 0) - baseline.get(r, 0),
                )
            )

        return """
        <div class="section">
            <h2>Role Distribution Drift Detected</h2>
            <p><strong>P-value:</strong> {p_value:.4f} (threshold: {threshold})</p>
            <p><strong>Chi-square Statistic:</strong> {chi2_statistic:.4f}</p>
            <div class="stats">
                <table>
                    <tr>
                        <th>Role</th>
                        <th>Baseline %</th>
                        <th>Recent %</th>
                        <th>Change</th>
                    </tr>
                    {rows}
                </table>
            </div>
            <div class="recommendation">
                <strong>Recommendation:</strong> Significant shift in role assignments detected.
                Review recent articles to determine if the news landscape has genuinely changed
                or if the role classification is drifting. May indicate need to retrain or adjust
                the classification prompt.
            </div>
        </div>
        """.format(
            p_value=role["p_value"],
            threshold=role["threshold"],
            chi2_statistic=role["chi2_statistic"],
            rows="".join(rows),
        )

    def _format_category_section(self, cat: dict[str, Any]) -> str:
        """Format category distribution drift section."""
        baseline = cat["baseline_distribution"]
        recent = cat["recent_distribution"]

        rows = []
        for c in self.CATEGORIES:
            rows.append(
                """
                <tr>
                    <td>{category}</td>
                    <td>{baseline:.1%}</td>
                    <td>{recent:.1%}</td>
                    <td>{change:+.1%}</td>
                </tr>
                """.format(
                    category=c,
                    baseline=baseline.get(c, 0),
                    recent=recent.get(c, 0),
                    change=recent.get(c, 0) - baseline.get(c, 0),
                )
            )

        return """
        <div class="section">
            <h2>Category Distribution Drift Detected</h2>
            <p><strong>P-value:</strong> {p_value:.4f} (threshold: {threshold})</p>
            <p><strong>Chi-square Statistic:</strong> {chi2_statistic:.4f}</p>
            <div class="stats">
                <table>
                    <tr>
                        <th>Category</th>
                        <th>Baseline %</th>
                        <th>Recent %</th>
                        <th>Change</th>
                    </tr>
                    {rows}
                </table>
            </div>
            <div class="recommendation">
                <strong>Recommendation:</strong> Category distribution has shifted significantly.
                Review to determine if this reflects real changes in news content or indicates
                prompt drift. May need to adjust category definitions or classification guidance.
            </div>
        </div>
        """.format(
            p_value=cat["p_value"],
            threshold=cat["threshold"],
            chi2_statistic=cat["chi2_statistic"],
            rows="".join(rows),
        )
