#!/usr/bin/env python3
"""
Test collection script for MDInsights.

Tests the ApifyCollector service without running the full pipeline.
Validates that articles are properly scraped and stored in the database.

Usage:
    python scripts/test_collection.py

Requirements:
    - .env file with APIFY_TOKEN configured
    - Database seeded with test sources (run seed_sources.py first)
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from app.database import SessionLocal, engine, Base
from app.models import NewsArticle, Run, RunStatus
from app.services.collector import ApifyCollector
import structlog

logger = structlog.get_logger()


def test_collection():
    """Test news collection from enabled sources."""
    print("\n🧪 Testing news collection...")

    # Load settings
    settings = get_settings()

    # Verify Apify is configured
    if not settings.is_apify_configured():
        print("\n❌ Error: APIFY_TOKEN not configured in .env")
        print("   Please add your Apify token to .env file")
        sys.exit(1)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    try:
        # Create collector instance
        collector = ApifyCollector(settings.apify_token)

        # Run collection
        print("\n📰 Starting collection from enabled sources...")
        article_count = collector.collect_from_sources()

        print(f"\n✅ Collection completed: {article_count} articles collected")

        # Validate articles in database
        db = SessionLocal()
        try:
            # Get the most recent run
            latest_run = db.query(Run).order_by(Run.id.desc()).first()

            if not latest_run:
                print("\n⚠️  Warning: No run record found in database")
                return

            print(f"\n📊 Run Details:")
            print(f"   - Run ID: {latest_run.id}")
            print(f"   - Status: {latest_run.status.value}")
            print(f"   - Started: {latest_run.started_at}")
            print(f"   - Completed: {latest_run.completed_at}")
            print(f"   - Articles Collected: {latest_run.articles_collected}")

            if latest_run.error_message:
                print(f"   - Error: {latest_run.error_message}")

            # Get articles from this run
            articles = db.query(NewsArticle).filter(
                NewsArticle.run_id == latest_run.id
            ).limit(5).all()

            if articles:
                print(f"\n📝 Sample Articles (showing first 5):")
                for i, article in enumerate(articles, 1):
                    print(f"\n   {i}. {article.title[:80]}...")
                    print(f"      Source: {article.source_name}")
                    print(f"      URL: {article.source_url}")
                    print(f"      Published: {article.published_at}")
                    print(f"      Has Description: {'Yes' if article.description else 'No'}")
                    print(f"      Classification Status: {'Not classified (NULL)' if not article.roles else 'Classified'}")

            # Verify classification fields are NULL
            classified_count = db.query(NewsArticle).filter(
                NewsArticle.run_id == latest_run.id,
                NewsArticle.roles.isnot(None)
            ).count()

            if classified_count > 0:
                print(f"\n⚠️  Warning: {classified_count} articles already classified (expected all NULL)")
            else:
                print(f"\n✅ Validation passed: All classification fields are NULL (as expected)")

            # Summary statistics
            total_articles = db.query(NewsArticle).count()
            total_runs = db.query(Run).count()

            print(f"\n📈 Database Summary:")
            print(f"   - Total Runs: {total_runs}")
            print(f"   - Total Articles: {total_articles}")

        finally:
            db.close()

    except Exception as e:
        logger.error("test_collection_failed", error=str(e), exc_info=True)
        print(f"\n❌ Collection test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_collection()
