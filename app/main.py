"""
MDInsights API - Multi-role insurance intelligence briefing system.

FastAPI application entry point with database initialization and health check.
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import text

from app.database import Base, engine, SessionLocal
# Import models to register them with Base.metadata before create_all
from app.models import news_article, source, run, api_event  # noqa: F401
from app.config import get_settings
from app.routers.admin import router as admin_router
from app.routers.pipeline import router as pipeline_router
from app.logging_config import configure_logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Creates database tables on startup,
    yields control during app lifetime, and handles cleanup on shutdown.
    """
    # Configure logging first
    settings = get_settings()
    configure_logging(log_level=settings.log_level)

    # Startup: Create data directory and database tables
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

    yield

    # Shutdown: Clean up resources if needed
    logger.info("Application shutdown complete")


app = FastAPI(
    title="MDInsights API",
    description="Multi-role insurance intelligence briefing system",
    version="0.1.0",
    lifespan=lifespan
)

# Register API routers
app.include_router(admin_router)
app.include_router(pipeline_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.

    Logs all exceptions with full context and returns a generic
    error response to avoid exposing internal details.
    """
    logger.error(
        "unhandled_exception: %s %s - %s",
        request.method,
        str(request.url.path),
        str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/api/health", tags=["Health"])
def health_check() -> dict:
    """
    Health check endpoint.

    Returns service status for monitoring and load balancer health checks.
    Validates database connectivity, data directory writability, and service configuration.
    """
    checks = {}
    overall_status = "healthy"
    settings = get_settings()

    # Check database connectivity
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        overall_status = "unhealthy"

    # Check data directory writability
    data_dir = settings.data_dir
    try:
        os.makedirs(data_dir, exist_ok=True)
        test_file = os.path.join(data_dir, ".health_check")
        with open(test_file, "w") as f:
            f.write("health_check")
        os.remove(test_file)
        checks["data_directory"] = {
            "status": "healthy",
            "message": f"Data directory writable: {os.path.abspath(data_dir)}"
        }
    except Exception as e:
        checks["data_directory"] = {
            "status": "unhealthy",
            "message": f"Data directory not writable: {str(e)}"
        }
        overall_status = "unhealthy"

    # Check external services configuration
    checks["external_services"] = {}

    # Azure OpenAI
    if settings.is_azure_openai_configured():
        checks["external_services"]["azure_openai"] = {
            "status": "configured",
            "message": "All configuration keys present"
        }
    else:
        checks["external_services"]["azure_openai"] = {
            "status": "warning",
            "message": "Missing configuration: endpoint or api_key"
        }
        if overall_status == "healthy":
            overall_status = "degraded"

    # Microsoft Graph
    if settings.is_graph_configured():
        checks["external_services"]["microsoft_graph"] = {
            "status": "configured",
            "message": "All configuration keys present"
        }
    else:
        checks["external_services"]["microsoft_graph"] = {
            "status": "warning",
            "message": "Missing configuration: tenant_id, client_id, client_secret, or sender_email"
        }
        if overall_status == "healthy":
            overall_status = "degraded"

    # Apify
    if settings.is_apify_configured():
        checks["external_services"]["apify"] = {
            "status": "configured",
            "message": "All configuration keys present"
        }
    else:
        checks["external_services"]["apify"] = {
            "status": "warning",
            "message": "Missing configuration: token"
        }
        if overall_status == "healthy":
            overall_status = "degraded"

    # Azure Storage
    if settings.is_azure_storage_configured():
        checks["external_services"]["azure_storage"] = {
            "status": "configured",
            "message": "Azure Blob Storage connection configured"
        }
    else:
        checks["external_services"]["azure_storage"] = {
            "status": "info",
            "message": "Azure Blob Storage not configured (local backups only)"
        }

    # MMC Core API Authentication (OAuth2 JWT — required for Phase 12 enterprise email)
    # Missing is NOT degraded — enterprise email falls back to Graph API gracefully
    if settings.is_mmc_auth_configured():
        checks["external_services"]["mmc_auth"] = {
            "status": "configured",
            "message": "MMC Core API OAuth2 credentials present"
        }
    else:
        checks["external_services"]["mmc_auth"] = {
            "status": "info",
            "message": "MMC Core API auth not configured (enterprise email will use Graph API fallback)"
        }

    # MMC Core API Key (X-Api-Key — required for Phase 10 Factiva and Phase 11 equity)
    # Missing is NOT degraded — these phases have their own fallback sources
    if settings.is_mmc_api_key_configured():
        checks["external_services"]["mmc_api_key"] = {
            "status": "configured",
            "message": "MMC Core API X-Api-Key present"
        }
    else:
        checks["external_services"]["mmc_api_key"] = {
            "status": "info",
            "message": "MMC Core API key not configured (Factiva/equity will use fallback sources)"
        }

    # Check backup freshness
    backup_dir = os.path.join(settings.data_dir, "backups")
    if os.path.isdir(backup_dir):
        backup_files = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith("mdinsights_") and f.endswith(".db")],
            reverse=True
        )
        if backup_files:
            latest_backup = backup_files[0]
            backup_mtime = os.path.getmtime(os.path.join(backup_dir, latest_backup))
            backup_age_hours = (datetime.utcnow().timestamp() - backup_mtime) / 3600
            checks["backup"] = {
                "status": "healthy" if backup_age_hours < 36 else "warning",
                "latest_backup": latest_backup,
                "age_hours": round(backup_age_hours, 1),
                "message": f"Latest backup: {latest_backup} ({round(backup_age_hours, 1)}h ago)"
            }
        else:
            checks["backup"] = {"status": "warning", "message": "No backup files found"}
    else:
        checks["backup"] = {"status": "warning", "message": "Backup directory does not exist"}

    # Check log file status
    log_dir = os.path.join(settings.data_dir, "logs")
    if os.path.isdir(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.startswith("mdinsights")]
        checks["logging"] = {
            "status": "healthy",
            "log_files": len(log_files),
            "log_directory": os.path.abspath(log_dir)
        }
    else:
        checks["logging"] = {"status": "warning", "message": "Log directory does not exist"}

    return {
        "status": overall_status,
        "service": "mdinsights",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect root to admin dashboard."""
    return RedirectResponse(url="/admin")


if __name__ == "__main__":
    import sys
    import asyncio

    if len(sys.argv) > 1 and sys.argv[1] == "run-pipeline":
        # CLI mode: run full pipeline with email delivery
        # Used by Windows Task Scheduler
        import structlog
        from app.database import Base, engine
        from app.services.collector import ApifyCollector
        from app.services.classifier import RoleClassificationService
        from app.services.reporter import RoleReportService
        from app.services.pipeline import PipelineOrchestrator

        # Configure logging first
        settings = get_settings()
        configure_logging(log_level=settings.log_level)

        # Ensure tables exist
        os.makedirs("data", exist_ok=True)
        Base.metadata.create_all(bind=engine)

        logger = structlog.get_logger("cli")

        logger.info("pipeline_cli_started")

        # Initialize services
        collector = ApifyCollector(apify_token=settings.apify_token)
        classifier = RoleClassificationService(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version
        )
        reporter = RoleReportService()

        # Initialize MMC Core API token manager
        from app.auth.token_manager import TokenManager
        token_manager = TokenManager()
        if token_manager.is_configured():
            logger.info("mmc_auth_configured", base_url=settings.mmc_api_base_url)
        else:
            logger.info("mmc_auth_not_configured", message="Enterprise APIs will use fallback methods")

        orchestrator = PipelineOrchestrator(
            collector=collector,
            classifier=classifier,
            reporter=reporter,
            token_manager=token_manager
        )

        # Run async pipeline
        result = asyncio.run(orchestrator.run_full_pipeline_with_email())

        # Log result
        if result["status"] == "completed":
            logger.info(
                "pipeline_cli_completed",
                run_id=result["run_id"],
                articles=result["articles_collected"],
                classified=result["articles_classified"],
                degraded_auth=result.get("degraded_auth", True),
                emails=result.get("emails_sent", {}),
                archived=result.get("reports_archived", [])
            )
            sys.exit(0)
        else:
            logger.error(
                "pipeline_cli_failed",
                error=result.get("error"),
                run_id=result.get("run_id")
            )
            sys.exit(1)
    elif len(sys.argv) > 1 and sys.argv[1] == "test-auth":
        # CLI mode: validate JWT token acquisition against staging endpoint
        import subprocess
        sys.exit(subprocess.call([sys.executable, "scripts/test_auth.py"]))
    else:
        # Web server mode (default)
        import uvicorn
        settings = get_settings()
        uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
