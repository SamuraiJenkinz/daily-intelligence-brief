"""
Test script for RoleReportService with sample data.

Generates HTML report using hardcoded sample articles (no database required).
Writes output to data/test_report.html for browser inspection.
"""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.reporter import RoleReportService


def create_sample_articles():
    """
    Create sample classified articles for testing.

    Returns:
        List of SimpleNamespace objects simulating NewsArticle ORM objects
    """
    base_date = datetime(2026, 2, 6, 10, 0, 0)

    articles = [
        # Critical priority - multi-role
        SimpleNamespace(
            id=1,
            title="Swiss Re Reports Strong Q4 Results with 15% ROE",
            description="Swiss Re's Q4 profits exceeded expectations with strong performance across all segments.",
            source_url="https://www.reinsurancene.ws/swiss-re-q4-2026",
            source_name="Reinsurance News",
            published_at=base_date,
            roles='["Leadership", "Brokers"]',
            priority="Critical",
            summary="Swiss Re reported Q4 2026 results showing 15% ROE, exceeding analyst expectations. "
                    "Property & Casualty reinsurance segment drove performance with strong pricing discipline. "
                    "Leadership signals continued capacity deployment in profitable segments.",
            sentiment="positive"
        ),
        # Critical priority - single role
        SimpleNamespace(
            id=2,
            title="New EU Cyber Security Directive Impacts Insurance Requirements",
            description="EU mandates cyber insurance for critical infrastructure operators effective Q2 2026.",
            source_url="https://www.insurancejournal.com/eu-cyber-directive-2026",
            source_name="Insurance Journal",
            published_at=base_date,
            roles='["Compliance"]',
            priority="Critical",
            summary="New EU directive requires critical infrastructure operators to maintain cyber insurance coverage "
                    "starting April 2026. Minimum coverage thresholds and reporting requirements specified. "
                    "Compliance teams must review portfolio for affected clients.",
            sentiment="negative"
        ),
        # High priority - multi-role
        SimpleNamespace(
            id=3,
            title="Lloyd's Market Sees 20% Increase in Cyber Premiums",
            description="Lloyd's cyber insurance market grows significantly driven by increased corporate demand.",
            source_url="https://www.lloyds.com/cyber-market-growth-2026",
            source_name="Lloyd's Market Report",
            published_at=base_date,
            roles='["Brokers", "Underwriting"]',
            priority="High",
            summary="Lloyd's cyber insurance premiums increased 20% year-over-year, with strong demand from "
                    "mid-market and enterprise clients. Brokers report pricing stabilization after 2023-2024 hardening. "
                    "Loss ratios improving as risk management standards mature.",
            sentiment="positive"
        ),
        # High priority - Leadership only
        SimpleNamespace(
            id=4,
            title="Moody's Upgrades Insurance Sector Outlook to Stable",
            description="Rating agency cites improved capitalization and strong underwriting results.",
            source_url="https://www.moodys.com/insurance-outlook-2026",
            source_name="Moody's",
            published_at=base_date,
            roles='["Leadership"]',
            priority="High",
            summary="Moody's upgraded the global insurance sector outlook from negative to stable, citing "
                    "improved capital positions and sustained underwriting discipline. Reinsurance sector "
                    "particularly strong with ROE above cost of capital for third consecutive year.",
            sentiment="positive"
        ),
        # Medium priority - Underwriting focus
        SimpleNamespace(
            id=5,
            title="Climate Risk Modeling: New Tools for Property Underwriters",
            description="Advanced climate models now available for property risk assessment.",
            source_url="https://www.propertycasualty360.com/climate-modeling-2026",
            source_name="PropertyCasualty360",
            published_at=base_date,
            roles='["Underwriting", "Brokers"]',
            priority="Medium",
            summary="New climate risk modeling platforms integrate real-time weather data with historical loss patterns. "
                    "Underwriters can now assess property exposures with greater precision for wildfire, flood, and "
                    "windstorm perils. Early adopters report 10-15% improvement in loss ratio accuracy.",
            sentiment="positive"
        ),
        # Medium priority - Compliance focus
        SimpleNamespace(
            id=6,
            title="IAIS Publishes Updated Anti-Money Laundering Guidelines",
            description="International Association of Insurance Supervisors releases revised AML standards.",
            source_url="https://www.iaisweb.org/aml-guidelines-2026",
            source_name="IAIS",
            published_at=base_date,
            roles='["Compliance", "Leadership"]',
            priority="Medium",
            summary="IAIS updated AML guidelines emphasize transaction monitoring for life insurance and annuity products. "
                    "New requirements for beneficial ownership verification and enhanced due diligence on high-value policies. "
                    "Implementation deadline: January 2027.",
            sentiment="neutral"
        ),
        # Monitor priority - market trend
        SimpleNamespace(
            id=7,
            title="Parametric Insurance Grows 25% in Agriculture Sector",
            description="Parametric coverage gaining traction among agricultural producers.",
            source_url="https://www.aginsurance.com/parametric-growth-2026",
            source_name="Agricultural Insurance News",
            published_at=base_date,
            roles='["Brokers"]',
            priority="Monitor",
            summary="Parametric insurance products for agriculture grew 25% in 2025, driven by faster claims settlement "
                    "and transparent triggers based on weather data. Particularly strong adoption in drought-prone regions. "
                    "Brokers report client satisfaction with simplified claims process.",
            sentiment="positive"
        ),
        # Monitor priority - tech development
        SimpleNamespace(
            id=8,
            title="AI-Powered Claims Processing Reduces Cycle Time by 40%",
            description="Insurers adopting AI claims tools see significant efficiency gains.",
            source_url="https://www.insurancetech.com/ai-claims-2026",
            source_name="Insurance Technology",
            published_at=base_date,
            roles='["Underwriting", "Leadership"]',
            priority="Monitor",
            summary="Insurance companies using AI-powered claims processing report 40% reduction in average cycle time "
                    "and 30% lower processing costs. Technology particularly effective for auto and property claims. "
                    "Customer satisfaction scores improve with faster settlement.",
            sentiment="positive"
        ),
    ]

    return articles


