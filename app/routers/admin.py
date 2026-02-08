"""
Admin router for manual pipeline triggering and run management.

Provides endpoints for:
- Manual pipeline execution
- Run history
- Admin UI
- Source management
- Recipient management
"""
import structlog
import re
from typing import List, Dict, Optional
from fastapi import APIRouter, Query, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from pydantic import BaseModel, EmailStr, ValidationError, field_validator

from app.config import get_settings
from app.services.collector import ApifyCollector
from app.services.classifier import RoleClassificationService
from app.services.reporter import RoleReportService
from app.services.pipeline import PipelineOrchestrator
from app.database import SessionLocal
from app.models import Run, Source, NewsArticle
from app.models.source import SourceType
from app.schemas.admin import SourceCreate, SourceUpdate
from datetime import datetime, date
from sqlalchemy import func


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Setup Jinja2 environment for admin templates
app_dir = Path(__file__).parent.parent
templates_dir = app_dir / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    autoescape=True
)


@router.get("", response_class=HTMLResponse)
def get_admin_dashboard():
    """
    Serve admin dashboard landing page.

    Shows system status summary including:
    - Source counts (total and enabled)
    - Articles collected today
    - Last run status
    - Recent runs table

    Returns:
        HTML dashboard page with system statistics
    """
    db = SessionLocal()

    try:
        # Get source counts
        total_sources = db.query(Source).count()
        active_sources = db.query(Source).filter(Source.enabled == True).count()

        # Get articles from today
        today = date.today()
        articles_today = db.query(NewsArticle).filter(
            func.date(NewsArticle.published_at) == today
        ).count()

        # Get last run
        last_run = db.query(Run).order_by(Run.id.desc()).first()

        # Get recent runs (last 10)
        runs = db.query(Run).order_by(Run.id.desc()).limit(10).all()

        # Format data for template
        runs_data = []
        for run in runs:
            runs_data.append({
                'id': run.id,
                'status': run.status.value,
                'created_at': run.created_at.strftime('%Y-%m-%d %H:%M:%S') if run.created_at else None,
                'completed_at': run.completed_at.strftime('%Y-%m-%d %H:%M:%S') if run.completed_at else None,
                'articles_collected': run.articles_collected,
                'articles_classified': run.articles_classified,
                'error_message': run.error_message
            })

        last_run_data = None
        if last_run:
            last_run_data = {
                'status': last_run.status.value,
                'created_at': last_run.created_at.strftime('%Y-%m-%d %H:%M:%S') if last_run.created_at else None
            }

        # Render template
        template = jinja_env.get_template('admin/dashboard.html')
        html = template.render(
            active_sources=active_sources,
            total_sources=total_sources,
            articles_today=articles_today,
            today_date=today.strftime('%Y-%m-%d'),
            last_run=last_run_data,
            runs=runs_data
        )

        return HTMLResponse(content=html)

    finally:
        db.close()


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

        # Check source health after pipeline run
        health_alerts = []
        try:
            from app.services.health_monitor import SourceHealthMonitor
            health_monitor = SourceHealthMonitor()
            db_health = SessionLocal()
            try:
                alerts = health_monitor.get_alerts(db_health)
                if alerts:
                    logger.warning(
                        "source_health_alerts",
                        alert_count=len(alerts),
                        sources=[a["source_name"] for a in alerts]
                    )
                    health_alerts = alerts
            finally:
                db_health.close()
        except Exception as health_err:
            logger.warning("health_check_failed", error=str(health_err))

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
                "X-Articles-Classified": str(result["articles_classified"]),
                "X-MDInsights-Health-Alerts": str(len(health_alerts))
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


@router.get("/sources", response_class=HTMLResponse)
def get_sources(
    request: Request,
    search: Optional[str] = Query(None),
    enabled_filter: Optional[str] = Query("all")
):
    """
    Get all sources for source management page.

    Args:
        request: FastAPI request object
        search: Optional search query for filtering by name or URL
        enabled_filter: Filter by enabled status ("all", "true", "false")

    Returns:
        HTML response with source table or full page
    """
    db = SessionLocal()

    try:
        # Build query with filters
        query = db.query(Source)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Source.name.ilike(search_pattern)) |
                (Source.url.ilike(search_pattern))
            )

        if enabled_filter == "true":
            query = query.filter(Source.enabled == True)
        elif enabled_filter == "false":
            query = query.filter(Source.enabled == False)

        sources = query.order_by(Source.name).all()

        # Check if this is an HTMX partial request
        is_htmx = request.headers.get("HX-Request") == "true"

        if is_htmx:
            # Return just the table body partial
            template = jinja_env.get_template('admin/partials/source_table.html')
            html = template.render(sources=sources)
        else:
            # Return full page
            template = jinja_env.get_template('admin/sources.html')
            html = template.render(sources=sources, active_nav="sources")

        return HTMLResponse(content=html)

    finally:
        db.close()


