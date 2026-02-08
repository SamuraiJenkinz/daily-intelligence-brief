"""Comprehensive production readiness validation script.

This script validates all prerequisites for deploying MDInsights to production,
including environment configuration, database setup, task scheduler registration,
template presence, brand compliance, documentation, and Python dependencies.

Usage:
    python scripts/validate_production_ready.py [--verbose]

Exit codes:
    0: All required checks passed (warnings allowed)
    1: One or more required checks failed
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Tuple, List


class ProductionValidator:
    """Validates production readiness across all system components."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log(self, msg: str, level: str = 'INFO'):
        """Print message with appropriate prefix."""
        prefix = {
            'PASS': '[PASS]',
            'FAIL': '[FAIL]',
            'WARN': '[WARN]',
            'INFO': '[INFO]'
        }.get(level, '      ')
        print(f"{prefix} {msg}")

    def check(self, condition: bool, name: str, details: str = '', required: bool = True):
        """Register check result."""
        if condition:
            self.passed += 1
            if self.verbose:
                self.log(f"PASS: {name}", 'PASS')
                if details:
                    print(f"      {details}")
        else:
            if required:
                self.failed += 1
                self.log(f"FAIL: {name}", 'FAIL')
            else:
                self.warnings += 1
                self.log(f"WARN: {name}", 'WARN')
            if details:
                print(f"      {details}")

    def section(self, title: str):
        """Print section header."""
        print(f"\n{'=' * 70}")
        print(f"{title}")
        print(f"{'=' * 70}")

    def validate_environment_variables(self) -> bool:
        """Validate required environment variables are set."""
        self.section("1. Environment Variables")

        # Required variables
        required_vars = [
            ('AZURE_OPENAI_ENDPOINT', 'Azure OpenAI endpoint URL'),
            ('AZURE_OPENAI_API_KEY', 'Azure OpenAI API key'),
            ('AZURE_OPENAI_DEPLOYMENT', 'Azure OpenAI deployment name'),
            ('MICROSOFT_TENANT_ID', 'Microsoft tenant ID for Graph API'),
            ('MICROSOFT_CLIENT_ID', 'Microsoft client ID for Graph API'),
            ('MICROSOFT_CLIENT_SECRET', 'Microsoft client secret for Graph API'),
            ('SENDER_EMAIL', 'Email address for sending reports'),
            ('APIFY_TOKEN', 'Apify API token for web scraping'),
            ('ADMIN_EMAIL', 'Administrator email for alerts'),
        ]

        # Optional variables (warn but don't fail)
        optional_vars = [
            ('AZURE_STORAGE_CONNECTION_STRING', 'Azure Blob Storage connection string for backups'),
        ]

        all_passed = True

        for var_name, description in required_vars:
            value = os.getenv(var_name, '')
            is_set = bool(value and value.strip())
            self.check(is_set, f"{var_name}", description, required=True)
            if not is_set:
                all_passed = False

        for var_name, description in optional_vars:
            value = os.getenv(var_name, '')
            is_set = bool(value and value.strip())
            self.check(is_set, f"{var_name} (optional)", description, required=False)

        return all_passed

    def validate_database(self) -> bool:
        """Validate database exists and has required tables/data."""
        self.section("2. Database")

        # Resolve database path
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        db_path = project_root / 'data' / 'mdinsights.db'

        # Check database file exists
        db_exists = db_path.exists()
        self.check(db_exists, "Database file exists", f"Path: {db_path}", required=True)

        if not db_exists:
            return False

        # Check for enabled sources and table structure
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check sources table has enabled sources
            cursor.execute("SELECT COUNT(*) FROM sources WHERE enabled = 1")
            enabled_count = cursor.fetchone()[0]
            self.check(
                enabled_count > 0,
                f"Enabled sources configured ({enabled_count} found)",
                "At least one source must be enabled for collection",
                required=True
            )

            # Check news_articles table exists
            cursor.execute("SELECT COUNT(*) FROM news_articles")
            article_count = cursor.fetchone()[0]
            self.check(
                True,  # Table exists if we got here
                f"News articles table exists ({article_count} articles)",
                "Database schema is initialized",
                required=True
            )

            conn.close()
            return enabled_count > 0

        except Exception as e:
            self.check(False, "Database validation", f"Error: {str(e)}", required=True)
            return False

    def validate_task_scheduler(self) -> bool:
        """Validate Windows Task Scheduler has required tasks registered."""
        self.section("3. Task Scheduler")

        # Skip on non-Windows
        if sys.platform != 'win32':
            self.log("Skipping Task Scheduler check (non-Windows platform)", 'INFO')
            return True

        required_tasks = [
            "MDInsights Daily Pipeline",
            "MDInsights Daily Pipeline - Backup",
            "MDInsights Daily Pipeline - Drift Check",
            "MDInsights Daily Pipeline - Monitor",
        ]

        all_registered = True

        for task_name in required_tasks:
            try:
                # Use schtasks to query task
                result = subprocess.run(
                    ['schtasks', '/query', '/tn', task_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                is_registered = result.returncode == 0
                self.check(
                    is_registered,
                    f"Task '{task_name}' registered",
                    "Scheduled task exists in Task Scheduler",
                    required=True
                )
                if not is_registered:
                    all_registered = False
            except Exception as e:
                self.check(
                    False,
                    f"Task '{task_name}' check",
                    f"Error: {str(e)}",
                    required=True
                )
                all_registered = False

        return all_registered

    def validate_templates(self) -> bool:
        """Validate required template files exist."""
        self.section("4. Templates")

        script_dir = Path(__file__).parent
        project_root = script_dir.parent

        required_templates = [
            ('app/templates/role_brief.html', 'Browser report template'),
            ('app/templates/email/role_email.html', 'Email report template'),
            ('app/templates/admin/base.html', 'Admin dashboard base template'),
        ]

        all_exist = True

        for template_path, description in required_templates:
            full_path = project_root / template_path
            exists = full_path.exists()
            self.check(exists, template_path, description, required=True)
            if not exists:
                all_exist = False

        return all_exist

    def validate_brand_compliance(self) -> bool:
        """Validate brand compliance by running verify_branding script."""
        self.section("5. Brand Compliance")

        script_dir = Path(__file__).parent
        verify_script = script_dir / 'verify_branding.py'

        if not verify_script.exists():
            self.check(
                False,
                "verify_branding.py script",
                f"Script not found: {verify_script}",
                required=True
            )
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(verify_script)],
                capture_output=True,
                text=True,
                timeout=30
            )
            passed = result.returncode == 0
            self.check(
                passed,
                "Brand verification checks",
                "All templates comply with Marsh brand guidelines" if passed else "Some brand checks failed",
                required=True
            )

            if self.verbose and result.stdout:
                print(result.stdout)

            return passed

        except Exception as e:
            self.check(
                False,
                "Brand verification execution",
                f"Error running verify_branding.py: {str(e)}",
                required=True
            )
            return False

    def validate_documentation(self) -> bool:
        """Validate required documentation files exist."""
        self.section("6. Documentation")

        script_dir = Path(__file__).parent
        project_root = script_dir.parent

        required_docs = [
            ('docs/ADMINISTRATOR_GUIDE.md', 'Administrator operations guide'),
            ('docs/DEPLOYMENT_GUIDE.md', 'Production deployment guide'),
        ]

        all_exist = True

        for doc_path, description in required_docs:
            full_path = project_root / doc_path
            exists = full_path.exists()
            self.check(exists, doc_path, description, required=True)
            if not exists:
                all_exist = False

        return all_exist

    def validate_dependencies(self) -> bool:
        """Validate key Python packages are importable."""
        self.section("7. Dependencies")

        required_packages = [
            ('fastapi', 'FastAPI web framework'),
            ('sqlalchemy', 'Database ORM'),
            ('jinja2', 'Template engine'),
            ('apify_client', 'Apify API client'),
            ('openai', 'Azure OpenAI client'),
            ('azure.identity', 'Azure authentication'),
            ('premailer', 'Email CSS inlining'),
            ('structlog', 'Structured logging'),
            ('tenacity', 'Retry logic'),
        ]

        all_importable = True

        for package_name, description in required_packages:
            try:
                __import__(package_name)
                self.check(True, f"{package_name}", description, required=True)
            except ImportError:
                self.check(
                    False,
                    f"{package_name}",
                    f"Package not installed: {description}",
                    required=True
                )
                all_importable = False

        return all_importable

    def run(self) -> int:
        """Run all validation checks."""
        print("=" * 70)
        print("MDInsights Production Readiness Validation")
        print("=" * 70)

        # Run all validation sections
        results = [
            self.validate_environment_variables(),
            self.validate_database(),
            self.validate_task_scheduler(),
            self.validate_templates(),
            self.validate_brand_compliance(),
            self.validate_documentation(),
            self.validate_dependencies(),
        ]

        # Summary
        print("\n" + "=" * 70)
        print("Validation Summary")
        print("=" * 70)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Warnings: {self.warnings}")
        print("=" * 70)

        if self.failed == 0:
            print("\nAll required checks passed! System is production-ready.")
            if self.warnings > 0:
                print(f"Note: {self.warnings} optional check(s) raised warnings (non-blocking).")
            return 0
        else:
            print(f"\n{self.failed} required check(s) failed. Review output above.")
            return 1


def main():
    """Main entry point."""
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    validator = ProductionValidator(verbose=verbose)
    exit_code = validator.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
