"""
Admin router for manual pipeline triggering and run management.

Provides endpoints for:
- Manual pipeline execution
- Run history
- Admin UI
- Source management
- Recipient management
"""
import json
import structlog
import re
from typing import List, Dict, Optional
from fastapi import APIRouter, Query, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from pydantic import BaseModel, EmailStr, ValidationError, field_validator

from app.config import get_settings
from app.services.classifier import RoleClassificationService
from app.services.reporter import RoleReportService
from app.services.pipeline import PipelineOrchestrator
from app.services.search import ArticleSearchService
from app.database import SessionLocal
from app.models import Run, Source, NewsArticle
from app.models.source import SourceType
from app.models.factiva_config import FactivaConfig
from app.models.equity_ticker import EquityTicker
from app.models.api_event import ApiEvent, ApiEventType
from app.schemas.admin import SourceCreate, SourceUpdate
from datetime import datetime, date
from sqlalchemy import func
import math


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Setup Jinja2 environment for admin templates
app_dir = Path(__file__).parent.parent
templates_dir = app_dir / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    autoescape=True
)
jinja_env.filters["fromjson"] = json.loads


def _get_enterprise_api_status(db) -> list:
    """
    Query api_events table for the most recent event per enterprise API.

    Returns a list of dicts with keys:
        api_name, display_name, status, last_checked, reason

    Status values:
        healthy   - Most recent event was a success
        degraded  - Most recent event was a fallback (service worked via fallback)
        offline   - Most recent event was a failure (not a fallback)
        unknown   - No events recorded for this API
    """
    DISPLAY_NAMES = {
        "auth": "Authentication",
        "news": "News (Factiva)",
        "equity": "Equity Prices",
        "email": "Email Delivery",
    }
    FALLBACK_TYPES = {
        ApiEventType.EQUITY_FALLBACK,
        ApiEventType.EMAIL_FALLBACK,
    }

    result = []
    for api_name in ["auth", "news", "equity", "email"]:
        latest = (
            db.query(ApiEvent)
            .filter(ApiEvent.api_name == api_name)
            .order_by(ApiEvent.timestamp.desc())
            .first()
        )

        if latest is None:
            status = "unknown"
            last_checked = None
            reason = None
        elif latest.success:
            status = "healthy"
            last_checked = latest.timestamp.strftime("%Y-%m-%d %H:%M")
            reason = None
        else:
            if latest.event_type in FALLBACK_TYPES:
                status = "degraded"
            else:
                status = "offline"
            last_checked = latest.timestamp.strftime("%Y-%m-%d %H:%M")
            reason = (latest.detail[:100] if latest.detail else None)

        result.append({
            "api_name": api_name,
            "display_name": DISPLAY_NAMES[api_name],
            "status": status,
            "last_checked": last_checked,
            "reason": reason,
        })

    return result


def _get_fallback_events(db, limit: int = 20) -> list:
    """
    Query api_events table for recent fallback/failure events.

    Returns a list of dicts with keys:
        timestamp, api_name, event_type, reason

    Covers: EQUITY_FALLBACK, EMAIL_FALLBACK, TOKEN_FAILED
    """
    FALLBACK_EVENT_TYPES = [
        ApiEventType.EQUITY_FALLBACK,
        ApiEventType.EMAIL_FALLBACK,
        ApiEventType.TOKEN_FAILED,
    ]

    events = (
        db.query(ApiEvent)
        .filter(ApiEvent.event_type.in_(FALLBACK_EVENT_TYPES))
        .order_by(ApiEvent.timestamp.desc())
        .limit(limit)
        .all()
    )

    result = []
    for event in events:
        result.append({
            "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M"),
            "api_name": event.api_name,
            "event_type": event.event_type.value.replace("_", " ").title(),
            "reason": (event.detail[:100] if event.detail else None),
        })

    return result