def main():
    """Generate test report and save to file."""
    print("=" * 60)
    print("MDInsights Report Test Script")
    print("=" * 60)

    # Create sample articles
    print("\n1. Creating sample articles...")
    articles = create_sample_articles()
    print(f"   [OK] Created {len(articles)} sample articles")

    # Analyze article distribution
    print("\n2. Article distribution:")
    role_counts = {}
    priority_counts = {}

    for article in articles:
        # Count roles
        import json
        roles = json.loads(article.roles)
        for role in roles:
            role_counts[role] = role_counts.get(role, 0) + 1

        # Count priorities
        priority = article.priority
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    print("\n   By Role:")
    for role in ["Brokers", "Leadership", "Compliance", "Underwriting"]:
        count = role_counts.get(role, 0)
        print(f"   - {role}: {count} articles")

    print("\n   By Priority:")
    for priority in ["Critical", "High", "Medium", "Monitor"]:
        count = priority_counts.get(priority, 0)
        print(f"   - {priority}: {count} articles")

    # Initialize reporter service
    print("\n3. Initializing RoleReportService...")
    reporter = RoleReportService()
    print("   [OK] Service initialized")

    # Generate report
    print("\n4. Generating HTML report...")
    report_date = datetime.now()
    html = reporter.generate_role_brief(
        articles=articles,
        report_date=report_date,
        company_name="Marsh"
    )
    print(f"   [OK] Generated {len(html)} characters of HTML")

    # Write to file
    print("\n5. Writing report to file...")
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "test_report.html"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"   [OK] Report saved to: {output_path}")
    print(f"\n{'=' * 60}")
    print("[SUCCESS] Test complete!")
    print(f"{'=' * 60}")
    print(f"\nOpen the report in your browser:")
    print(f"   file:///{output_path.absolute().as_posix()}")
    print()


if __name__ == "__main__":
    main()
