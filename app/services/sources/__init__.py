"""
News source scrapers module.

Contains abstract base class and concrete implementations for each
supported news source.
"""
from app.services.sources.base import NewsSource
from app.services.sources.reinsurance_news import ReinsuranceNewsSource

__all__ = ["NewsSource", "ReinsuranceNewsSource"]