def _update_env_var(env_content: str, var_name: str, value: str) -> str:
    """
    Update or append a variable in .env file content.

    If the variable exists, its line is replaced.
    If not found, it is appended to the end of the content.

    Returns updated env_content string.
    """
    pattern = re.compile(f"^{re.escape(var_name)}=.*$", re.MULTILINE)
    if pattern.search(env_content):
        return pattern.sub(f"{var_name}={value}", env_content)
    else:
        if env_content and not env_content.endswith("\n"):
            env_content += "\n"
        env_content += f"{var_name}={value}\n"
        return env_content


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
            # Query per-run source breakdown (collector_source distribution)
            source_counts = db.query(
                NewsArticle.collector_source,
                func.count(NewsArticle.id)
            ).filter(
                NewsArticle.run_id == run.id
            ).group_by(NewsArticle.collector_source).all()

            source_breakdown = {(src or 'Factiva'): count for src, count in source_counts}

            runs_data.append({
                'id': run.id,
                'status': run.status.value,
                'created_at': run.started_at.strftime('%Y-%m-%d %H:%M:%S') if run.started_at else None,
                'completed_at': run.completed_at.strftime('%Y-%m-%d %H:%M:%S') if run.completed_at else None,
                'articles_collected': run.articles_collected,
                'articles_classified': run.articles_classified,
                'error_message': run.error_message,
                'source_breakdown': source_breakdown,
            })

        last_run_data = None
        if last_run:
            last_run_data = {
                'status': last_run.status.value,
                'created_at': last_run.started_at.strftime('%Y-%m-%d %H:%M:%S') if last_run.started_at else None
            }

        # Get enterprise API status and fallback events
        enterprise_status = _get_enterprise_api_status(db)
        fallback_events = _get_fallback_events(db)

        # Render template
        template = jinja_env.get_template('admin/dashboard.html')
        html = template.render(
            active_nav='dashboard',
            active_sources=active_sources,
            total_sources=total_sources,
            articles_today=articles_today,
            today_date=today.strftime('%Y-%m-%d'),
            last_run=last_run_data,
            runs=runs_data,
            enterprise_status=enterprise_status,
            fallback_events=fallback_events,
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
    template = jinja_env.get_template('admin/trigger.html')
    html = template.render(active_nav='trigger')
    return HTMLResponse(content=html)


@router.post("/trigger-pipeline", response_class=HTMLResponse)
def trigger_pipeline():
    """
    Manually trigger complete pipeline execution.

    Executes collection → classification → reporting workflow for all roles
    and returns generated HTML report with custom headers.

    Returns:
        HTMLResponse with generated report

    Raises:
        HTTPException: If pipeline execution fails
    """
    settings = get_settings()

    try:
        logger.info("manual_trigger_started")

        # Validate configuration
        if not settings.is_azure_openai_configured():
            raise HTTPException(
                status_code=500,
                detail="Azure OpenAI not configured. Set credentials in .env"
            )

        # Initialize services
        classifier = RoleClassificationService(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version
        )
        reporter = RoleReportService()

        # Initialize pipeline orchestrator
        orchestrator = PipelineOrchestrator(
            classifier=classifier,
            reporter=reporter
        )

        # Execute pipeline
        result = orchestrator.run_full_pipeline()

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


@router.post("/trigger-pipeline-email", response_class=HTMLResponse)
async def trigger_pipeline_with_email():
    """
    Manually trigger complete pipeline with email delivery.

    Executes collection → classification → reporting → email workflow
    for all roles.

    Returns:
        HTMLResponse with pipeline result summary
    """
    settings = get_settings()

    try:
        logger.info("manual_trigger_with_email_started")

        # Validate configuration
        if not settings.is_azure_openai_configured():
            raise HTTPException(
                status_code=500,
                detail="Azure OpenAI not configured. Set credentials in .env"
            )

        if not settings.is_graph_configured():
            raise HTTPException(
                status_code=500,
                detail="Microsoft Graph not configured. Set GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, and GRAPH_SENDER_EMAIL in .env"
            )

        # Initialize services
        classifier = RoleClassificationService(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version
        )
        reporter = RoleReportService()

        orchestrator = PipelineOrchestrator(
            classifier=classifier,
            reporter=reporter
        )

        # Execute full pipeline with email delivery
        result = await orchestrator.run_full_pipeline_with_email()

        if result["status"] != "completed":
            error_msg = result.get("error", "Unknown error")
            logger.error("manual_trigger_email_failed", error=error_msg)
            raise HTTPException(
                status_code=500,
                detail=f"Pipeline execution failed: {error_msg}"
            )

        logger.info(
            "manual_trigger_email_completed",
            run_id=result["run_id"],
            articles_collected=result["articles_collected"],
            articles_classified=result["articles_classified"],
            emails_sent=result.get("emails_sent", {})
        )

        return HTMLResponse(
            content=result.get("html_output", ""),
            headers={
                "X-MDInsights-Run-ID": str(result["run_id"]),
                "X-Articles-Collected": str(result["articles_collected"]),
                "X-Articles-Classified": str(result["articles_classified"]),
                "X-Emails-Sent": json.dumps(result.get("emails_sent", {})),
                "X-Reports-Archived": str(len(result.get("reports_archived", [])))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("manual_trigger_email_error", error=str(e), exc_info=True)
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
                "created_at": run.started_at.isoformat() if run.started_at else None,
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
    enabled: bool = Form(True)
):
    """
    Create a new source.

    Args:
        name: Source name
        url: Source URL
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
                enabled=enabled
            )
        except ValidationError as e:
            # Return form with errors
            errors = {err["loc"][0]: err["msg"] for err in e.errors()}
            template = jinja_env.get_template('admin/partials/source_form.html')
            html = template.render(errors=errors, form_data={
                "name": name,
                "url": url,
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
                "enabled": enabled
            })
            return HTMLResponse(content=html, status_code=422)

        # Create new source
        # Use RSS as default source_type (DB column is NOT NULL, RSS is safe default)
        new_source = Source(
            name=source_data.name,
            url=source_data.url,
            source_type=SourceType.RSS,
            actor_id=None,
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
    enabled: bool = Form(False)
):
    """
    Update an existing source.

    Args:
        source_id: Source ID
        name: Source name
        url: Source URL
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

        # Update source (preserve existing source_type and actor_id)
        source.name = source_data.name
        source.url = source_data.url
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


# Pydantic schema for recipient validation
class RecipientUpdate(BaseModel):
    """Schema for validating recipient email lists."""
    to: str = ""
    cc: str = ""
    bcc: str = ""

    @field_validator('to', 'cc', 'bcc')
    @classmethod
    def validate_emails(cls, v: str) -> str:
        """Validate that all emails in comma-separated list are valid."""
        if not v or not v.strip():
            return ""

        # Split by comma and validate each email
        emails = [e.strip() for e in v.split(',') if e.strip()]

        # Simple email regex validation
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        for email in emails:
            if not email_pattern.match(email):
                raise ValueError(f"Invalid email address: {email}")

        return v


@router.get("/recipients", response_class=HTMLResponse)
def get_recipients_page(request: Request):
    """
    Serve recipient management page.

    Shows email recipients for all four roles (Brokers, Leadership,
    Compliance, Underwriting) with inline editing capability.

    Args:
        request: FastAPI request object for HTMX detection

    Returns:
        HTML response with recipient management interface
    """
    settings = get_settings()

    # Build recipients dict for all roles
    roles = ["Brokers", "Leadership", "Compliance", "Underwriting"]
    recipients = {}

    for role in roles:
        recipients[role] = settings.get_email_recipients(role)

    # Check if this is an HTMX request
    is_htmx = request.headers.get("HX-Request") == "true"

    if is_htmx:
        # Return partial (though unlikely for this endpoint)
        template = jinja_env.get_template('admin/recipients.html')
        html = template.render(all_recipients=recipients, active_nav="recipients")
    else:
        # Return full page
        template = jinja_env.get_template('admin/recipients.html')
        html = template.render(all_recipients=recipients, active_nav="recipients")

    return HTMLResponse(content=html)


@router.get("/recipients/{role}/edit", response_class=HTMLResponse)
def get_recipient_edit_form(role: str):
    """
    Get edit form partial for a role's recipients.

    Args:
        role: Role name (Brokers, Leadership, Compliance, Underwriting)

    Returns:
        HTML response with recipient card in edit mode

    Raises:
        HTTPException: If role is invalid
    """
    valid_roles = ["Brokers", "Leadership", "Compliance", "Underwriting"]

    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    settings = get_settings()
    recipients = settings.get_email_recipients(role)

    # Convert lists back to comma-separated strings for form
    form_data = {
        "to": ", ".join(recipients.to),
        "cc": ", ".join(recipients.cc),
        "bcc": ", ".join(recipients.bcc)
    }

    template = jinja_env.get_template('admin/partials/recipient_card.html')
    html = template.render(role=role, recipients=recipients, form_data=form_data, edit=True)

    return HTMLResponse(content=html)


@router.post("/recipients/{role}", response_class=HTMLResponse)
def update_recipients(
    role: str,
    to: str = Form(default=""),
    cc: str = Form(default=""),
    bcc: str = Form(default="")
):
    """
    Update email recipients for a role.

    Saves changes to .env file and clears settings cache so
    changes take effect on next pipeline run.

    Args:
        role: Role name (Brokers, Leadership, Compliance, Underwriting)
        to: Comma-separated TO email addresses
        cc: Comma-separated CC email addresses
        bcc: Comma-separated BCC email addresses

    Returns:
        HTML response with updated recipient card

    Raises:
        HTTPException: If role is invalid or validation fails
    """
    valid_roles = ["Brokers", "Leadership", "Compliance", "Underwriting"]

    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    try:
        # Validate input
        recipient_data = RecipientUpdate(to=to, cc=cc, bcc=bcc)
    except ValidationError as e:
        # Return edit form with errors
        errors = {err["loc"][0]: err["msg"] for err in e.errors()}

        settings = get_settings()
        recipients = settings.get_email_recipients(role)

        template = jinja_env.get_template('admin/partials/recipient_card.html')
        html = template.render(
            role=role,
            recipients=recipients,
            form_data={"to": to, "cc": cc, "bcc": bcc},
            edit=True,
            errors=errors
        )
        return HTMLResponse(content=html, status_code=422)

    # Update .env file
    env_path = Path(".env")

    # Map role to env variable prefixes
    role_prefix_map = {
        "Brokers": "REPORT_RECIPIENTS_BROKERS",
        "Leadership": "REPORT_RECIPIENTS_LEADERSHIP",
        "Compliance": "REPORT_RECIPIENTS_COMPLIANCE",
        "Underwriting": "REPORT_RECIPIENTS_UNDERWRITING"
    }

    prefix = role_prefix_map[role]

    # Read current .env content
    if env_path.exists():
        env_content = env_path.read_text(encoding="utf-8")
    else:
        env_content = ""

    # Update or add each recipient type
    for field_name, field_value in [("", to), ("_CC", cc), ("_BCC", bcc)]:
        var_name = f"{prefix}{field_name}"
        pattern = re.compile(f"^{re.escape(var_name)}=.*$", re.MULTILINE)

        if pattern.search(env_content):
            # Replace existing line
            env_content = pattern.sub(f"{var_name}={field_value}", env_content)
        else:
            # Append new line
            if env_content and not env_content.endswith("\n"):
                env_content += "\n"
            env_content += f"{var_name}={field_value}\n"

    # Write updated content
    env_path.write_text(env_content, encoding="utf-8")

    # Clear settings cache
    get_settings.cache_clear()

    logger.info("recipients_updated", role=role)

    # Return updated card in display mode
    settings = get_settings()
    recipients = settings.get_email_recipients(role)

    template = jinja_env.get_template('admin/partials/recipient_card.html')
    html = template.render(role=role, recipients=recipients, edit=False)

    return HTMLResponse(content=html)


@router.get("/archive", response_class=HTMLResponse)
def get_archive_browser(
    request: Request,
    role: str = Query(default=None),
    month: str = Query(default=None)
):
    """
    Browse archived reports grouped by date.

    Args:
        request: FastAPI request object
        role: Optional filter by role (brokers, leadership, compliance, underwriting)
        month: Optional filter by month (YYYY-MM format)

    Returns:
        HTML archive browser page or HTMX partial
    """
    import re
    from collections import defaultdict

    # Get reports directory
    reports_dir = Path(__file__).parent.parent.parent / "data" / "reports"

    # Valid roles (lowercase)
    valid_roles = ["brokers", "leadership", "compliance", "underwriting"]

    # Build archive data
    archive_data = defaultdict(lambda: {role: None for role in valid_roles})

    if reports_dir.exists():
        # Scan directory structure: data/reports/{role}/{YYYY-MM-DD}.html
        for role_dir in reports_dir.iterdir():
            if not role_dir.is_dir():
                continue

            role_name = role_dir.name
            if role_name not in valid_roles:
                continue

            # Apply role filter if specified
            if role and role_name != role.lower():
                continue

            # Scan for date-named HTML files
            for report_file in role_dir.glob("*.html"):
                # Validate filename format (YYYY-MM-DD.html)
                if not re.match(r'^\d{4}-\d{2}-\d{2}\.html$', report_file.name):
                    continue

                date_str = report_file.stem  # Remove .html extension

                # Apply month filter if specified
                if month and not date_str.startswith(month):
                    continue

                # Get file size
                size_bytes = report_file.stat().st_size
                size_kb = size_bytes / 1024

                archive_data[date_str][role_name] = {
                    "path": str(report_file.relative_to(reports_dir.parent.parent)),
                    "size_kb": round(size_kb, 1),
                    "exists": True
                }

    # Sort by date descending
    sorted_dates = sorted(archive_data.keys(), reverse=True)

    # Build sorted archive list
    archive_list = [
        {
            "date": date_str,
            "reports": archive_data[date_str]
        }
        for date_str in sorted_dates
    ]

    # Get available months for filter dropdown
    available_months = sorted(set(date[:7] for date in archive_data.keys()), reverse=True)

    # Check if HTMX request
    is_htmx = request.headers.get("HX-Request") == "true"

    if is_htmx:
        # Return just the archive list partial
        template = jinja_env.get_template('admin/partials/archive_list.html')
        html = template.render(archive_list=archive_list)
    else:
        # Return full page
        template = jinja_env.get_template('admin/archive.html')
        html = template.render(
            active_nav='archive',
            archive_list=archive_list,
            available_months=available_months,
            selected_role=role,
            selected_month=month,
            valid_roles=valid_roles
        )

    return HTMLResponse(content=html)


@router.get("/audio/{role}/{date}")
async def stream_audio(role: str, date: str):
    """
    Stream MP3 audio file for a role's daily briefing.

    Security:
    - Validates role against whitelist
    - Validates date format (YYYY-MM-DD)
    - Uses Path.resolve() to prevent path traversal
    - Verifies final path is within data/audio/

    Args:
        role: Role name (brokers, leadership, compliance, underwriting)
        date: Date in YYYY-MM-DD format

    Returns:
        FileResponse with MP3 audio content (supports HTTP range requests for seeking)

    Raises:
        HTTPException: 404 if file not found, invalid role, or invalid path
    """
    # Valid roles (lowercase)
    valid_roles = ["brokers", "leadership", "compliance", "underwriting"]

    # SECURITY: Validate role
    if role.lower() not in valid_roles:
        logger.warning("audio_stream_invalid_role", role=role)
        raise HTTPException(status_code=404, detail="Invalid role")

    # SECURITY: Validate date format (YYYY-MM-DD)
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        logger.warning("audio_stream_invalid_date", date=date)
        raise HTTPException(status_code=404, detail="Invalid date format")

    # Build audio path
    audio_dir = Path(__file__).parent.parent.parent / "data" / "audio"
    audio_path = audio_dir / date / f"{role.lower()}.mp3"

    # SECURITY: Resolve path and verify it's within audio directory
    try:
        resolved_path = audio_path.resolve()
        resolved_audio_dir = audio_dir.resolve()

        # Check if resolved path is within audio directory
        if not str(resolved_path).startswith(str(resolved_audio_dir)):
            logger.warning(
                "audio_stream_path_traversal_attempt",
                role=role,
                date=date,
                attempted_path=str(resolved_path)
            )
            raise HTTPException(status_code=404, detail="Invalid path")

        # Check if file exists
        if not resolved_path.exists() or not resolved_path.is_file():
            raise HTTPException(status_code=404, detail="Audio file not found")

        # Log successful stream
        logger.info("audio_stream_served", role=role, date=date)

        # Return file with audio/mpeg MIME type
        # FileResponse automatically handles HTTP range requests (Accept-Ranges header)
        # which enables browser seeking in HTML5 audio player
        return FileResponse(
            path=str(resolved_path),
            media_type="audio/mpeg",
            filename=f"{role}_{date}.mp3"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("audio_stream_error", role=role, date=date, error=str(e))
        raise HTTPException(status_code=404, detail="Audio file not found")


@router.get("/archive/{role}/{date}", response_class=HTMLResponse)
def get_archived_report(role: str, date: str):
    """
    Serve an archived report HTML file.

    Security:
    - Validates date format (YYYY-MM-DD)
    - Validates role is in allowed list
    - Uses Path.resolve() to prevent path traversal
    - Verifies final path is within data/reports/

    Args:
        role: Role name (lowercase)
        date: Date in YYYY-MM-DD format

    Returns:
        FileResponse with HTML content

    Raises:
        HTTPException: 404 if file not found or invalid path
    """
    # Valid roles (lowercase)
    valid_roles = ["brokers", "leadership", "compliance", "underwriting"]

    # SECURITY: Validate role
    if role.lower() not in valid_roles:
        raise HTTPException(status_code=404, detail="Invalid role")

    # SECURITY: Validate date format (YYYY-MM-DD)
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=404, detail="Invalid date format")

    # Build path
    reports_dir = Path(__file__).parent.parent.parent / "data" / "reports"
    report_path = reports_dir / role.lower() / f"{date}.html"

    # SECURITY: Resolve path and verify it's within reports directory
    try:
        resolved_path = report_path.resolve()
        resolved_reports_dir = reports_dir.resolve()

        # Check if resolved path is within reports directory
        if not str(resolved_path).startswith(str(resolved_reports_dir)):
            raise HTTPException(status_code=404, detail="Invalid path")

        # Check if file exists
        if not resolved_path.exists() or not resolved_path.is_file():
            raise HTTPException(status_code=404, detail="Report not found")

    except Exception as e:
        logger.error("archive_access_error", role=role, date=date, error=str(e))
        raise HTTPException(status_code=404, detail="Report not found")

    # Return file (no filename= so browser renders inline instead of downloading)
    return FileResponse(
        path=str(resolved_path),
        media_type="text/html"
    )


@router.get("/runs-table", response_class=HTMLResponse)
def get_runs_table():
    """
    Get recent runs table HTML partial.

    Returns:
        HTML table partial with recent pipeline runs
    """
    db = SessionLocal()

    try:
        # Get recent runs (last 10)
        runs = db.query(Run).order_by(Run.id.desc()).limit(10).all()

        # Build HTML table
        if not runs:
            html = """
            <div class="text-center p-4 text-muted">
                <i class="bi bi-inbox" style="font-size: 3rem;"></i>
                <p class="mt-2">No pipeline runs yet</p>
            </div>
            """
        else:
            rows = []
            for run in runs:
                status_badge = {
                    'completed': '<span class="badge bg-success">Completed</span>',
                    'failed': '<span class="badge bg-danger">Failed</span>',
                    'running': '<span class="badge bg-primary">Running</span>',
                    'pending': '<span class="badge bg-secondary">Pending</span>'
                }.get(run.status.value, f'<span class="badge bg-secondary">{run.status.value}</span>')

                created = run.started_at.strftime('%Y-%m-%d %H:%M:%S') if run.started_at else 'N/A'
                completed = run.completed_at.strftime('%Y-%m-%d %H:%M:%S') if run.completed_at else 'N/A'

                error_cell = ''
                if run.error_message:
                    error_cell = f'<small class="text-danger">{run.error_message[:100]}...</small>'

                row = f"""
                <tr>
                    <td>{run.id}</td>
                    <td>{status_badge}</td>
                    <td><small>{created}</small></td>
                    <td><small>{completed}</small></td>
                    <td>{run.articles_collected or 0}</td>
                    <td>{run.articles_classified or 0}</td>
                    <td>{error_cell}</td>
                </tr>
                """
                rows.append(row)

            html = f"""
            <div class="table-responsive">
                <table class="table table-hover mb-0">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Completed</th>
                            <th>Collected</th>
                            <th>Classified</th>
                            <th>Error</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
            """

        return HTMLResponse(content=html)

    finally:
        db.close()


@router.get("/factiva", response_class=HTMLResponse)
def get_factiva_config():
    """
    Serve Factiva query configuration page.

    Displays the current FactivaConfig row (id=1) with form controls for
    industry codes, company codes, keywords, page size, and enabled toggle.

    Returns:
        HTML Factiva configuration page
    """
    db = SessionLocal()
    try:
        config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
        if not config:
            # Seed default if missing (startup migration normally handles this)
            config = FactivaConfig(
                id=1,
                industry_codes="i82,i832",
                company_codes="MM",
                keywords="insurance reinsurance",
                page_size=25,
                enabled=True,
            )
            db.add(config)
            db.commit()
            db.refresh(config)

        template = jinja_env.get_template("admin/factiva.html")
        return HTMLResponse(template.render(
            config=config,
            active_nav="factiva",
            success=None,
            error=None,
        ))
    finally:
        db.close()


@router.post("/factiva", response_class=HTMLResponse)
def update_factiva_config(
    industry_codes: str = Form(""),
    company_codes: str = Form(""),
    keywords: str = Form(""),
    page_size: int = Form(25),
    date_range_hours: int = Form(48),
    enabled: str = Form("false"),
):
    """
    Update Factiva query configuration.

    Persists changes to the factiva_config DB table (row id=1). Changes take
    effect on the next pipeline run.

    Note: The enabled field uses a hidden+checkbox pair — the hidden field sends
    "false" when the checkbox is unchecked, and "true" when checked (checkbox
    value overrides hidden input in form submission order).

    Args:
        industry_codes: Comma-separated Factiva industry codes (e.g. "i82,i832")
        company_codes: Comma-separated Factiva company codes (e.g. "MM")
        keywords: Free-text search keywords (e.g. "insurance reinsurance")
        page_size: Articles per search page (10, 25, 50, or 100)
        date_range_hours: Hours to look back for articles (1-168, default 48)
        enabled: "true" or "false" string from hidden+checkbox field pair

    Returns:
        HTML Factiva configuration page with success or error message
    """
    db = SessionLocal()
    config = None
    try:
        config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
        if not config:
            config = FactivaConfig(id=1)
            db.add(config)

        # Validate page_size
        if page_size not in (10, 25, 50, 100):
            page_size = 25

        # Validate date_range_hours (clamp to 1-168 hours)
        if date_range_hours < 1:
            date_range_hours = 1
        elif date_range_hours > 168:
            date_range_hours = 168

        # Clean comma-separated inputs — strip whitespace, remove empty entries
        config.industry_codes = ",".join(
            c.strip() for c in industry_codes.split(",") if c.strip()
        )
        config.company_codes = ",".join(
            c.strip() for c in company_codes.split(",") if c.strip()
        )
        config.keywords = keywords.strip()
        config.page_size = page_size
        config.date_range_hours = date_range_hours
        # Convert string "true"/"false" from hidden+checkbox pair to bool
        config.enabled = enabled.lower() in ("true", "on", "1", "yes")
        config.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(config)

        logger.info(
            "factiva_config_updated",
            industry_codes=config.industry_codes,
            company_codes=config.company_codes,
            keywords=config.keywords,
            page_size=config.page_size,
            date_range_hours=config.date_range_hours,
            enabled=config.enabled,
        )

        template = jinja_env.get_template("admin/factiva.html")
        return HTMLResponse(template.render(
            config=config,
            active_nav="factiva",
            success="Factiva configuration saved successfully.",
            error=None,
        ))

    except Exception as e:
        logger.error("factiva_config_update_failed", error=str(e))
        template = jinja_env.get_template("admin/factiva.html")
        return HTMLResponse(template.render(
            config=config if config else FactivaConfig(id=1),
            active_nav="factiva",
            success=None,
            error=f"Failed to save configuration: {str(e)}",
        ))
    finally:
        db.close()


@router.get("/search", response_class=HTMLResponse)
def search_articles(
    request: Request,
    q: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(default=1, ge=1)
):
    """
    Search articles with FTS5 full-text search and filters.

    Provides debounced keyword search with multi-filter support:
    - Keyword search across title, description, summary (FTS5 with BM25 ranking)
    - Filter by role, priority, source, date range
    - Paginated results (25 per page)

    Args:
        request: FastAPI request object for HTMX detection
        q: Search query string
        role: Filter by role (Brokers, Leadership, etc.)
        date_from: Filter articles published on or after this date (YYYY-MM-DD)
        date_to: Filter articles published on or before this date (YYYY-MM-DD)
        priority: Filter by priority (Critical, High, Medium, Monitor)
        source: Filter by source name
        page: Page number for pagination

    Returns:
        HTML response with search page or results partial
    """
    db = SessionLocal()

    try:
        # Parse dates
        date_from_parsed = None
        date_to_parsed = None

        if date_from:
            try:
                date_from_parsed = datetime.strptime(date_from, "%Y-%m-%d").date()
            except ValueError:
                pass

        if date_to:
            try:
                date_to_parsed = datetime.strptime(date_to, "%Y-%m-%d").date()
            except ValueError:
                pass

        # Pagination
        per_page = 25
        offset = (page - 1) * per_page

        # Search articles
        articles, total_count = ArticleSearchService.search(
            db=db,
            query=q,
            role=role,
            date_from=date_from_parsed,
            date_to=date_to_parsed,
            priority=priority,
            source_name=source,
            limit=per_page,
            offset=offset
        )

        # Calculate total pages
        total_pages = math.ceil(total_count / per_page) if total_count > 0 else 0

        # Get filter options
        filter_options = ArticleSearchService.get_filter_options(db)

        # Check if HTMX request
        is_htmx = request.headers.get("HX-Request") == "true"

        if is_htmx:
            # Return just the results partial
            template = jinja_env.get_template('admin/partials/search_results.html')
            html = template.render(
                articles=articles,
                total_count=total_count,
                current_page=page,
                total_pages=total_pages,
                q=q,
                role=role,
                date_from=date_from,
                date_to=date_to,
                priority=priority,
                source=source
            )
        else:
            # Return full page
            template = jinja_env.get_template('admin/search.html')
            html = template.render(
                active_nav='search',
                articles=articles,
                total_count=total_count,
                current_page=page,
                total_pages=total_pages,
                q=q,
                role=role,
                date_from=date_from,
                date_to=date_to,
                priority=priority,
                source=source,
                filter_options=filter_options
            )

        return HTMLResponse(content=html)

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Equity Ticker Mappings — CRUD routes
# Phase 11: Entity-to-ticker mappings for equity price enrichment
# ---------------------------------------------------------------------------


@router.get("/equity", response_class=HTMLResponse)
def get_equity_tickers(request: Request):
    """
    Serve equity ticker mapping management page.

    Lists all EquityTicker rows with add/edit/delete capability.
    Used by admin to configure entity-to-ticker mappings for equity price enrichment.

    Returns:
        HTML equity ticker management page
    """
    db = SessionLocal()
    try:
        tickers = db.query(EquityTicker).order_by(EquityTicker.entity_name).all()
        # Read optional flash messages from query params
        success = request.query_params.get("success")
        error = request.query_params.get("error")

        template = jinja_env.get_template("admin/equity.html")
        return HTMLResponse(template.render(
            tickers=tickers,
            active_nav="equity",
            success=success,
            error=error,
        ))
    finally:
        db.close()


@router.post("/equity", response_class=HTMLResponse)
def add_equity_ticker(
    entity_name: str = Form(""),
    ticker: str = Form(""),
    exchange: str = Form("NYSE"),
    enabled: str = Form("false"),
):
    """
    Add a new entity-to-ticker mapping.

    Validates entity_name is non-empty and unique (case-insensitive).
    Redirects to /admin/equity with success or error flash message.

    Args:
        entity_name: Company name as extracted by AI classifier
        ticker:      Exchange ticker symbol (e.g. "MMC")
        exchange:    Exchange code (e.g. "NYSE")
        enabled:     "true"/"false" from hidden+checkbox pair
    """
    from fastapi.responses import RedirectResponse as _RedirectResponse
    from sqlalchemy import func as sqla_func

    entity_name = entity_name.strip()
    ticker_symbol = ticker.strip().upper()
    exchange = exchange.strip().upper() or "NYSE"
    is_enabled = enabled.lower() in ("true", "on", "1", "yes")

    # Validate required fields
    if not entity_name:
        return _RedirectResponse(
            url="/admin/equity?error=Entity+name+is+required",
            status_code=303,
        )
    if not ticker_symbol:
        return _RedirectResponse(
            url="/admin/equity?error=Ticker+symbol+is+required",
            status_code=303,
        )

    db = SessionLocal()
    try:
        # Check uniqueness — case-insensitive match
        existing = db.query(EquityTicker).filter(
            sqla_func.lower(EquityTicker.entity_name) == entity_name.lower()
        ).first()
        if existing:
            return _RedirectResponse(
                url=f"/admin/equity?error=A+mapping+for+%27{entity_name}%27+already+exists",
                status_code=303,
            )

        new_ticker = EquityTicker(
            entity_name=entity_name,
            ticker=ticker_symbol,
            exchange=exchange,
            enabled=is_enabled,
            updated_at=datetime.utcnow(),
        )
        db.add(new_ticker)
        db.commit()

        logger.info(
            "equity_ticker_added",
            entity_name=entity_name,
            ticker=ticker_symbol,
            exchange=exchange,
            enabled=is_enabled,
        )

        return _RedirectResponse(
            url=f"/admin/equity?success=Mapping+for+%27{entity_name}%27+added+successfully",
            status_code=303,
        )

    except Exception as exc:
        logger.error("equity_ticker_add_failed", error=str(exc))
        return _RedirectResponse(
            url=f"/admin/equity?error=Failed+to+add+mapping:+{str(exc)[:100]}",
            status_code=303,
        )
    finally:
        db.close()


@router.post("/equity/delete/{ticker_id}", response_class=HTMLResponse)
def delete_equity_ticker(ticker_id: int):
    """
    Delete an equity ticker mapping by id.

    Redirects to /admin/equity with success flash message.

    Args:
        ticker_id: EquityTicker row id to delete
    """
    from fastapi.responses import RedirectResponse as _RedirectResponse

    db = SessionLocal()
    try:
        ticker_row = db.query(EquityTicker).filter(EquityTicker.id == ticker_id).first()
        if not ticker_row:
            return _RedirectResponse(
                url="/admin/equity?error=Mapping+not+found",
                status_code=303,
            )

        entity_name = ticker_row.entity_name
        db.delete(ticker_row)
        db.commit()

        logger.info("equity_ticker_deleted", ticker_id=ticker_id, entity_name=entity_name)

        return _RedirectResponse(
            url=f"/admin/equity?success=Mapping+for+%27{entity_name}%27+deleted",
            status_code=303,
        )

    except Exception as exc:
        logger.error("equity_ticker_delete_failed", ticker_id=ticker_id, error=str(exc))
        return _RedirectResponse(
            url=f"/admin/equity?error=Failed+to+delete+mapping:+{str(exc)[:100]}",
            status_code=303,
        )
    finally:
        db.close()


@router.get("/equity/edit/{ticker_id}", response_class=HTMLResponse)
def get_equity_ticker_edit(ticker_id: int):
    """
    Render edit form for a single equity ticker mapping.

    Args:
        ticker_id: EquityTicker row id to edit

    Returns:
        HTML edit page with fields pre-populated
    """
    db = SessionLocal()
    try:
        ticker_row = db.query(EquityTicker).filter(EquityTicker.id == ticker_id).first()
        if not ticker_row:
            raise HTTPException(status_code=404, detail="Ticker mapping not found")

        template = jinja_env.get_template("admin/equity_edit.html")
        return HTMLResponse(template.render(
            ticker=ticker_row,
            active_nav="equity",
            error=None,
        ))
    finally:
        db.close()


@router.post("/equity/edit/{ticker_id}", response_class=HTMLResponse)
def update_equity_ticker(
    ticker_id: int,
    entity_name: str = Form(""),
    ticker: str = Form(""),
    exchange: str = Form("NYSE"),
    enabled: str = Form("false"),
):
    """
    Update an equity ticker mapping.

    Validates entity_name uniqueness (excluding current row).
    Redirects to /admin/equity with success flash message.

    Args:
        ticker_id:   EquityTicker row id to update
        entity_name: Updated company entity name
        ticker:      Updated ticker symbol
        exchange:    Updated exchange code
        enabled:     "true"/"false" from hidden+checkbox pair
    """
    from fastapi.responses import RedirectResponse as _RedirectResponse
    from sqlalchemy import func as sqla_func

    entity_name = entity_name.strip()
    ticker_symbol = ticker.strip().upper()
    exchange = exchange.strip().upper() or "NYSE"
    is_enabled = enabled.lower() in ("true", "on", "1", "yes")

    # Validate required fields
    if not entity_name:
        return _RedirectResponse(
            url=f"/admin/equity/edit/{ticker_id}?error=Entity+name+is+required",
            status_code=303,
        )
    if not ticker_symbol:
        return _RedirectResponse(
            url=f"/admin/equity/edit/{ticker_id}?error=Ticker+symbol+is+required",
            status_code=303,
        )

    db = SessionLocal()
    try:
        row = db.query(EquityTicker).filter(EquityTicker.id == ticker_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Ticker mapping not found")

        # Check uniqueness — exclude the current row
        existing = db.query(EquityTicker).filter(
            sqla_func.lower(EquityTicker.entity_name) == entity_name.lower(),
            EquityTicker.id != ticker_id,
        ).first()
        if existing:
            # Re-render edit form with error (do not commit)
            # Build a temporary display object with the new values
            template = jinja_env.get_template("admin/equity_edit.html")
            display_row = EquityTicker(
                id=row.id,
                entity_name=entity_name,
                ticker=ticker_symbol,
                exchange=exchange,
                enabled=is_enabled,
                updated_at=row.updated_at,
            )
            return HTMLResponse(template.render(
                ticker=display_row,
                active_nav="equity",
                error=f"A mapping for '{entity_name}' already exists.",
            ))

        # Apply updates
        row.entity_name = entity_name
        row.ticker = ticker_symbol
        row.exchange = exchange
        row.enabled = is_enabled
        row.updated_at = datetime.utcnow()
        db.commit()

        logger.info(
            "equity_ticker_updated",
            ticker_id=ticker_id,
            entity_name=entity_name,
            ticker=ticker_symbol,
            exchange=exchange,
            enabled=is_enabled,
        )

        return _RedirectResponse(
            url=f"/admin/equity?success=Mapping+for+%27{entity_name}%27+updated+successfully",
            status_code=303,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("equity_ticker_update_failed", ticker_id=ticker_id, error=str(exc))
        return _RedirectResponse(
            url=f"/admin/equity?error=Failed+to+update+mapping:+{str(exc)[:100]}",
            status_code=303,
        )
    finally:
        db.close()


@router.get("/enterprise-config", response_class=HTMLResponse)
def get_enterprise_config():
    """
    Serve the Enterprise API credential configuration page.

    Displays current non-secret values and boolean flags for secret fields.
    Secret values (client secrets, API keys) are never rendered — only
    a boolean indicating whether they are set is passed to the template.

    Returns:
        HTML page with grouped credential form for MMC Core API and Microsoft Graph
    """
    settings = get_settings()

    config_display = {
        # Non-secret fields — render actual values
        "mmc_api_base_url": settings.mmc_api_base_url,
        "mmc_api_client_id": settings.mmc_api_client_id,
        "mmc_sender_email": settings.mmc_sender_email,
        "microsoft_tenant_id": settings.microsoft_tenant_id,
        "microsoft_client_id": settings.microsoft_client_id,
        "sender_email": settings.sender_email,
        # Secret fields — boolean flags only (never render actual secrets)
        "mmc_api_client_secret_set": bool(settings.mmc_api_client_secret.strip()),
        "mmc_api_key_set": bool(settings.mmc_api_key.strip()),
        "microsoft_client_secret_set": bool(settings.microsoft_client_secret.strip()),
    }

    template = jinja_env.get_template("admin/enterprise_config.html")
    return HTMLResponse(content=template.render(
        config=config_display,
        active_nav="enterprise_config",
        success=None,
        error=None,
    ))


@router.post("/enterprise-config", response_class=HTMLResponse)
def post_enterprise_config(
    mmc_api_base_url: str = Form(""),
    mmc_api_client_id: str = Form(""),
    mmc_api_client_secret: str = Form(""),
    mmc_api_key: str = Form(""),
    mmc_sender_email: str = Form(""),
    microsoft_tenant_id: str = Form(""),
    microsoft_client_id: str = Form(""),
    microsoft_client_secret: str = Form(""),
    sender_email: str = Form(""),
):
    """
    Save enterprise API credentials to .env file and clear settings cache.

    Non-secret fields are always written. Secret fields are only written
    when a non-blank value is provided (blank = keep existing value).

    Returns:
        HTML page with success or error message
    """
    try:
        env_path = Path(".env")

        if env_path.exists():
            env_content = env_path.read_text(encoding="utf-8")
        else:
            env_content = ""

        # Non-secret fields: always update
        NON_SECRET_FIELDS = [
            ("MMC_API_BASE_URL", mmc_api_base_url),
            ("MMC_API_CLIENT_ID", mmc_api_client_id),
            ("MMC_SENDER_EMAIL", mmc_sender_email),
            ("MICROSOFT_TENANT_ID", microsoft_tenant_id),
            ("MICROSOFT_CLIENT_ID", microsoft_client_id),
            ("SENDER_EMAIL", sender_email),
        ]
        for var_name, value in NON_SECRET_FIELDS:
            env_content = _update_env_var(env_content, var_name, value)

        # Secret fields: only update if non-blank value provided
        SECRET_FIELDS = [
            ("MMC_API_CLIENT_SECRET", mmc_api_client_secret),
            ("MMC_API_KEY", mmc_api_key),
            ("MICROSOFT_CLIENT_SECRET", microsoft_client_secret),
        ]
        for var_name, value in SECRET_FIELDS:
            if value.strip():
                env_content = _update_env_var(env_content, var_name, value)

        env_path.write_text(env_content, encoding="utf-8")

        # Clear settings cache so pipeline picks up new values
        get_settings.cache_clear()

        logger.info("enterprise_config_updated")

        # Re-read and re-render with success message
        settings = get_settings()
        config_display = {
            "mmc_api_base_url": settings.mmc_api_base_url,
            "mmc_api_client_id": settings.mmc_api_client_id,
            "mmc_sender_email": settings.mmc_sender_email,
            "microsoft_tenant_id": settings.microsoft_tenant_id,
            "microsoft_client_id": settings.microsoft_client_id,
            "sender_email": settings.sender_email,
            "mmc_api_client_secret_set": bool(settings.mmc_api_client_secret.strip()),
            "mmc_api_key_set": bool(settings.mmc_api_key.strip()),
            "microsoft_client_secret_set": bool(settings.microsoft_client_secret.strip()),
        }

        template = jinja_env.get_template("admin/enterprise_config.html")
        return HTMLResponse(content=template.render(
            config=config_display,
            active_nav="enterprise_config",
            success="Enterprise configuration saved successfully.",
            error=None,
        ))

    except Exception as e:
        logger.error("enterprise_config_update_failed", error=str(e))

        settings = get_settings()
        config_display = {
            "mmc_api_base_url": settings.mmc_api_base_url,
            "mmc_api_client_id": settings.mmc_api_client_id,
            "mmc_sender_email": settings.mmc_sender_email,
            "microsoft_tenant_id": settings.microsoft_tenant_id,
            "microsoft_client_id": settings.microsoft_client_id,
            "sender_email": settings.sender_email,
            "mmc_api_client_secret_set": bool(settings.mmc_api_client_secret.strip()),
            "mmc_api_key_set": bool(settings.mmc_api_key.strip()),
            "microsoft_client_secret_set": bool(settings.microsoft_client_secret.strip()),
        }

        template = jinja_env.get_template("admin/enterprise_config.html")
        return HTMLResponse(content=template.render(
            config=config_display,
            active_nav="enterprise_config",
            success=None,
            error=str(e),
        ))
