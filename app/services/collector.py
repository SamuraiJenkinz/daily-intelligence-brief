"""
Apify-based news collection service for MDInsights.

Orchestrates scraping from multiple enabled sources, stores raw articles
in database for subsequent classification.
"""
from datetime import datetime
from typing import List, Dict, Any
from apify_client import ApifyClient
import structlog

from app.database import SessionLocal
from app.models import NewsArticle, Source, Run, RunStatus, SourceType
from app.services.sources import (
    NewsSource,
    ReinsuranceNewsSource,
    InsuranceJournalSource,
    BusinessInsuranceSource,
    ArtemisSource,
    LloydsListSource
)

logger = structlog.get_logger()


class ApifyCollector:
    """
    Orchestrates news collection from Apify-based sources.

    Manages the complete collection workflow:
    1. Query enabled sources from database
    2. Instantiate appropriate source scrapers
    3. Execute scraping with error handling
    4. Store raw articles in database
    5. Track run metadata and status
    """

    def __init__(self, apify_token: str):
        """
        Initialize collector with Apify credentials.

        Args:
            apify_token: Apify API token for authentication
        """
        self.apify_client = ApifyClient(apify_token)
        self.logger = logger.bind(service="collector")

    def collect_from_sources(self) -> int:
        """
        Collect articles from all enabled sources.

        Returns:
            Number of articles collected

        Raises:
            Exception: If critical collection error occurs
        """
        db = SessionLocal()
        run = None

        try:
            # Create run record
            run = Run(status=RunStatus.RUNNING)
            db.add(run)
            db.commit()
            db.refresh(run)

            self.logger.info("collection_started", run_id=run.id)

            # Query enabled sources
            sources = db.query(Source).filter(Source.enabled == True).all()

            if not sources:
                self.logger.warning("no_enabled_sources")
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.utcnow()
                db.commit()
                return 0

            total_articles = 0

            for source in sources:
                try:
                    articles = self._scrape_source(source)
                    if articles:
                        self._store_articles(db, run.id, articles)
                        total_articles += len(articles)
                        self.logger.info(
                            "source_scraped",
                            source_name=source.name,
                            article_count=len(articles)
                        )
                    else:
                        self.logger.warning(
                            "no_articles_found",
                            source_name=source.name
                        )

                except Exception as e:
                    self.logger.error(
                        "source_scrape_failed",
                        source_name=source.name,
                        error=str(e),
                        exc_info=True
                    )
                    # Continue with next source - don't block pipeline
                    continue

            # Update run status
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.articles_collected = total_articles
            db.commit()

            self.logger.info(
                "collection_completed",
                run_id=run.id,
                total_articles=total_articles
            )

            return total_articles

        except Exception as e:
            self.logger.error("collection_failed", error=str(e), exc_info=True)

            if run:
                run.status = RunStatus.FAILED
                run.completed_at = datetime.utcnow()
                run.error_message = str(e)
                db.commit()

            raise

        finally:
            db.close()

    def _scrape_source(self, source: Source) -> List[Dict[str, Any]]:
        """
        Scrape articles from a single source.

        Args:
            source: Source ORM instance

        Returns:
            List of article dictionaries
        """
        # Instantiate appropriate source class based on source configuration
        scraper = self._get_source_scraper(source)

        if not scraper:
            self.logger.warning(
                "no_scraper_for_source",
                source_name=source.name,
                source_type=source.source_type
            )
            return []

        return scraper.scrape()

    def _get_source_scraper(self, source: Source) -> NewsSource:
        """
        Get appropriate scraper instance for source.

        Args:
            source: Source ORM instance

        Returns:
            NewsSource implementation or None
        """
        # Map source names to scraper classes
        source_map = {
            "Reinsurance News": ReinsuranceNewsSource,
            "Insurance Journal": InsuranceJournalSource,
            "Business Insurance": BusinessInsuranceSource,
            "Artemis": ArtemisSource,
            "Lloyd's List": LloydsListSource
        }

        scraper_class = source_map.get(source.name)

        if not scraper_class:
            return None

        return scraper_class(self.apify_client, source.url)

    def _store_articles(
        self,
        db: SessionLocal,
        run_id: int,
        articles: List[Dict[str, Any]]
    ) -> None:
        """
        Store scraped articles in database.

        Args:
            db: Database session
            run_id: ID of current run
            articles: List of article dictionaries
        """
        try:
            for article_data in articles:
                article = NewsArticle(
                    run_id=run_id,
                    title=article_data["title"],
                    description=article_data.get("description"),
                    source_url=article_data.get("url"),
                    source_name=article_data["source_name"],
                    published_at=article_data.get("published_at"),
                    # Classification fields remain NULL until 01-03
                    roles=None,
                    priority=None,
                    summary=None,
                    sentiment=None
                )
                db.add(article)

            # Commit all articles in single transaction
            db.commit()

            self.logger.info(
                "articles_stored",
                run_id=run_id,
                count=len(articles)
            )

        except Exception as e:
            db.rollback()
            self.logger.error(
                "article_storage_failed",
                run_id=run_id,
                error=str(e),
                exc_info=True
            )
            raise