@router.post("/sources/create", response_class=HTMLResponse)
def create_source(
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form(...),
    actor_id: Optional[str] = Form(None),
    enabled: bool = Form(True)
):
    """
    Create a new source.

    Args:
        name: Source name
        url: Source URL
        source_type: Type of source (apify or rss)
        actor_id: Optional Apify actor ID
        enabled: Whether source is enabled

    Returns:
        HTML response with updated source table
    """
    db = SessionLocal()

    try:
        # Validate input with Pydantic
        try:
            source_data = SourceCreate(
                name=name,
                url=url,
                source_type=source_type,
                actor_id=actor_id if actor_id else None,
                enabled=enabled
            )
        except ValidationError as e:
            # Return form with errors
            errors = {err["loc"][0]: err["msg"] for err in e.errors()}
            template = jinja_env.get_template('admin/partials/source_form.html')
            html = template.render(errors=errors, form_data={
                "name": name,
                "url": url,
                "source_type": source_type,
                "actor_id": actor_id,
                "enabled": enabled
            })
            return HTMLResponse(content=html, status_code=422)

        # Check for duplicate name
        existing = db.query(Source).filter(Source.name == source_data.name).first()
        if existing:
            errors = {"name": "A source with this name already exists"}
            template = jinja_env.get_template('admin/partials/source_form.html')
            html = template.render(errors=errors, form_data={
                "name": name,
                "url": url,
                "source_type": source_type,
                "actor_id": actor_id,
                "enabled": enabled
            })
            return HTMLResponse(content=html, status_code=422)

        # Create new source
        new_source = Source(
            name=source_data.name,
            url=source_data.url,
            source_type=SourceType(source_data.source_type),
            actor_id=source_data.actor_id,
            enabled=source_data.enabled
        )

        db.add(new_source)
        db.commit()
        db.refresh(new_source)

        logger.info("source_created", source_id=new_source.id, name=new_source.name)

        # Return updated table
        sources = db.query(Source).order_by(Source.name).all()
        template = jinja_env.get_template('admin/partials/source_table.html')
        html = template.render(sources=sources)

        return HTMLResponse(content=html)

    finally:
        db.close()


@router.get("/sources/{source_id}/edit", response_class=HTMLResponse)
def get_source_edit_row(source_id: int):
    """
    Get inline edit form for a source.

    Args:
        source_id: Source ID

    Returns:
        HTML response with edit row partial
    """
    db = SessionLocal()

    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        template = jinja_env.get_template('admin/partials/source_edit_row.html')
        html = template.render(source=source)

        return HTMLResponse(content=html)

    finally:
        db.close()


@router.post("/sources/{source_id}", response_class=HTMLResponse)
def update_source(
    source_id: int,
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form(...),
    actor_id: Optional[str] = Form(None),
    enabled: bool = Form(False)
):
    """
    Update an existing source.

    Args:
        source_id: Source ID
        name: Source name
        url: Source URL
        source_type: Type of source (apify or rss)
        actor_id: Optional Apify actor ID
        enabled: Whether source is enabled

    Returns:
        HTML response with updated source row
    """
    db = SessionLocal()

    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Validate input with Pydantic
        try:
            source_data = SourceUpdate(
                name=name,
                url=url,
                source_type=source_type,
                actor_id=actor_id if actor_id else None,
                enabled=enabled
            )
        except ValidationError as e:
            # Return edit row with errors
            errors = {err["loc"][0]: err["msg"] for err in e.errors()}
            template = jinja_env.get_template('admin/partials/source_edit_row.html')
            html = template.render(source=source, errors=errors)
            return HTMLResponse(content=html, status_code=422)

        # Check for duplicate name (excluding current source)
        existing = db.query(Source).filter(
            Source.name == source_data.name,
            Source.id != source_id
        ).first()
        if existing:
            errors = {"name": "A source with this name already exists"}
            template = jinja_env.get_template('admin/partials/source_edit_row.html')
            html = template.render(source=source, errors=errors)
            return HTMLResponse(content=html, status_code=422)

        # Update source
        source.name = source_data.name
        source.url = source_data.url
        source.source_type = SourceType(source_data.source_type)
        source.actor_id = source_data.actor_id
        source.enabled = source_data.enabled

        db.commit()
        db.refresh(source)

        logger.info("source_updated", source_id=source.id, name=source.name)

        # Return updated row
        template = jinja_env.get_template('admin/partials/source_row.html')
        html = template.render(source=source)

        return HTMLResponse(content=html)

    finally:
        db.close()


@router.post("/sources/{source_id}/toggle", response_class=HTMLResponse)
def toggle_source(source_id: int):
    """
    Toggle source enabled status.

    Args:
        source_id: Source ID

    Returns:
        HTML response with updated source row
    """
    db = SessionLocal()

    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Toggle enabled status
        source.enabled = not source.enabled
        db.commit()
        db.refresh(source)

        logger.info("source_toggled", source_id=source.id, enabled=source.enabled)

        # Return updated row
        template = jinja_env.get_template('admin/partials/source_row.html')
        html = template.render(source=source)

        return HTMLResponse(content=html)

    finally:
        db.close()


@router.delete("/sources/{source_id}", response_class=HTMLResponse)
def delete_source(source_id: int):
    """
    Delete a source.

    Args:
        source_id: Source ID

    Returns:
        Empty HTML response (HTMX removes the row)
    """
    db = SessionLocal()

    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        source_name = source.name
        db.delete(source)
        db.commit()

        logger.info("source_deleted", source_id=source_id, name=source_name)

        # Return empty response with success toast trigger
        return HTMLResponse(
            content="",
            headers={"HX-Trigger": "showToast"}
        )

    finally:
        db.close()
