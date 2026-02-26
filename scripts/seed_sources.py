#!/usr/bin/env python3
"""
Seed database with test news sources for MDInsights.

NOTE: These sources are HISTORICAL and no longer used by the pipeline.
      As of Phase 15 (v1.2), MDInsights uses Factiva as the sole news source.
      This script is kept for reference and potential future multi-source support.

This script inserts initial source configurations into the database,
checking for existing records to ensure idempotency.

Usage:
    python scripts/seed_sources.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal, engine, Base
from app.models import Source, SourceType
import structlog

logger = structlog.get_logger()


def seed_sources():
    """Seed database with test sources."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Define sources to seed
        sources_data = [
            # Core Apify sources (Phase 1-2)
            {
                "name": "Reinsurance News",
                "url": "https://www.reinsurancene.ws/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "Insurance Journal",
                "url": "https://www.insurancejournal.com/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "Business Insurance",
                "url": "https://www.businessinsurance.com/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "Artemis",
                "url": "https://www.artemis.bm/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "Lloyd's List",
                "url": "https://www.lloydslist.com/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            # RSS sources
            {
                "name": "Bloomberg",
                "url": "https://feeds.bloomberg.com/markets/news.rss",
                "source_type": SourceType.RSS,
                "actor_id": None,
                "enabled": True
            },
            {
                "name": "Reuters",
                "url": "https://www.reutersagency.com/feed/",
                "source_type": SourceType.RSS,
                "actor_id": None,
                "enabled": True
            },
            {
                "name": "S&P Global",
                "url": "https://www.spglobal.com/ratings/en/rss",
                "source_type": SourceType.RSS,
                "actor_id": None,
                "enabled": True
            },
            {
                "name": "AM Best",
                "url": "https://news.ambest.com/rss/RssNewsFeed.aspx",
                "source_type": SourceType.RSS,
                "actor_id": None,
                "enabled": True
            },
            # Additional Apify sources
            {
                "name": "Insurance Business UK",
                "url": "https://www.insurancebusinessmag.com/uk/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "The Insurer",
                "url": "https://www.theinsurer.com/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "GlobeNewsWire",
                "url": "https://www.globenewswire.com/news-release/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "Verisk",
                "url": "https://www.verisk.com/newsroom/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "APCIA",
                "url": "https://www.apci.org/media/news-releases/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "Gallagher Re",
                "url": "https://www.ajg.com/gallagherre/news/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "Mapfre",
                "url": "https://www.mapfre.com/en/press/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "Research and Markets",
                "url": "https://www.researchandmarkets.com/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            {
                "name": "KCC",
                "url": "https://www.kaplancomplianceandconsulting.com/news/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
            },
            # Disabled sources (not ready for production)
            {
                "name": "Moody's",
                "url": "https://www.moodys.com/newsandevents",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": False
            },
            {
                "name": "Fitch Ratings",
                "url": "https://www.fitchratings.com/research",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": False
            }
        ]

        sources_created = 0
        sources_skipped = 0

        for source_data in sources_data:
            # Check if source already exists
            existing = db.query(Source).filter(
                Source.name == source_data["name"]
            ).first()

            if existing:
                logger.info(
                    "source_exists",
                    source_name=source_data["name"],
                    source_id=existing.id
                )
                sources_skipped += 1
                continue

            # Create new source
            source = Source(**source_data)
            db.add(source)
            sources_created += 1
            logger.info("source_created", source_name=source_data["name"])

        # Commit all changes
        db.commit()

        logger.info(
            "seeding_completed",
            created=sources_created,
            skipped=sources_skipped
        )

        print(f"\nSeeding completed:")
        print(f"   - Created: {sources_created}")
        print(f"   - Skipped (already exists): {sources_skipped}")

    except Exception as e:
        db.rollback()
        logger.error("seeding_failed", error=str(e), exc_info=True)
        print(f"\nSeeding failed: {e}")
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding news sources...")
    seed_sources()
