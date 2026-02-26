"""
ApiEvent ORM model for MDInsights enterprise API event tracking.

Records all enterprise API interactions (auth, news, equity, email) so the
admin dashboard (Phase 13) can display API health status and event history.
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Enum, ForeignKey

from app.database import Base


class ApiEventType(str, enum.Enum):
    """Enterprise API event types.

    Auth events (Phase 9):
        TOKEN_ACQUIRED  - First JWT token successfully obtained
        TOKEN_REFRESHED - JWT token proactively refreshed before expiry
        TOKEN_FAILED    - JWT token acquisition/refresh failed

    News events (Phase 10 - Factiva):
        NEWS_FETCH      - Successful Factiva article fetch
        NEWS_FALLBACK   - (Historical) Fallback event from multi-source era

    Equity events (Phase 11):
        EQUITY_FETCH    - Successful equity price fetch
        EQUITY_FALLBACK - Fell back to previous price data (API unavailable)

    Email events (Phase 12):
        EMAIL_SENT      - Enterprise email successfully delivered
        EMAIL_FALLBACK  - Fell back to Microsoft Graph (enterprise API unavailable)
    """
    TOKEN_ACQUIRED = "token_acquired"
    TOKEN_REFRESHED = "token_refreshed"
    TOKEN_FAILED = "token_failed"
    NEWS_FETCH = "news_fetch"
    NEWS_FALLBACK = "news_fallback"
    EQUITY_FETCH = "equity_fetch"
    EQUITY_FALLBACK = "equity_fallback"
    EMAIL_SENT = "email_sent"
    EMAIL_FALLBACK = "email_fallback"


class ApiEvent(Base):
    """
    ORM model for enterprise API event records.

    Each row represents a single API interaction event — token acquisition,
    news fetch, equity lookup, or email send — with success/failure status
    and optional structured detail for debugging.

    The api_events table is read by the Phase 13 admin dashboard to display
    real-time API health and recent event history per API.
    """
    __tablename__ = "api_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(Enum(ApiEventType), nullable=False)
    api_name = Column(String(50), nullable=False)  # "auth", "news", "equity", "email"
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, nullable=False)
    detail = Column(Text, nullable=True)  # JSON-safe string — never contains secrets
    run_id = Column(
        Integer,
        ForeignKey("runs.id"),
        nullable=True  # Null for out-of-pipeline calls (e.g., scripts/test_auth.py)
    )

    def __repr__(self) -> str:
        return (
            f"<ApiEvent(id={self.id}, type={self.event_type}, "
            f"api={self.api_name}, success={self.success})>"
        )
