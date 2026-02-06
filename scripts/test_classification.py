"""
Test script for article classification.

Tests Azure OpenAI classification on collected articles to validate
multi-role assignment and classification quality.

Usage:
    python scripts/test_classification.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from sqlalchemy import desc
from app.database import SessionLocal, init_db
from app.config import get_settings
from app.models.news_article import NewsArticle
from app.services.classifier import RoleClassificationService


logger = structlog.get_logger(__name__)


def test_classification():
    """
    Test classification on a small batch of unclassified articles.

    Queries database for unclassified articles from latest run,
    runs classification, and validates multi-role assignment.
    """
    # Load settings
    settings = get_settings()

    # Validate Azure OpenAI configuration
    if not settings.is_azure_openai_configured():
        print("❌ Azure OpenAI not configured. Please set environment variables:")
        print("   - AZURE_OPENAI_ENDPOINT")
        print("   - AZURE_OPENAI_API_KEY")
        print("   - AZURE_OPENAI_DEPLOYMENT")
        return

    print(f"✅ Azure OpenAI configured: {settings.azure_openai_deployment}")
    print()

    # Initialize database
    init_db()

    # Create database session
    db = SessionLocal()

    try:
        # Query unclassified articles from latest run (limit to 5 for testing)
        print("📋 Querying unclassified articles...")
        unclassified_articles = (
            db.query(NewsArticle)
            .filter(NewsArticle.roles.is_(None))
            .order_by(desc(NewsArticle.created_at))
            .limit(5)
            .all()
        )

        if not unclassified_articles:
            print("ℹ️  No unclassified articles found. Run collector first:")
            print("   python scripts/collect_news.py")
            return

        print(f"Found {len(unclassified_articles)} unclassified articles")
        print()

        # Create classification service
        print("🤖 Initializing classification service...")
        classifier = RoleClassificationService(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version
        )
        print()

        # Classify articles
        print("🔄 Classifying articles...")
        print()
        classified_count = classifier.classify_articles(db, unclassified_articles)

        print()
        print(f"✅ Classification complete: {classified_count}/{len(unclassified_articles)} articles classified")
        print()

        # Display results
        print("=" * 80)
        print("CLASSIFICATION RESULTS")
        print("=" * 80)
        print()

        # Refresh articles to get updated data
        db.refresh(unclassified_articles[0])  # Force reload from DB

        multi_role_count = 0
        for article in unclassified_articles:
            db.refresh(article)  # Ensure we have latest data

            # Parse roles from JSON
            import json
            roles = json.loads(article.roles) if article.roles else []

            if len(roles) >= 2:
                multi_role_count += 1

            print(f"📰 {article.title[:70]}...")
            print(f"   Source: {article.source_name}")
            print(f"   Roles: {', '.join(roles)} ({len(roles)} roles)")
            print(f"   Priority: {article.priority}")
            print(f"   Sentiment: {article.sentiment}")
            print(f"   Summary: {article.summary[:100]}...")
            print()

        print("=" * 80)
        print("VALIDATION METRICS")
        print("=" * 80)
        print()

        multi_role_pct = (multi_role_count / len(unclassified_articles)) * 100 if unclassified_articles else 0
        print(f"Multi-role articles: {multi_role_count}/{len(unclassified_articles)} ({multi_role_pct:.1f}%)")

        if multi_role_pct >= 40:
            print("✅ Multi-role assignment target met (40-60% expected)")
        else:
            print("⚠️  Multi-role assignment below target (40-60% expected)")

        print()
        print("Test complete! ✨")

    except Exception as e:
        logger.error("test_failed", error=str(e))
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print()
    print("🧪 MDInsights Classification Test")
    print("=" * 80)
    print()
    test_classification()
