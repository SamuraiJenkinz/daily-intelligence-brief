"""
Standalone CLI script for testing audio generation.

Generates audio briefings from the most recent pipeline run's classified articles.
Enables manual testing and verification of audio quality without running the full pipeline.

Usage:
    python scripts/generate_audio.py --role brokers
    python scripts/generate_audio.py --role all
    python scripts/generate_audio.py --role brokers --date 2026-02-27
    python scripts/generate_audio.py --role brokers --force
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from sqlalchemy import desc

from app.database import SessionLocal, Base, engine
from app.config import get_settings
from app.models.run import Run, RunStatus
from app.models.news_article import NewsArticle
from app.services.audio_generator import AudioBriefingService


logger = structlog.get_logger(__name__)


def prepare_articles(articles):
    """
    Prepare articles for audio generation by parsing JSON fields.

    Args:
        articles: List of NewsArticle ORM objects

    Returns:
        List of article dictionaries with parsed JSON fields
    """
    prepared = []
    for article in articles:
        # Parse entities field (JSON string -> list of dicts)
        entities = []
        if article.entities:
            if isinstance(article.entities, str):
                entities = json.loads(article.entities)
            else:
                entities = article.entities

        article_dict = {
            'id': article.id,
            'title': article.title,
            'description': article.description,
            'source_url': article.source_url,
            'source_name': article.source_name,
            'published_at': article.published_at,
            'roles': json.loads(article.roles) if article.roles else [],
            'priority': article.priority,
            'summary': article.summary,
            'sentiment': article.sentiment,
            'entities': entities,
            'impact_level': article.impact_level,
            'category': article.category,
            'region': article.region,
            'business_line': article.business_line,
            'collector_source': getattr(article, 'collector_source', None) or 'Factiva',
        }
        prepared.append(article_dict)
    return prepared


def estimate_duration(word_count: int) -> str:
    """
    Estimate audio duration based on word count.

    Args:
        word_count: Number of words in script

    Returns:
        Formatted duration estimate (e.g., "2:15")
    """
    # Assume 150 words per minute
    duration_minutes = word_count / 150.0
    minutes = int(duration_minutes)
    seconds = int((duration_minutes - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate audio briefings from the most recent pipeline run."
    )
    parser.add_argument(
        '--role',
        type=str,
        default='brokers',
        help='Role to generate for (brokers, leadership, compliance, underwriting, or all)'
    )
    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='Date in YYYY-MM-DD format (default: today)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force regeneration even if file exists'
    )

    args = parser.parse_args()

    # Parse date
    if args.date:
        try:
            report_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Invalid date format: {args.date}. Expected YYYY-MM-DD")
            return
    else:
        report_date = datetime.now()

    # Validate settings
    settings = get_settings()

    if not settings.is_azure_openai_configured():
        print("[X] Azure OpenAI not configured. Please set environment variables:")
        print("   - AZURE_OPENAI_ENDPOINT")
        print("   - AZURE_OPENAI_API_KEY")
        print("   - AZURE_OPENAI_DEPLOYMENT")
        return

    print(f"[OK] Azure OpenAI configured: {settings.azure_openai_deployment}")
    print()

    # Check num2words installation
    try:
        import num2words
    except ImportError:
        print("[X] num2words not installed. Please install:")
        print("   pip install num2words>=0.5.13")
        return

    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)

    # Create database session
    db = SessionLocal()

    try:
        # Query most recent completed run
        print("[*] Loading most recent completed pipeline run...")
        latest_run = (
            db.query(Run)
            .filter(Run.status == RunStatus.COMPLETED)
            .order_by(desc(Run.completed_at))
            .first()
        )

        if not latest_run:
            print("[X] No completed pipeline runs found in database.")
            print("   Run the pipeline first: python scripts/test_pipeline.py")
            return

        print(f"[OK] Found run {latest_run.id} from {latest_run.completed_at}")
        print(f"   Articles: {latest_run.articles_collected}")
        print(f"   Classified: {latest_run.articles_classified}")
        print()

        # Load classified articles from this run
        print("[*] Loading classified articles...")
        articles = (
            db.query(NewsArticle)
            .filter(
                NewsArticle.run_id == latest_run.id,
                NewsArticle.roles.isnot(None)  # Only classified articles
            )
            .all()
        )

        if not articles:
            print("[X] No classified articles found in latest run.")
            print("   Ensure classification has run successfully.")
            return

        print(f"[OK] Loaded {len(articles)} classified articles")
        print()

        # Prepare articles (parse JSON fields)
        prepared_articles = prepare_articles(articles)

        # Initialize audio service
        print("[*] Initializing audio briefing service...")
        audio_service = AudioBriefingService()

        # Generate audio
        if args.role.lower() == 'all':
            print("[*] Generating audio for all roles...")
            print()
            result = audio_service.generate_all_briefings(prepared_articles, report_date)

            # Print summary
            print("\n" + "="*60)
            print("GENERATION SUMMARY")
            print("="*60)
            print(f"Total generated: {result['total_generated']}")
            print(f"Total skipped:   {result['total_skipped']}")
            print(f"Total failed:    {result['total_failed']}")
            print()

            # Print details per role
            for role_result in result['results']:
                role = role_result['role']
                if role_result.get('generated'):
                    word_count = role_result['word_count']
                    size_mb = role_result['size_mb']
                    duration = estimate_duration(word_count)
                    print(f"[OK] {role}: {word_count} words, {size_mb} MB, ~{duration} duration")
                    print(f"   Path: {role_result['path']}")
                elif role_result.get('reason') == 'already_exists':
                    print(f"[SKIP] {role}: Already exists (skipped)")
                    print(f"   Path: {role_result['path']}")
                else:
                    print(f"[FAIL] {role}: Failed - {role_result.get('error', 'Unknown error')}")
                print()

        else:
            # Single role generation
            role = args.role.capitalize()
            if role not in ["Brokers", "Leadership", "Compliance", "Underwriting"]:
                print(f"[X] Invalid role: {args.role}")
                print("   Valid roles: brokers, leadership, compliance, underwriting, all")
                return

            # Filter articles for this role
            role_articles = [a for a in prepared_articles if role in a.get('roles', [])]

            if not role_articles:
                print(f"[X] No articles found for role: {role}")
                return

            print(f"[*] Generating audio for {role}...")
            print(f"   Articles: {len(role_articles)}")
            print()

            # If force flag, delete existing file
            if args.force:
                from app.services.audio_generator import AUDIO_DIR
                date_str = report_date.strftime("%Y-%m-%d")
                audio_path = Path(AUDIO_DIR) / date_str / f"{role.lower()}.mp3"
                if audio_path.exists():
                    print(f"[DEL] Deleting existing file: {audio_path}")
                    audio_path.unlink()
                    print()

            result = audio_service.generate_briefing(role, role_articles, report_date)

            # Print result
            print("\n" + "="*60)
            print(f"GENERATION RESULT: {role}")
            print("="*60)

            if result.get('generated'):
                word_count = result['word_count']
                size_mb = result['size_mb']
                duration = estimate_duration(word_count)
                print(f"[OK] Generated successfully")
                print(f"   Word count:    {word_count}")
                print(f"   File size:     {size_mb} MB")
                print(f"   Duration est:  ~{duration}")
                print(f"   Voice:         {result['voice']}")
                print(f"   Model:         {result['model']}")
                print(f"   Path:          {result['path']}")
            elif result.get('reason') == 'already_exists':
                print(f"[SKIP] Audio already exists (use --force to regenerate)")
                print(f"   File size:     {result['size_mb']} MB")
                print(f"   Path:          {result['path']}")
            else:
                print(f"[FAIL] Generation failed")
                print(f"   Error: {result.get('error', 'Unknown error')}")

            print()

    finally:
        db.close()


if __name__ == '__main__':
    main()
