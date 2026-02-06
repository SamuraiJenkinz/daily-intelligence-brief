"""
Run ORM model for MDInsights.

Stores collection run metadata and status.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class RunStatus(str, enum.Enum):
    """Run status enumeration."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Run(Base):
    """
    ORM model for news collection runs.

    Each Run represents a single execution of the news collection process,
    tracking when it started, finished, how many articles were collected,
    and classification metrics (articles_classified, classification_errors).
    """
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(Enum(RunStatus), default=RunStatus.RUNNING, nullable=False)
    articles_collected = Column(Integer, default=0, nullable=False)
    articles_classified = Column(Integer, default=0, nullable=False)
    classification_errors = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    articles = relationship("NewsArticle", back_populates="run")

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, status={self.status}, articles={self.articles_collected})>"
