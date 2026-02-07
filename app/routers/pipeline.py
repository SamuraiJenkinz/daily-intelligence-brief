"""
Pipeline router for health monitoring and pipeline operations.

Provides endpoints for:
- Source health monitoring
- Pipeline status checks
"""
from fastapi import APIRouter
import structlog

from app.database import SessionLocal
from app.services.health_monitor import SourceHealthMonitor


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Pipeline"])


@router.get("/health/sources")
async def check_source_health():
    """
    Check health of all enabled news sources.

    Analyzes article collection patterns over the last 7 days to establish
    baselines and identifies sources with anomalous behavior (zero articles,
    below-baseline counts, or prolonged inactivity).

    Returns:
        Dict with aggregate health metrics and per-source details:
        - total_sources: Total number of enabled sources checked
        - healthy: Number of sources operating normally
        - warning: Number of sources below baseline (< 50% of average)
        - critical: Number of sources with zero articles (when baseline > 0)
        - unknown: Number of sources without historical data
        - alerts: List of sources requiring attention
        - sources: Full list of per-source health reports
    """
    health_monitor = SourceHealthMonitor()
    db = SessionLocal()

    try:
        results = health_monitor.check_all_sources(db)
        alerts = [r for r in results if r.get("alert")]

        return {
            "total_sources": len(results),
            "healthy": len([r for r in results if r["status"] == "healthy"]),
            "warning": len([r for r in results if r["status"] == "warning"]),
            "critical": len([r for r in results if r["status"] == "critical"]),
            "unknown": len([r for r in results if r["status"] == "unknown"]),
            "alerts": alerts,
            "sources": results
        }
    finally:
        db.close()
