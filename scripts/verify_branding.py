"""Verify MDInsights templates match Marsh brand guidelines.

This script validates that browser and email templates comply with Marsh brand
standards by checking color palettes, typography, attribution, and key structural
elements against the prototype reference.

Usage:
    python scripts/verify_branding.py [--verbose]

Exit codes:
    0: All brand checks passed
    1: One or more brand checks failed
"""
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Marsh brand color palette
MARSH_COLORS = {
    'marsh-blue': '#00263e',
    'marsh-light-blue': '#0077c8',
    'marsh-accent': '#00a3e0',
    'alert-red': '#dc3545',
    'alert-orange': '#fd7e14',
    'alert-yellow': '#ffc107',
    'success-green': '#28a745',
    'neutral-gray': '#6c757d',
    'bg-light': '#f5f7fa',
}

# Required attribution strings
REQUIRED_STRINGS = {
    'kevin_taylor': 'Kevin Taylor',
    'colleague_tech': 'Colleague Technology Services',
    'confidential': 'CONFIDENTIAL',
}

# Email template inline colors (email uses inline styles, not CSS variables)
EMAIL_INLINE_COLORS = {
    'header_bg': '#00263e',
    'accent_gradient': '#00a3e0',
    'bg_light': '#f5f7fa',
}


class BrandVerifier:
    """Verifies brand compliance across templates."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log(self, msg: str, level: str = 'INFO'):
        """Print message if verbose mode enabled."""
        if self.verbose or level in ('PASS', 'FAIL', 'WARN'):
            prefix = {
                'PASS': '[PASS]',
                'FAIL': '[FAIL]',
                'WARN': '[WARN]',
                'INFO': '[INFO]'
            }.get(level, '      ')
            print(f"{prefix} {msg}")

    def check(self, condition: bool, name: str, details: str = ''):
        """Register check result."""
        if condition:
            self.passed += 1
            self.log(f"PASS: {name}", 'PASS')
            if details and self.verbose:
                self.log(f"  {details}", 'INFO')
        else:
            self.failed += 1
            self.log(f"FAIL: {name}", 'FAIL')
            if details:
                self.log(f"  {details}", 'INFO')

    def warn(self, name: str, details: str = ''):
        """Register warning."""
        self.warnings += 1
        self.log(f"WARN: {name}", 'WARN')
        if details:
            self.log(f"  {details}", 'INFO')

    def check_browser_template(self, path: Path) -> bool:
        """Verify browser template brand compliance."""
        self.log(f"\n[Browser Template] Checking: {path.name}")

        if not path.exists():
            self.check(False, "Browser template exists", f"File not found: {path}")
            return False

        content = path.read_text(encoding='utf-8')

        # 1. Check CSS color variables
        self.log("\n[CSS Color Variables]")
        for var_name, expected_color in MARSH_COLORS.items():
            # Match: --marsh-blue: #00263e;
            pattern = rf'--{var_name}\s*:\s*{re.escape(expected_color)}\s*;'
            found = re.search(pattern, content)
            self.check(
                bool(found),
                f"CSS variable --{var_name}",
                f"Expected: {expected_color}"
            )

        # 2. Check header gradient
        self.log("\n[Header Gradient]")
        gradient_pattern = r'linear-gradient\(135deg,\s*var\(--marsh-blue\)\s*0%,\s*#003d6b\s*50%,\s*var\(--marsh-light-blue\)\s*100%\)'
        has_gradient = bool(re.search(gradient_pattern, content))
        self.check(
            has_gradient,
            "Header gradient (135deg, marsh-blue to #003d6b to marsh-light-blue)",
            "Expected: linear-gradient(135deg, var(--marsh-blue) 0%, #003d6b 50%, var(--marsh-light-blue) 100%)"
        )

        # 3. Check typography
        self.log("\n[Typography]")
        has_segoe = "'Segoe UI'" in content or '"Segoe UI"' in content
        self.check(
            has_segoe,
            "Font-family includes 'Segoe UI'",
            "Marsh brand font stack"
        )

        # 4. Check required strings
        self.log("\n[Attribution & Compliance]")
        for key, text in REQUIRED_STRINGS.items():
            found = text in content
            self.check(
                found,
                f"Contains '{text}'",
                f"Required for {key}"
            )

        # 5. Check placeholders
        self.log("\n[Template Placeholders]")
        has_company = '{{ company_name }}' in content
        has_date = '{{ report_date' in content
        self.check(has_company, "Company name placeholder", "{{ company_name }}")
        self.check(has_date, "Report date placeholder", "{{ report_date.* }}")

        return self.failed == 0

    def check_email_template(self, path: Path) -> bool:
        """Verify email template brand compliance."""
        self.log(f"\n[Email Template] Checking: {path.name}")

        if not path.exists():
            self.check(False, "Email template exists", f"File not found: {path}")
            return False

        content = path.read_text(encoding='utf-8')

        # 1. Check inline colors (email uses inline styles, not CSS variables)
        self.log("\n[Inline Brand Colors]")

        # Header background color #00263e
        header_bg_pattern = r'background-color:\s*#00263e'
        has_header_bg = bool(re.search(header_bg_pattern, content))
        self.check(
            has_header_bg,
            "Header background color (#00263e)",
            "Marsh blue inline style"
        )

        # Accent gradient with #00a3e0
        accent_gradient_pattern = r'linear-gradient\([^)]*#00a3e0'
        has_accent = bool(re.search(accent_gradient_pattern, content))
        self.check(
            has_accent,
            "Accent gradient with #00a3e0",
            "Marsh accent color in gradient"
        )

        # Background color #f5f7fa
        bg_light_pattern = r'background-color:\s*#f5f7fa'
        has_bg_light = bool(re.search(bg_light_pattern, content))
        self.check(
            has_bg_light,
            "Background light color (#f5f7fa)",
            "Marsh light background"
        )

        # 2. Check typography
        self.log("\n Typography:")
        has_segoe = "'Segoe UI'" in content or '"Segoe UI"' in content or 'Segoe UI' in content
        self.check(
            has_segoe,
            "Font-family includes Segoe UI",
            "Marsh brand font stack"
        )

        # 3. Check required strings
        self.log("\n Attribution & Compliance:")
        for key, text in REQUIRED_STRINGS.items():
            found = text in content
            self.check(
                found,
                f"Contains '{text}'",
                f"Required for {key}"
            )

        # 4. Check placeholders
        self.log("\n Template Placeholders:")
        has_company = '{{ company_name }}' in content
        has_date = '{{ report_date' in content
        has_role = '{{ role }}' in content
        self.check(has_company, "Company name placeholder", "{{ company_name }}")
        self.check(has_date, "Report date placeholder", "{{ report_date.* }}")
        self.check(has_role, "Role placeholder", "{{ role }}")

        return self.failed == 0

    def run(self, browser_path: Path, email_path: Path) -> int:
        """Run all brand verification checks."""
        print("=" * 70)
        print("MDInsights Brand Verification")
        print("=" * 70)

        initial_failures = self.failed

        # Check both templates
        self.check_browser_template(browser_path)
        self.check_email_template(email_path)

        # Summary
        print("\n" + "=" * 70)
        print("Verification Summary")
        print("=" * 70)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Warnings: {self.warnings}")
        print("=" * 70)

        if self.failed == 0:
            print("\nAll brand checks passed! Templates are brand-compliant.")
            return 0
        else:
            print(f"\n{self.failed} brand check(s) failed. Review output above.")
            return 1


def main():
    """Main entry point."""
    # Parse arguments
    verbose = '--verbose' in sys.argv or '-v' in sys.argv

    # Resolve paths relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    browser_template = project_root / 'app' / 'templates' / 'role_brief.html'
    email_template = project_root / 'app' / 'templates' / 'email' / 'role_email.html'

    # Run verification
    verifier = BrandVerifier(verbose=verbose)
    exit_code = verifier.run(browser_template, email_template)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
