"""
Generic RSS/Atom feed scraper implementation.

Provides a reusable source class for any standard RSS or Atom feed.
Handles feed parsing, date normalization, and error recovery.
"""
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import structlog
import feedparser

from app.services.sources.base import NewsSource

logger = structlog.get_logger()


class RSSSource(NewsSource):
    """
    Generic RSS/Atom feed scraper.

    Works with any standard RSS 2.0 or Atom feed URL. Normalizes feed entries
    to standard article schema with consistent date handling and error recovery.

    Args:
        apify_client: ApifyClient instance (unused but required by ABC)
        source_url: RSS/Atom feed URL
        source_name: Optional custom name for this source (defaults to feed title)

    Example:
        >>> source = RSSSource(client, "https://example.com/feed.xml", "Example News")
        >>> articles = source.scrape()
    """

    def __init__(self, apify_client, source_url: str, source_name: Optional[str] = None):
        """
        Initialize RSS feed scraper.

        Args:
            apify_client: ApifyClient instance (unused but required by ABC)
            source_url: RSS/Atom feed URL to parse
            source_name: Optional custom source name (defaults to feed title)
        """
        super().__init__(apify_client, source_url)
        self.source_name = source_name

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape articles from RSS/Atom feed.

        Parses feed entries and normalizes to standard article schema.
        Handles malformed feeds gracefully (logs warning, continues if entries exist).
        Falls back through multiple date fields to find publication date.

        Returns:
            List of article dictionaries matching standard schema.
            Empty list if feed fetch fails or parsing errors occur.
        """
        log = logger.bind(source="rss", url=self.source_url)
        log.info("scraping_rss_feed_started")

        try:
            # Parse RSS/Atom feed
            feed = feedparser.parse(self.source_url)

            # Check for malformed feed (bozo flag)
            if feed.bozo:
                bozo_exception = getattr(feed, 'bozo_exception', None)
                log.warning(
                    "feed_malformed_but_continuing",
                    bozo_exception=str(bozo_exception) if bozo_exception else "Unknown"
                )
                # If no entries despite malformed flag, return empty
                if not feed.entries:
                    log.warning("feed_malformed_no_entries")
                    return []

            # Get source name from feed if not provided
            default_source_name = feed.feed.get('title', 'RSS Feed')
            source_name = self.source_name or default_source_name

            # Process entries (limit to 20)
            articles = []
            for entry in feed.entries[:20]:
                article = self._normalize_entry(entry, source_name)
                if article:  # Skip entries that failed normalization
                    articles.append(article)

            log.info("scraping_rss_feed_completed", article_count=len(articles), source=source_name)
            return articles

        except Exception as e:
            log.error("scraping_rss_feed_failed", error=str(e), exc_info=True)
            return []

    def _normalize_entry(self, entry: Any, source_name: str) -> Optional[Dict[str, Any]]:
        """
        Normalize RSS/Atom entry to standard article schema.

        Args:
            entry: feedparser entry object
            source_name: Source identifier for this article

        Returns:
            Normalized article dictionary or None if title is missing
        """
        # Extract and validate title (required)
        title = entry.get('title', '').strip()
        if not title:
            return None  # Skip entries without title

        # Extract description (try summary first, fall back to description)
        raw_description = entry.get('summary', '') or entry.get('description', '')
        description = self._strip_html(raw_description).strip()

        # Extract URL
        url = entry.get('link', '').strip()

        # Extract published date (fall back through multiple fields)
        published_at = self._extract_date(entry)

        return {
            "title": title,
            "description": description,
            "url": url,
            "published_at": published_at,
            "source_name": source_name
        }

    def _extract_date(self, entry: Any) -> datetime:
        """
        Extract publication date from entry with fallback chain.

        Tries published_parsed → updated_parsed → created_parsed → current time.

        Args:
            entry: feedparser entry object

        Returns:
            datetime object (never None)
        """
        # Try published_parsed first
        time_struct = entry.get('published_parsed')
        if not time_struct:
            # Fall back to updated_parsed
            time_struct = entry.get('updated_parsed')
        if not time_struct:
            # Fall back to created_parsed
            time_struct = entry.get('created_parsed')

        # Convert time.struct_time to datetime
        if time_struct:
            try:
                # time_struct is a 9-tuple, take first 6 elements for datetime
                return datetime(*time_struct[:6])
            except (TypeError, ValueError):
                pass  # Fall through to current time

        # Final fallback: current time
        return datetime.utcnow()

    def _strip_html(self, text: str) -> str:
        """
        Remove HTML tags from text using simple regex.

        Args:
            text: Text potentially containing HTML tags

        Returns:
            Text with HTML tags removed
        """
        if not text:
            return ''
        # Remove HTML tags
        return re.sub(r'<[^>]+>', '', text)
