"""
Article search service using SQLite FTS5 for fast full-text search.

Provides ranked full-text search with BM25 scoring and multi-filter support.
Gracefully falls back to LIKE queries if FTS5 table is not available.
"""
import structlog
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from datetime import date

from app.models import NewsArticle, Source

logger = structlog.get_logger(__name__)


class ArticleSearchService:
    """
    Article search service with FTS5 full-text search support.

    Provides:
    - Fast ranked full-text search using SQLite FTS5 with BM25 ranking
    - Multi-filter support (role, date range, priority, source)
    - Graceful fallback to LIKE queries if FTS5 unavailable
    - Filter option discovery for UI dropdowns
    """

    @staticmethod
    def _sanitize_fts_query(query: str) -> str:
        """
        Sanitize FTS5 query to prevent syntax errors.

        Escapes special FTS5 characters: " * [ ] { } ( ) ^ : + -

        Args:
            query: Raw search query from user

        Returns:
            Sanitized query safe for FTS5 MATCH
        """
        if not query:
            return query

        # Remove or escape FTS5 special characters
        # Keep simple: escape double quotes, remove operators
        query = query.replace('"', '""')  # Escape quotes
        query = query.replace('*', '')  # Remove wildcards
        query = query.replace('+', ' ')  # Convert to space
        query = query.replace('-', ' ')  # Convert to space
        query = query.replace(':', ' ')  # Convert to space
        query = query.replace('^', ' ')  # Convert to space

        # Wrap in quotes for phrase search (prevents syntax errors)
        query = query.strip()
        if query:
            query = f'"{query}"'

        return query

    @staticmethod
    def search(
        db: Session,
        query: Optional[str] = None,
        role: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        priority: Optional[str] = None,
        source_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[NewsArticle], int]:
        """
        Search articles with FTS5 full-text search and filters.

        Args:
            db: Database session
            query: Search query string (searches title, description, summary)
            role: Filter by role (Brokers, Leadership, etc.)
            date_from: Filter articles published on or after this date
            date_to: Filter articles published on or before this date
            priority: Filter by priority (Critical, High, Medium, Monitor)
            source_name: Filter by source name
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            Tuple of (articles list, total count)
        """
        try:
            if query and query.strip():
                # Use FTS5 for keyword search
                sanitized_query = ArticleSearchService._sanitize_fts_query(query)

                # FTS5 search with BM25 ranking
                # Join articles_fts with news_articles for ranking
                sql = text("""
                    SELECT
                        news_articles.*,
                        bm25(articles_fts) as rank
                    FROM news_articles
                    INNER JOIN articles_fts ON news_articles.id = articles_fts.rowid
                    WHERE articles_fts MATCH :query
                    ORDER BY rank
                """)

                # Execute FTS search
                result = db.execute(sql, {"query": sanitized_query})
                article_ids = [row[0] for row in result]  # Extract IDs

                if article_ids:
                    # Get full articles ordered by rank
                    articles_query = db.query(NewsArticle).filter(
                        NewsArticle.id.in_(article_ids)
                    )
                else:
                    # No results
                    articles_query = db.query(NewsArticle).filter(NewsArticle.id == -1)

            else:
                # No keyword search - standard query
                articles_query = db.query(NewsArticle)

            # Apply filters
            filters = []

            if role:
                # JSON text field search - use LIKE
                filters.append(NewsArticle.roles.like(f'%"{role}"%'))

            if date_from:
                filters.append(NewsArticle.published_at >= date_from)

            if date_to:
                filters.append(NewsArticle.published_at <= date_to)

            if priority:
                filters.append(NewsArticle.priority == priority)

            if source_name:
                filters.append(NewsArticle.source_name == source_name)

            if filters:
                articles_query = articles_query.filter(and_(*filters))

            # Get total count
            total_count = articles_query.count()

            # Apply pagination and ordering
            if not (query and query.strip()):
                # If no FTS search, order by published date
                articles_query = articles_query.order_by(NewsArticle.published_at.desc())

            articles = articles_query.limit(limit).offset(offset).all()

            logger.info(
                "article_search",
                query=query,
                role=role,
                date_from=date_from,
                date_to=date_to,
                priority=priority,
                source_name=source_name,
                results=len(articles),
                total=total_count
            )

            return articles, total_count

        except Exception as e:
            # Fallback to LIKE query if FTS5 fails
            logger.warning("fts_search_failed_fallback", error=str(e))

            articles_query = db.query(NewsArticle)

            # Apply text search with LIKE
            if query and query.strip():
                search_pattern = f"%{query}%"
                articles_query = articles_query.filter(
                    or_(
                        NewsArticle.title.like(search_pattern),
                        NewsArticle.description.like(search_pattern),
                        NewsArticle.summary.like(search_pattern)
                    )
                )

            # Apply filters (same as above)
            filters = []

            if role:
                filters.append(NewsArticle.roles.like(f'%"{role}"%'))

            if date_from:
                filters.append(NewsArticle.published_at >= date_from)

            if date_to:
                filters.append(NewsArticle.published_at <= date_to)

            if priority:
                filters.append(NewsArticle.priority == priority)

            if source_name:
                filters.append(NewsArticle.source_name == source_name)

            if filters:
                articles_query = articles_query.filter(and_(*filters))

            # Get total count
            total_count = articles_query.count()

            # Apply pagination and ordering
            articles = (
                articles_query
                .order_by(NewsArticle.published_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            logger.info(
                "article_search_fallback",
                query=query,
                results=len(articles),
                total=total_count
            )

            return articles, total_count

    @staticmethod
    def get_filter_options(db: Session) -> Dict[str, List[str]]:
        """
        Get available filter options for search UI.

        Returns distinct values for roles, priorities, and sources
        to populate dropdown filters.

        Args:
            db: Database session

        Returns:
            Dict with keys: roles, priorities, sources
        """
        # Get distinct roles (parse JSON array)
        # Use raw SQL to extract unique roles from JSON arrays
        roles_result = db.execute(text("""
            SELECT DISTINCT roles FROM news_articles
            WHERE roles IS NOT NULL
        """))

        roles = set()
        for row in roles_result:
            if row[0]:
                # Parse JSON array string
                import json
                try:
                    role_list = json.loads(row[0])
                    if isinstance(role_list, list):
                        roles.update(role_list)
                except (json.JSONDecodeError, TypeError):
                    pass

        # Get distinct priorities
        priorities_result = db.query(NewsArticle.priority).distinct().filter(
            NewsArticle.priority.isnot(None)
        ).all()
        priorities = sorted([p[0] for p in priorities_result if p[0]])

        # Get distinct sources
        sources_result = db.query(NewsArticle.source_name).distinct().filter(
            NewsArticle.source_name.isnot(None)
        ).all()
        sources = sorted([s[0] for s in sources_result if s[0]])

        return {
            "roles": sorted(list(roles)),
            "priorities": priorities,
            "sources": sources
        }
