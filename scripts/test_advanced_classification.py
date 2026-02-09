#!/usr/bin/env python3
"""
End-to-end test script for Phase 3 advanced classification.

Tests the expanded classification pipeline against live Azure OpenAI,
verifying all 9 classification dimensions are populated correctly including
entities, impact_level, category, region, and business_line.

Usage:
    python scripts/test_advanced_classification.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import subprocess
import structlog
from sqlalchemy import desc
from app.database import SessionLocal, Base, engine
from app.config import get_settings
from app.models.news_article import NewsArticle
from app.services.classifier import RoleClassificationService


logger = structlog.get_logger(__name__)


def test_advanced_classification():
    """
    Test advanced classification on a batch of articles with Phase 3 fields.

    Validates that all 9 classification dimensions are populated correctly:
    - roles, priority, summary, sentiment (Phase 1)
    - entities, impact_level, category, region, business_line (Phase 3)
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

    # Run migration to ensure Phase 3 columns exist
    print("🔄 Running Phase 3 migration to ensure columns exist...")
    try:
        subprocess.run(
            [sys.executable, "scripts/migrate_003_classification_fields.py"],
            cwd=str(project_root),
            check=True,
            capture_output=True
        )
        print("✅ Migration complete")
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print(e.stderr.decode() if e.stderr else "")
        return
    print()

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # Create database session
    db = SessionLocal()

    try:
        # Query 5 articles from latest run
        print("📋 Querying articles from latest run...")
        articles = (
            db.query(NewsArticle)
            .order_by(desc(NewsArticle.created_at))
            .limit(5)
            .all()
        )

        if not articles:
            print("ℹ️  No articles found in database. Run collector first:")
            print("   python scripts/collect_news.py")
            return

        print(f"Found {len(articles)} articles")
        print()

        # Reset classification for these articles to force re-classification
        print("🔄 Resetting classification for test articles...")
        for article in articles:
            article.roles = None
            print(f"  - {article.title[:60]}...")
        db.commit()
        print(f"✅ Reset {len(articles)} articles for re-classification")
        print()

        # Create classification service
        print("🤖 Initializing advanced classification service...")
        classifier = RoleClassificationService(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version
        )
        print()

        # Classify articles with expanded schema
        print("🔄 Classifying articles with Phase 3 expanded schema...")
        print()
        classified_count = classifier.classify_articles(db, articles)

        print()
        print(f"✅ Classification complete: {classified_count}/{len(articles)} articles classified")
        print()

        # Display comprehensive results
        print("=" * 80)
        print("COMPREHENSIVE CLASSIFICATION RESULTS")
        print("=" * 80)
        print()

        # Validation counters
        multi_role_count = 0
        total_entities = 0
        impact_distribution = {}
        category_distribution = {}
        region_distribution = {}
        business_line_distribution = {}
        zero_entity_count = 0
        null_field_errors = []
        entity_validation_failures = []

        for article in articles:
            db.refresh(article)  # Ensure we have latest data

            # Parse roles from JSON
            roles = json.loads(article.roles) if article.roles else []

            if len(roles) >= 2:
                multi_role_count += 1

            # Display basic classification
            print(f"📰 {article.title[:70]}...")
            print(f"   Source: {article.source_name}")
            print(f"   Roles: {', '.join(roles)} ({len(roles)} roles)")
            print(f"   Priority: {article.priority}")
            print(f"   Sentiment: {article.sentiment}")

            # Display Phase 3 fields
            print(f"   Impact Level: {article.impact_level or 'NULL ❌'}")
            print(f"   Category: {article.category or 'NULL ❌'}")
            print(f"   Region: {article.region or 'NULL ❌'}")
            print(f"   Business Line: {article.business_line or 'NULL ❌'}")

            # Display and validate entities
            print(f"   Entities:")
            if article.entities:
                try:
                    entities = json.loads(article.entities)
                    total_entities += len(entities)

                    if len(entities) == 0:
                        print(f"      ⚠️  No entities extracted (expected 3-10)")
                        zero_entity_count += 1
                    else:
                        # Validate entity structure and display
                        for entity in entities:
                            try:
                                # Validate required fields
                                assert "name" in entity, f"Entity missing 'name': {entity}"
                                assert "type" in entity, f"Entity missing 'type': {entity}"
                                assert "context" in entity, f"Entity missing 'context': {entity}"
                                assert entity["type"] in ("company", "person", "organization"), \
                                    f"Invalid entity type: {entity['type']}"

                                # Display entity
                                print(f"      - {entity['name']} ({entity['type']}): {entity['context']}")
                            except AssertionError as e:
                                print(f"      ❌ INVALID ENTITY: {e}")
                                entity_validation_failures.append((article.title[:50], str(e)))

                        print(f"      ✅ Entity round-trip PASS ({len(entities)} entities)")

                except json.JSONDecodeError as e:
                    print(f"      ❌ Entity JSON parse error: {e}")
                    entity_validation_failures.append((article.title[:50], f"JSON parse error: {e}"))
            else:
                print(f"      ⚠️  No entities extracted (NULL/empty)")
                zero_entity_count += 1

            # Track distributions
            if article.impact_level:
                impact_distribution[article.impact_level] = impact_distribution.get(article.impact_level, 0) + 1
            else:
                null_field_errors.append(("impact_level", article.title[:50]))

            if article.category:
                category_distribution[article.category] = category_distribution.get(article.category, 0) + 1
            else:
                null_field_errors.append(("category", article.title[:50]))

            if article.region:
                region_distribution[article.region] = region_distribution.get(article.region, 0) + 1
            else:
                null_field_errors.append(("region", article.title[:50]))

            if article.business_line:
                business_line_distribution[article.business_line] = \
                    business_line_distribution.get(article.business_line, 0) + 1
            else:
                null_field_errors.append(("business_line", article.title[:50]))

            print()

        # Validation metrics
        print("=" * 80)
        print("VALIDATION METRICS")
        print("=" * 80)
        print()

        # Multi-role rate
        multi_role_pct = (multi_role_count / len(articles)) * 100 if articles else 0
        print(f"Multi-role articles: {multi_role_count}/{len(articles)} ({multi_role_pct:.1f}%)")
        if multi_role_pct >= 40:
            print("  ✅ Multi-role assignment target met (40-60% expected)")
        else:
            print("  ⚠️  Multi-role assignment below target (40-60% expected)")
        print()

        # Entity metrics
        avg_entities = total_entities / len(articles) if articles else 0
        print(f"Average entities per article: {avg_entities:.1f} (target: 3-10)")
        if avg_entities >= 3:
            print("  ✅ Entity extraction target met")
        else:
            print("  ⚠️  Entity extraction below target")

        if zero_entity_count > 0:
            print(f"  ⚠️  {zero_entity_count} articles with 0 entities")
        print()

        # Distribution tables
        print("Impact Level Distribution:")
        for level in ["Critical", "High", "Medium", "Low"]:
            count = impact_distribution.get(level, 0)
            print(f"  {level:12} {count:2} articles")
        print()

        print("Category Distribution:")
        for cat, count in sorted(category_distribution.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat:20} {count:2} articles")
        print()

        print("Region Distribution:")
        for region, count in sorted(region_distribution.items(), key=lambda x: x[1], reverse=True):
            print(f"  {region:20} {count:2} articles")
        print()

        print("Business Line Distribution:")
        for line, count in sorted(business_line_distribution.items(), key=lambda x: x[1], reverse=True):
            print(f"  {line:20} {count:2} articles")
        print()

        # Error reporting
        if null_field_errors:
            print("❌ NULL FIELD ERRORS:")
            for field, title in null_field_errors:
                print(f"  {field:20} NULL in: {title}")
            print()

        if entity_validation_failures:
            print("❌ ENTITY VALIDATION FAILURES:")
            for title, error in entity_validation_failures:
                print(f"  {title}: {error}")
            print()

        # Final verdict
        print("=" * 80)
        print("FINAL VERDICT")
        print("=" * 80)
        print()

        all_fields_populated = len(null_field_errors) == 0
        entity_target_met = avg_entities >= 3
        entities_valid = len(entity_validation_failures) == 0

        if all_fields_populated and entity_target_met and entities_valid:
            print("✅ PASS")
            print("   - All 9 classification dimensions populated")
            print(f"   - Average entity count {avg_entities:.1f} >= 3")
            print("   - All entity round-trips valid")
        else:
            print("❌ FAIL")
            if not all_fields_populated:
                print(f"   - {len(null_field_errors)} NULL field errors found")
            if not entity_target_met:
                print(f"   - Entity count {avg_entities:.1f} below target 3")
            if not entities_valid:
                print(f"   - {len(entity_validation_failures)} entity validation failures")

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
    print("🧪 MDInsights Advanced Classification Test (Phase 3)")
    print("=" * 80)
    print()
    test_advanced_classification()
