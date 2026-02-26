"""
Source ORM model for MDInsights.

Stores news source configurations for scraping.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
import enum
from app.database import Base


class SourceType(str, enum.Enum):
    """Source type enumeration."""
    APIFY = "apify"
    RSS = "rss"


class Source(Base):
    """
    ORM model for news sources.

    Each Source represents a website or feed that MDInsights monitors
    for relevant insurance news articles.
    """
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    url = Column(String(1000), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    actor_id = Column(String(255), nullable=True)  # Source-specific identifier (historical: Apify actor IDs)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name='{self.name}', type={self.source_type})>"
