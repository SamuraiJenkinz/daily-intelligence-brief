"""
News source interface module.

Contains abstract base class for news source scrapers.
Concrete Apify/RSS implementations removed in Phase 15 (v1.2)
when pipeline switched to Factiva-only collection.
"""
from app.services.sources.base import NewsSource

__all__ = ["NewsSource"]
