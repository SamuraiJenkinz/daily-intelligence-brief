"""
EquityTicker ORM model for MDInsights.

Multi-row mapping table that associates company entity names (as extracted by
the AI classifier) with their exchange ticker symbols for equity price enrichment.

Created in Phase 11 — Equity Price Enrichment.

Each row maps one entity_name → (ticker, exchange) pair. The EquityPriceClient
reads enabled rows at enrichment time to look up current price data via the MMC
Core API equity endpoint.

The entity_name field must match exactly what the AI classifier produces (e.g.
"Marsh McLennan", "AIG", "Swiss Re") — this is the join key used in Plan 02
pipeline integration.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.database import Base


class EquityTicker(Base):
    """
    ORM model for entity-to-ticker mappings.

    Each row maps a company entity name (as extracted by AI classification) to
    its exchange ticker symbol. The pipeline enrichment step (Phase 11-02) uses
    these mappings to automatically fetch equity price data for relevant entities
    mentioned in classified articles.

    Admin-managed via /admin/equity CRUD interface.

    Fields:
        entity_name     - Company name as extracted by AI classifier (unique key)
        ticker          - Exchange ticker symbol (e.g. "MMC", "AIG")
        exchange        - Exchange code (e.g. "NYSE", "NASDAQ")
        enabled         - Disable mapping without deleting the row
        updated_at      - Auto-updated timestamp on every save
        updated_by      - Admin username/email who last modified this row
    """
    __tablename__ = "equity_tickers"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Entity name as extracted by AI classification — must match exactly
    entity_name = Column(
        String(200),
        unique=True,
        nullable=False,
        comment="Company name as extracted by AI classifier (join key for price lookup)"
    )

    # Exchange ticker symbol
    ticker = Column(
        String(20),
        nullable=False,
        comment="Exchange ticker symbol (e.g. 'MMC', 'AIG')"
    )

    # Exchange code
    exchange = Column(
        String(20),
        nullable=False,
        default="NYSE",
        comment="Exchange code (e.g. 'NYSE', 'NASDAQ', 'LSE')"
    )

    # Master switch — disable without deleting
    enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="If False, this mapping is skipped during price enrichment"
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
        comment="Username/email of admin who last modified this mapping"
    )

    def __repr__(self) -> str:
        return (
            f"<EquityTicker(entity_name='{self.entity_name}', "
            f"ticker='{self.ticker}', exchange='{self.exchange}', "
            f"enabled={self.enabled})>"
        )
