"""
FactivaCollector — Dow Jones Factiva API client for MDInsights.

Queries the MMC Core API Factiva endpoint to retrieve recent insurance/reinsurance
news articles. Used by the Phase 10-02 pipeline integration as the primary news
source, with Apify/RSS as fallback.

API contracts:
    Search:  GET {base_url}/coreapi/recent-news/v1/search
             Headers: X-Api-Key: {key}
             Returns: articles list with metadata + pagination links

    Article: GET {base_url}/coreapi/recent-news/v1/article/{articleId}
             Headers: X-Api-Key: {key}
             Returns: full article with plaintext body

Authentication:
    X-Api-Key header only — no JWT/Bearer needed for news or equity endpoints.
    Credentials read from Settings (mmc_api_base_url, mmc_api_key).

Error handling:
    - Individual article fetch failures fall back to snippet from search result
    - Search failures propagate to caller (pipeline handles fallback to Apify)
    - All outcomes recorded as ApiEvent(type=NEWS_FETCH) for dashboard visibility
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.database import SessionLocal
from app.models.api_event import ApiEvent, ApiEventType


class FactivaCollector:
    """
    Factiva API client for MDInsights news collection.

    Queries the MMC Core API Factiva search endpoint, fetches individual article
    bodies for plaintext content, and normalizes results to the standard article
    dict schema consumed by the pipeline classifier and DB persistence layer.

    Usage:
        collector = FactivaCollector()
        if collector.is_configured():
            articles = collector.collect(query_params)

    Query parameters (from FactivaConfig row):
        industry_codes  - Comma-separated Factiva industry codes (e.g. "i82,i832")
        company_codes   - Comma-separated company codes (e.g. "MM")
        keywords        - Comma-separated search terms (e.g. "insurance reinsurance")
        page_size       - Articles per page (default 25, max 100)

    Normalized article dict schema (compatible with pipeline persistence):
        title           - Article headline
        description     - Full plaintext body, or snippet if body unavailable
        url             - Canonical article URL
        published_at    - datetime object (UTC)
        source_name     - "Factiva"
        collector_source - "Factiva" (for news_articles.collector_source field)
    """

    BASE_SEARCH_PATH = "/coreapi/recent-news/v1/search"
    BASE_ARTICLE_PATH = "/coreapi/recent-news/v1/article"
    SOURCE_LABEL = "Factiva"
    MAX_ARTICLES = 100  # Hard cap to avoid excessive API calls per run

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url: str = settings.mmc_api_base_url.rstrip("/")
        self.api_key: str = settings.mmc_api_key
        self.logger = structlog.get_logger(__name__).bind(service="factiva_collector")

    def is_configured(self) -> bool:
        """Return True if base_url and api_key are both present in Settings."""
        return bool(self.base_url and self.api_key)

    def collect(
        self,
        query_params: Dict[str, Any],
        run_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Collect articles from Factiva for the past 24 hours.

        Builds a search query from query_params, fetches search results, then
        fetches individual article bodies for plaintext content. Normalizes all
        results to the standard article dict schema.

        Args:
            query_params: Dict with keys: industry_codes, company_codes, keywords,
                          page_size. Values are comma-separated strings.
            run_id: Optional pipeline run ID for event attribution.

        Returns:
            List of normalized article dicts. May be empty if no results found.

        Raises:
            Exception: If the search request itself fails after retries. The caller
                       (pipeline) is responsible for handling the fallback to Apify.
        """
        # Build date window: yesterday to today (UTC)
        today = datetime.now(timezone.utc)
        yesterday = today - timedelta(days=1)
        from_date = yesterday.strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")

        # Parse comma-separated codes to lists for query building
        industry_codes_raw = query_params.get("industry_codes", "i82,i832")
        company_codes_raw = query_params.get("company_codes", "MM")
        keywords_raw = query_params.get("keywords", "insurance reinsurance")
        page_size = int(query_params.get("page_size", 25))

        # Build search query params
        params = {
            "fromDate": from_date,
            "toDate": to_date,
            "sortBy": "date",
            "sortOrder": "desc",
            "deduplication": "similar",
            "pageSize": min(page_size, self.MAX_ARTICLES),
        }

        # Add industry codes if provided
        industry_codes = [c.strip() for c in industry_codes_raw.split(",") if c.strip()]
        if industry_codes:
            params["industryCodes"] = ",".join(industry_codes)

        # Add company codes if provided
        company_codes = [c.strip() for c in company_codes_raw.split(",") if c.strip()]
        if company_codes:
            params["companyCodes"] = ",".join(company_codes)

        # Add keywords if provided
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        if keywords:
            params["keywords"] = " ".join(keywords)

        self.logger.info(
            "factiva_search_started",
            from_date=from_date,
            to_date=to_date,
            industry_codes=industry_codes,
            page_size=params["pageSize"],
        )

        try:
            search_response = self._search(params)
        except Exception as exc:
            self.logger.error(
                "factiva_search_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            self._record_event(
                event_type=ApiEventType.NEWS_FETCH,
                success=False,
                detail=json.dumps({
                    "error": type(exc).__name__,
                    "message": str(exc)[:200],
                    "phase": "search",
                }),
                run_id=run_id,
            )
            raise

        # Extract article list — handle both "data" and "articles" response keys
        articles_raw = (
            search_response.get("data")
            or search_response.get("articles")
            or []
        )

        # If pagination offers a pageSize100 link and we have fewer than 100 results,
        # follow it to get up to 100 articles in one call
        pagination = search_response.get("pagination", {})
        links = pagination.get("links", {})
        page_size_100_url = links.get("pageSize100")
        if page_size_100_url and len(articles_raw) < self.MAX_ARTICLES:
            try:
                self.logger.info("factiva_following_pagesize100_link")
                full_response = self._search_by_url(page_size_100_url)
                articles_raw = (
                    full_response.get("data")
                    or full_response.get("articles")
                    or articles_raw
                )
            except Exception as exc:
                self.logger.warning(
                    "factiva_pagesize100_follow_failed",
                    error=str(exc),
                    message="Continuing with initial result set",
                )

        # Apply hard cap
        articles_raw = articles_raw[: self.MAX_ARTICLES]

        self.logger.info(
            "factiva_search_returned",
            article_count=len(articles_raw),
        )

        # Fetch individual article bodies and normalize
        normalized_articles: List[Dict[str, Any]] = []
        for item in articles_raw:
            article_id = item.get("articleId") or item.get("id") or ""
            article_body: Dict[str, Any] = {}

            if article_id:
                try:
                    article_body = self._fetch_article(str(article_id))
                except Exception as exc:
                    self.logger.warning(
                        "factiva_article_fetch_failed",
                        article_id=article_id,
                        error_type=type(exc).__name__,
                        error=str(exc),
                        message="Falling back to search snippet",
                    )
                    # article_body stays as empty dict — normalizer uses snippet fallback

            normalized = self._normalize_article(item, article_body)
            normalized_articles.append(normalized)

        self.logger.info(
            "factiva_collection_complete",
            articles_collected=len(normalized_articles),
            run_id=run_id,
        )

        self._record_event(
            event_type=ApiEventType.NEWS_FETCH,
            success=True,
            detail=json.dumps({
                "articles_collected": len(normalized_articles),
                "from_date": from_date,
                "to_date": to_date,
            }),
            run_id=run_id,
        )

        return normalized_articles

    def _build_headers(self) -> Dict[str, str]:
        """
        Build request headers for Factiva API calls.

        Uses X-Api-Key authentication only — no JWT/Bearer token required
        for news and equity endpoints.
        """
        return {
            "X-Api-Key": self.api_key,
            "Accept": "application/json",
        }

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Factiva search API call.

        Args:
            params: Query parameters for the search endpoint.

        Returns:
            Parsed JSON response dict.

        Raises:
            httpx.HTTPStatusError: On non-2xx responses (after raise_for_status).
            httpx.TimeoutException: On request timeout (triggers tenacity retry).
            httpx.ConnectError: On connection failure (triggers tenacity retry).
        """
        url = f"{self.base_url}{self.BASE_SEARCH_PATH}"
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params, headers=self._build_headers())
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    def _search_by_url(self, url: str) -> Dict[str, Any]:
        """
        Execute a Factiva search using an opaque pagination URL.

        Used to follow pageSize100 links from the initial search response.

        Args:
            url: Full URL (may include base URL) returned by Factiva pagination.

        Returns:
            Parsed JSON response dict.
        """
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self._build_headers())
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    def _fetch_article(self, article_id: str) -> Dict[str, Any]:
        """
        Fetch full article body by article ID.

        Returns an empty dict on 4xx errors (article not found, access denied) so
        the collector can fall back to the search snippet rather than crashing.

        Args:
            article_id: Factiva article identifier from search result.

        Returns:
            Parsed JSON response dict with article details (plaintext, links, etc.).
            Returns empty dict for 4xx client errors.

        Raises:
            httpx.TimeoutException: On timeout (triggers tenacity retry).
            httpx.ConnectError: On connection failure (triggers tenacity retry).
            httpx.HTTPStatusError: On 5xx server errors after raise_for_status.
        """
        url = f"{self.base_url}{self.BASE_ARTICLE_PATH}/{article_id}"
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self._build_headers())

            # 4xx = article unavailable (not found, paywalled, access denied)
            # Log warning and return empty dict so caller uses snippet fallback
            if 400 <= response.status_code < 500:
                self.logger.warning(
                    "factiva_article_client_error",
                    article_id=article_id,
                    status_code=response.status_code,
                )
                return {}

            response.raise_for_status()
            return response.json()

    def _normalize_article(
        self,
        search_item: Dict[str, Any],
        article_body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize a Factiva API article to the standard MDInsights article dict schema.

        Maps Factiva-specific field names to the schema expected by the pipeline
        persistence layer (NewsArticle ORM model fields).

        Args:
            search_item: Article object from /search response.
            article_body: Full article object from /article/{id} response.
                          May be empty dict if the individual fetch failed.

        Returns:
            Dict with keys: title, description, url, published_at,
                            source_name, collector_source.
        """
        # Title from search result headline
        title = (search_item.get("headline") or "").strip()

        # Description: prefer full plaintext body, fall back to search snippet
        description = (
            article_body.get("plaintext")
            or search_item.get("snippet")
            or ""
        )

        # URL: prefer article-level self link, fall back to search-level self link
        article_links = article_body.get("links", {}) or {}
        search_links = search_item.get("links", {}) or {}
        url = (
            article_links.get("self")
            or search_links.get("self")
            or ""
        )

        # Published timestamp: convert epoch milliseconds to UTC datetime
        published_at: Optional[datetime] = None
        epoch_ms = search_item.get("publicationTimestampInMilliseconds")
        if epoch_ms is not None:
            try:
                published_at = datetime.fromtimestamp(
                    int(epoch_ms) / 1000.0,
                    tz=timezone.utc,
                ).replace(tzinfo=None)  # Store as naive UTC (consistent with other sources)
            except (ValueError, TypeError, OSError) as exc:
                self.logger.warning(
                    "factiva_timestamp_parse_failed",
                    epoch_ms=epoch_ms,
                    error=str(exc),
                )

        return {
            "title": title,
            "description": description,
            "url": url,
            "published_at": published_at,
            "source_name": self.SOURCE_LABEL,
            "collector_source": self.SOURCE_LABEL,
        }

    def _record_event(
        self,
        event_type: ApiEventType,
        success: bool,
        detail: Optional[str] = None,
        run_id: Optional[int] = None,
    ) -> None:
        """
        Record a news API event to the api_events table.

        Opens its own isolated DB session so event recording never interferes
        with caller's transaction context. Failures are swallowed — event recording
        must never crash the collection flow.

        Args:
            event_type: ApiEventType.NEWS_FETCH or ApiEventType.NEWS_FALLBACK
            success: True if the operation succeeded
            detail: JSON-safe string with event context (no secrets, max 500 chars)
            run_id: Optional pipeline run ID (None for out-of-pipeline calls)
        """
        try:
            with SessionLocal() as session:
                event = ApiEvent(
                    event_type=event_type,
                    api_name="news",
                    timestamp=datetime.utcnow(),
                    success=success,
                    detail=detail[:500] if detail else None,
                    run_id=run_id,
                )
                session.add(event)
                session.commit()
        except Exception as exc:
            # Never propagate DB errors into the collection flow
            self.logger.warning(
                "factiva_api_event_record_failed",
                event_type=event_type.value,
                error=str(exc),
            )
