"""
Abstract base class for news source scrapers.

Defines standard interface for all source implementations to enable
multi-source expansion in Phase 2.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class NewsSource(ABC):
    """
    Abstract base class for news source scrapers.

    All source-specific scrapers must implement this interface to ensure
    consistent article data format and enable polymorphic usage in collector.

    Standard article schema:
        {
            "title": str,           # Article headline (required)
            "description": str,     # Article excerpt/summary (optional)
            "url": str,             # Article URL (optional)
            "published_at": datetime, # Publication date (optional)
            "source_name": str      # Source identifier (required)
        }
    """

    def __init__(self, apify_client, source_url: str):
        """
        Initialize source scraper.

        Args:
            apify_client: ApifyClient instance for API access
            source_url: Base URL of the news source
        """
        self.apify_client = apify_client
        self.source_url = source_url

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape articles from this source.

        Returns:
            List of article dictionaries matching standard schema.
            Returns empty list if scraping fails or no articles found.

        Raises:
            Exception: Only for critical errors that should halt pipeline.
                       Most errors should be logged and return empty list.
        """
        pass
