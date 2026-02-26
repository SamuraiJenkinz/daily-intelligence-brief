"""
FactivaConfig ORM model for MDInsights.

Single-row configuration table for admin-configurable Factiva API query parameters.
Created in Phase 10, extended in Phase 14 — Factiva News Collection.

The row with id=1 is the active configuration. It is seeded on startup via migration
and managed by the Phase 10-03 admin UI.

Fields are stored as comma-separated strings (industry_codes, company_codes, keywords)
and parsed to lists at query time by FactivaCollector.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.database import Base


class FactivaConfig(Base):
    """
    ORM model for Factiva API query configuration.

    A single row (id=1) holds the active configuration. The FactivaCollector
    reads this row at collection time to build its search query.

    Admin-configurable fields:
        industry_codes  - Factiva industry code filter (comma-separated, e.g. "i82,i832")
        company_codes   - Factiva company/entity codes (comma-separated, e.g. "MM")
        keywords        - Free-text search terms (comma-separated, e.g. "insurance reinsurance")
        page_size       - Articles per search page (1-100, default 25)
        date_range_hours - Lookback window in hours for search date range (default 48)
        enabled         - Master switch: if False, FactivaCollector skips collection

    Audit fields:
        updated_at      - Last modification timestamp (auto-updated on save)
        updated_by      - Username/email of admin who made the change (nullable)
    """
    __tablename__ = "factiva_config"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Factiva search query parameters — parsed to lists by FactivaCollector
    industry_codes = Column(
        String(500),
        nullable=False,
        default="i82,i832",
        comment="Factiva industry code filter, comma-separated (e.g. 'i82,i832')"
    )
    company_codes = Column(
        String(500),
        nullable=False,
        default="MM",
        comment="Factiva company/entity codes, comma-separated (e.g. 'MM')"
    )
    keywords = Column(
        String(500),
        nullable=False,
        default="insurance reinsurance",
        comment="Free-text keyword search terms, comma-separated"
    )
    page_size = Column(
        Integer,
        nullable=False,
        default=25,
        comment="Articles per search page (1-100)"
    )
    date_range_hours = Column(
        Integer,
        nullable=False,
        default=48,
        comment="Lookback window in hours for Factiva search date range (default 48)"
    )

    # Master switch — set False to disable Factiva without removing config
    enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="If False, FactivaCollector skips collection entirely"
    )

    # Audit trail
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=True,
        comment="Auto-updated on every save"
    )
    updated_by = Column(
        String(100),
        nullable=True,
        comment="Username/email of admin who last modified this config"
    )

    def __repr__(self) -> str:
        return (
            f"<FactivaConfig(id={self.id}, enabled={self.enabled}, "
            f"industry_codes='{self.industry_codes}', keywords='{self.keywords}', "
            f"date_range_hours={self.date_range_hours})>"
        )
