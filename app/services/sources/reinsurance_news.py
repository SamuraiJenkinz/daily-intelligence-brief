"""
Reinsurance News scraper implementation.

Scrapes articles from https://www.reinsurancene.ws/ using Apify Web Scraper actor.
"""
from datetime import datetime
from typing import List, Dict, Any
import structlog

from app.services.sources.base import NewsSource

logger = structlog.get_logger()


class ReinsuranceNewsSource(NewsSource):
    """
    Scraper for Reinsurance News website.

    Uses Apify's web-scraper actor to extract article data from structured HTML.
    Target: https://www.reinsurancene.ws/

    CSS Selectors (based on typical news site structure):
    - Article containers: article, .post, .entry
    - Title: h2 a, h3 a, .entry-title
    - Description: .entry-content, .excerpt, p
    - URL: article a[href], h2 a[href]
    - Date: time, .published, .entry-date

    Note: Selectors should be validated against actual site structure.
    """

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape latest articles from Reinsurance News.

        Returns:
            List of article dictionaries matching standard schema.
            Empty list if scraping fails.
        """
        log = logger.bind(source="reinsurance_news", url=self.source_url)
        log.info("scraping_started")

        try:
            # Configure web scraper actor
            run_input = {
                "startUrls": [{"url": self.source_url}],
                "linkSelector": "article a[href], h2 a[href], h3 a[href]",
                "pageFunction": """
                    async function pageFunction(context) {
                        const { $, request } = context;

                        // Extract article data from page
                        const articles = [];

                        // Find all article containers
                        $('article, .post, .entry').each((index, element) => {
                            // Limit to first 20 articles
                            if (index >= 20) return false;

                            const $article = $(element);

                            // Extract title
                            const title = $article.find('h2, h3, .entry-title').first().text().trim();
                            if (!title) return; // Skip if no title

                            // Extract description
                            const description = $article.find('.entry-content, .excerpt, p').first().text().trim();

                            // Extract URL
                            const relativeUrl = $article.find('a').first().attr('href');
                            const url = relativeUrl ? new URL(relativeUrl, request.url).href : '';

                            // Extract date (fallback to current date if not found)
                            const dateText = $article.find('time, .published, .entry-date').first().attr('datetime')
                                          || $article.find('time, .published, .entry-date').first().text().trim();
                            let publishedAt = new Date();
                            if (dateText) {
                                const parsed = new Date(dateText);
                                if (!isNaN(parsed.getTime())) {
                                    publishedAt = parsed;
                                }
                            }

                            articles.push({
                                title: title,
                                description: description || '',
                                url: url,
                                published_at: publishedAt.toISOString(),
                                source_name: 'Reinsurance News'
                            });
                        });

                        return articles;
                    }
                """,
                "maxRequestsPerCrawl": 1,  # Only scrape homepage
                "maxConcurrency": 1,
                "proxyConfiguration": {
                    "useApifyProxy": True
                }
            }

            # Run the actor
            log.info("running_apify_actor", actor="apify/web-scraper")
            run = self.apify_client.actor("apify/web-scraper").call(run_input=run_input)

            # Get results from dataset
            articles = []
            for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                # Each item should be a list of articles from pageFunction
                if isinstance(item, list):
                    for article in item:
                        articles.append(self._normalize_article(article))
                elif isinstance(item, dict):
                    articles.append(self._normalize_article(item))

            log.info("scraping_completed", article_count=len(articles))
            return articles

        except Exception as e:
            log.error("scraping_failed", error=str(e), exc_info=True)
            # Return empty list - don't block pipeline
            return []

    def _normalize_article(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize scraped article data to standard schema.

        Args:
            raw_article: Raw article data from Apify

        Returns:
            Normalized article dictionary
        """
        # Parse published_at string to datetime
        published_at = None
        if raw_article.get("published_at"):
            try:
                published_at = datetime.fromisoformat(
                    raw_article["published_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                # Use current time as fallback
                published_at = datetime.utcnow()

        return {
            "title": raw_article.get("title", "").strip(),
            "description": raw_article.get("description", "").strip(),
            "url": raw_article.get("url", "").strip(),
            "published_at": published_at,
            "source_name": raw_article.get("source_name", "Reinsurance News")
        }
