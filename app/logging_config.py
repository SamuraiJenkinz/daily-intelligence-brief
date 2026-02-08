"""
Centralized logging configuration for MDInsights.

Configures structlog with JSON output and daily log rotation
for production-grade observability.
"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler
import structlog


def configure_logging(log_dir: str = "data/logs", log_level: str = "INFO"):
    """
    Configure structured logging with daily rotation and JSON output.

    Sets up:
    - stdlib logging with TimedRotatingFileHandler (daily rotation, 30-day retention)
    - Console output via StreamHandler
    - structlog with JSON renderer for structured logs
    - Integration between stdlib and structlog

    Args:
        log_dir: Directory for log files (default: data/logs)
        log_level: Logging level (default: INFO)
    """
    # Create log directory if not exists
    os.makedirs(log_dir, exist_ok=True)

    # Configure stdlib logging
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # File handler with daily rotation (30-day retention)
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "mdinsights.log"),
        when="midnight",
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addHandler(file_handler)

    # Console handler for stdout
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # Merge context variables
            structlog.processors.add_log_level,  # Add log level to event dict
            structlog.processors.StackInfoRenderer(),  # Render stack info if available
            structlog.processors.TimeStamper(fmt="iso", utc=True),  # ISO timestamp in UTC
            structlog.processors.JSONRenderer()  # Render as JSON
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level.upper(), logging.INFO)),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),  # Use stdlib logging
        cache_logger_on_first_use=True,
    )
