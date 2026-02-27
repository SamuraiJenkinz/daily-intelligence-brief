"""
NewsArticle ORM model for MDInsights.

Stores scraped news articles with multi-role classification results.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class NewsArticle(Base):
    """
    ORM model for news articles found during scraping runs.

    Each NewsArticle is associated with a Run (when it was discovered).
    Classification fields (roles, priority, summary, sentiment) are populated
    by Azure OpenAI after initial scraping.

    The 'roles' field stores a JSON array of role strings (e.g., ["Brokers", "Leadership"])
    to support multi-role assignment per article.

    Phase 3 fields (entities, impact_level, category, region, business_line) provide
    advanced classification for entity extraction and categorical filtering.
    """
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)

    # News content
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_name = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Source attribution: "Factiva" (sole collection source since v1.2)
    collector_source = Column(String(20), nullable=True, default="Factiva")

    # Classification results (populated by Azure OpenAI)
    # JSON array stored as string: ["Brokers", "Leadership", ...]
    roles = Column(Text, nullable=True)  # JSON array of role strings
    priority = Column(String(20), nullable=True)  # Critical, High, Medium, Monitor
    summary = Column(Text, nullable=True)  # AI-generated summary
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral

    # Phase 3: Advanced classification fields
    entities = Column(Text, nullable=True)  # JSON array of {name, type, context} objects
    impact_level = Column(String(20), nullable=True)  # Critical, High, Medium, Low
    category = Column(String(50), nullable=True)  # M&A, Regulatory, Loss Event, etc.
    region = Column(String(50), nullable=True)  # North America, Europe, etc.
    business_line = Column(String(50), nullable=True)  # Property, Casualty, etc.

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("Run", back_populates="articles")

    def __repr__(self) -> str:
        return f"<NewsArticle(id={self.id}, title='{self.title[:50]}...')>"
