#!/usr/bin/env python3
"""
Test collection script for MDInsights.

Tests the FactivaCollector service without running the full pipeline.
Validates that articles are properly fetched and stored in the database.

Usage:
    python scripts/test_collection.py

Requirements:
    - .env file with MMC_API_BASE_URL and MMC_API_KEY configured
    - Database with factiva_config table seeded
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from app.database import SessionLocal, engine, Base
from app.models import NewsArticle, Run, RunStatus, FactivaConfig
from app.collectors.factiva import FactivaCollector
import structlog

logger = structlog.get_logger()


def test_collection():
    """Test news collection from Factiva."""
    print("\n🧪 Testing Factiva news collection...")

    # Load settings
    settings = get_settings()

    # Verify Factiva is configured
    factiva_collector = FactivaCollector()
    if not factiva_collector.is_configured():
        print("\n❌ Error: MMC API key not configured for Factiva")
        print("   Please add MMC_API_BASE_URL and MMC_API_KEY to .env file")
        sys.exit(1)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    try:
        # Load query params from database config
        db = SessionLocal()
        try:
            factiva_config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
            if not factiva_config or not factiva_config.enabled:
                print("\n⚠️  Warning: Factiva disabled in admin dashboard")
                print("   Enable Factiva in the admin panel and configure query parameters")
                sys.exit(1)

            query_params = {
                "industry_codes": factiva_config.industry_codes or "",
                "company_codes": factiva_config.company_codes or "",
                "keywords": factiva_config.keywords or "",
                "page_size": factiva_config.page_size or 25,
                "date_range_hours": factiva_config.date_range_hours or 48,
            }

            print("\n📋 Factiva Query Parameters:")
            print(f"   - Industry Codes: {query_params['industry_codes'][:50]}...")
            print(f"   - Company Codes: {query_params['company_codes'][:50] if query_params['company_codes'] else 'None'}...")
            print(f"   - Keywords: {query_params['keywords'][:50] if query_params['keywords'] else 'None'}...")
            print(f"   - Page Size: {query_params['page_size']}")
            print(f"   - Date Range: {query_params['date_range_hours']} hours")

            # Run collection
            print("\n📰 Starting collection from Factiva API...")
            factiva_articles = factiva_collector.collect(query_params)

            article_count = len(factiva_articles)
            print(f"\n✅ Collection completed: {article_count} articles fetched")

            # Store articles (create Run record)
            run = Run(status=RunStatus.RUNNING, articles_collected=article_count)
            db.add(run)
            db.commit()
            db.refresh(run)

            for article_data in factiva_articles:
                article = NewsArticle(
                    run_id=run.id,
                    title=article_data["title"],
                    description=article_data.get("description"),
                    source_url=article_data.get("url"),
                    source_name=article_data["source_name"],
                    published_at=article_data.get("published_at"),
                    collector_source=article_data.get("collector_source", "Factiva"),
                )
                db.add(article)

            run.status = RunStatus.COMPLETED
            db.commit()

            print(f"\n📊 Run Details:")
            print(f"   - Run ID: {run.id}")
            print(f"   - Status: {run.status.value}")
            print(f"   - Started: {run.started_at}")
            print(f"   - Completed: {run.completed_at}")
            print(f"   - Articles Collected: {run.articles_collected}")

            if run.error_message:
                print(f"   - Error: {run.error_message}")

            # Get articles from this run
            articles = db.query(NewsArticle).filter(
                NewsArticle.run_id == run.id
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
                NewsArticle.run_id == run.id,
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
