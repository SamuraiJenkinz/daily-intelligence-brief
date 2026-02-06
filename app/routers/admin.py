"""
Admin router for manual pipeline triggering and run management.

Provides endpoints for:
- Manual pipeline execution
- Run history
- Admin UI
"""
import structlog
from typing import List, Dict
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from app.config import get_settings
from app.services.collector import ApifyCollector
from app.services.classifier import RoleClassificationService
from app.services.reporter import RoleReportService
from app.services.pipeline import PipelineOrchestrator
from app.database import SessionLocal
from app.models import Run


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Setup Jinja2 environment for admin templates
app_dir = Path(__file__).parent.parent
templates_dir = app_dir / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    autoescape=True
)


@router.get("/trigger", response_class=HTMLResponse)
def get_admin_trigger_ui():
    """
    Serve admin UI for manual pipeline triggering.

    Returns:
        HTML page with form for triggering pipeline execution
    """
    template = jinja_env.get_template('admin_trigger.html')
    html = template.render()
    return HTMLResponse(content=html)


@router.post("/trigger-pipeline", response_class=HTMLResponse)
def trigger_pipeline(role: str = Query(default="Brokers")):
    """
    Manually trigger complete pipeline execution.

    Executes collection → classification → reporting workflow and
    returns generated HTML report with custom headers.

    Args:
        role: Target role for report (Brokers, Leadership, Compliance, Underwriting)

    Returns:
        HTMLResponse with generated report

    Raises:
        HTTPException: If pipeline execution fails
    """
    settings = get_settings()

    try:
        logger.info("manual_trigger_started", role=role)

        # Validate configuration
        if not settings.is_apify_configured():
            raise HTTPException(
                status_code=500,
                detail="Apify not configured. Set APIFY_TOKEN in .env"
            )

        if not settings.is_azure_openai_configured():
            raise HTTPException(
                status_code=500,
                detail="Azure OpenAI not configured. Set credentials in .env"
            )

        # Initialize services
        collector = ApifyCollector(apify_token=settings.apify_token)
        classifier = RoleClassificationService(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version
        )
        reporter = RoleReportService()

        # Initialize pipeline orchestrator
        orchestrator = PipelineOrchestrator(
            collector=collector,
            classifier=classifier,
            reporter=reporter
        )

        # Execute pipeline
        result = orchestrator.run_full_pipeline(role=role)

        # Check if pipeline succeeded
        if result["status"] != "completed":
            error_msg = result.get("error", "Unknown error")
            logger.error("manual_trigger_failed", error=error_msg)
            raise HTTPException(
                status_code=500,
                detail=f"Pipeline execution failed: {error_msg}"
            )

        # Return HTML report with custom headers
        logger.info(
            "manual_trigger_completed",
            run_id=result["run_id"],
            articles_collected=result["articles_collected"],
            articles_classified=result["articles_classified"]
        )

        return HTMLResponse(
            content=result["html_output"],
            headers={
                "X-MDInsights-Run-ID": str(result["run_id"]),
                "X-Articles-Collected": str(result["articles_collected"]),
                "X-Articles-Classified": str(result["articles_classified"])
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("manual_trigger_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution error: {str(e)}"
        )


@router.get("/runs")
def get_recent_runs() -> List[Dict]:
    """
    Get recent pipeline runs.

    Returns:
        List of recent runs (last 10) with metadata
    """
    db = SessionLocal()

    try:
        runs = db.query(Run).order_by(Run.id.desc()).limit(10).all()

        return [
            {
                "id": run.id,
                "status": run.status.value,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "articles_collected": run.articles_collected,
                "articles_classified": run.articles_classified,
                "error_message": run.error_message
            }
            for run in runs
        ]

    finally:
        db.close()
