"""
Pipeline test script for MDInsights.

Simulates full pipeline execution: collection → classification → reporting.
Writes HTML output to data/pipeline_test.html for inspection.

NOTE: Requires live Apify and Azure OpenAI credentials in .env file.
      Do NOT run in CI/CD - this is a manual test tool only.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from app.config import get_settings
from app.services.collector import ApifyCollector
from app.services.classifier import RoleClassificationService
from app.services.reporter import RoleReportService
from app.services.pipeline import PipelineOrchestrator


def main():
    """Run pipeline test."""
    print("=" * 60)
    print("MDInsights Pipeline Test")
    print("=" * 60)
    print()

    # Load environment variables
    load_dotenv()
    settings = get_settings()

    # Validate configuration
    print("Configuration Check:")
    print(f"  Apify: {'✓ Configured' if settings.is_apify_configured() else '✗ Missing'}")
    print(f"  Azure OpenAI: {'✓ Configured' if settings.is_azure_openai_configured() else '✗ Missing'}")
    print()

    if not settings.is_apify_configured():
        print("ERROR: Apify token not configured. Set APIFY_TOKEN in .env")
        return 1

    if not settings.is_azure_openai_configured():
        print("ERROR: Azure OpenAI not configured. Set credentials in .env")
        return 1

    # Initialize services
    print("Initializing services...")
    collector = ApifyCollector(apify_token=settings.apify_token)
    classifier = RoleClassificationService(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        deployment=settings.azure_openai_deployment,
        api_version=settings.azure_openai_api_version
    )
    reporter = RoleReportService()

    # Initialize orchestrator
    orchestrator = PipelineOrchestrator(
        collector=collector,
        classifier=classifier,
        reporter=reporter
    )
    print("✓ Services initialized")
    print()

    # Run pipeline
    print("Executing pipeline...")
    print("  This may take several minutes...")
    print()

    start_time = datetime.utcnow()

    try:
        result = orchestrator.run_full_pipeline(role="Brokers")

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # Print results
        print("=" * 60)
        print("Pipeline Results")
        print("=" * 60)
        print()
        print(f"  Status: {result['status']}")
        print(f"  Run ID: {result['run_id']}")
        print(f"  Articles Collected: {result['articles_collected']}")
        print(f"  Articles Classified: {result['articles_classified']}")
        print(f"  Duration: {duration:.2f} seconds")
        print()

        if result['status'] == 'completed':
            # Write HTML output to file
            output_path = Path("data/pipeline_test.html")
            output_path.parent.mkdir(exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result['html_output'])

            print(f"✓ HTML report written to: {output_path.absolute()}")
            print()
            print("Open this file in a browser to view the report.")
            print()
            return 0

        else:
            print(f"✗ Pipeline failed: {result.get('error', 'Unknown error')}")
            print()
            return 1

    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        print()
        print("=" * 60)
        print("Pipeline Error")
        print("=" * 60)
        print()
        print(f"  Error: {str(e)}")
        print(f"  Duration: {duration:.2f} seconds")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
