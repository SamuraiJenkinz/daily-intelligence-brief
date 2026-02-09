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
from app.services.search import ArticleSearchService
from app.database import SessionLocal
from app.models import Run, Source, NewsArticle
from app.models.source import SourceType
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
                'created_at': run.started_at.strftime('%Y-%m-%d %H:%M:%S') if run.started_at else None,
                'completed_at': run.completed_at.strftime('%Y-%m-%d %H:%M:%S') if run.completed_at else None,
                'articles_collected': run.articles_collected,
                'articles_classified': run.articles_classified,
                'error_message': run.error_message
            })

        last_run_data = None
        if last_run:
            last_run_data = {
                'status': last_run.status.value,
                'created_at': last_run.started_at.strftime('%Y-%m-%d %H:%M:%S') if last_run.started_at else None
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
    import re
    from fastapi.responses import FileResponse

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
