#!/usr/bin/env python3
"""
Seed database with test news sources for MDInsights.

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
            {
                "name": "Reinsurance News",
                "url": "https://www.reinsurancene.ws/",
                "source_type": SourceType.APIFY,
                "actor_id": "apify/web-scraper",
                "enabled": True
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

        print(f"\n✅ Seeding completed:")
        print(f"   - Created: {sources_created}")
        print(f"   - Skipped (already exists): {sources_skipped}")

    except Exception as e:
        db.rollback()
        logger.error("seeding_failed", error=str(e), exc_info=True)
        print(f"\n❌ Seeding failed: {e}")
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding news sources...")
    seed_sources()
