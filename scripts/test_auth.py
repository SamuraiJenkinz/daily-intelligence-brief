"""
Standalone JWT token acquisition test for MMC Core API.

Usage:
    python scripts/test_auth.py

Tests:
    1. Validates MMC API environment variables are present
    2. Attempts token acquisition from Access Management API
    3. Validates token response structure
    4. Tests token refresh (force re-acquisition)
    5. Reports success/failure with structured output

Exit codes:
    0 = All tests passed
    1 = Token acquisition failed
    2 = Configuration missing
"""
import asyncio
import os
import sys
import time

# Ensure project root is on path when running as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load .env before importing app modules (pydantic-settings reads env at import time)
load_dotenv()

from app.config import get_settings
from app.database import Base, engine
from app.logging_config import configure_logging

# Import all models to register with Base.metadata (ensures api_events table is created)
import app.models.news_article  # noqa: F401
import app.models.source  # noqa: F401
import app.models.run  # noqa: F401
import app.models.api_event  # noqa: F401

from app.auth.token_manager import TokenManager


def _print_separator():
    print("-" * 60)


def _check_config(settings) -> bool:
    """Check configuration and print which vars are missing. Returns True if OK."""
    _print_separator()
    print("STEP 1: Checking MMC Core API configuration")
    _print_separator()

    missing = []
    if not settings.mmc_api_base_url:
        missing.append("MMC_API_BASE_URL")
    if not settings.mmc_api_client_id:
        missing.append("MMC_API_CLIENT_ID")
    if not settings.mmc_api_client_secret:
        missing.append("MMC_API_CLIENT_SECRET")

    if missing:
        print(f"CONFIGURATION MISSING - cannot proceed.")
        print(f"\nThe following environment variables are not set:")
        for var in missing:
            print(f"  - {var}")
        print(f"\nTo fix:")
        print(f"  1. Copy .env.example to .env")
        print(f"  2. Fill in the MMC Core API section")
        print(f"  3. Run this script again")
        print(f"\nStaging host: mmc-dallas-int-non-prod-ingress.mgti.mmc.com")
        return False

    print(f"Base URL:     {settings.mmc_api_base_url}")
    print(f"Token path:   {settings.mmc_api_token_path}")
    print(f"Client ID:    {settings.mmc_api_client_id[:4]}*** (truncated for security)")
    print(f"Config check: PASSED")
    return True


async def _test_token_acquisition(tm: TokenManager) -> bool:
    """Test initial token acquisition. Returns True on success."""
    _print_separator()
    print("STEP 2: Acquiring JWT token from Access Management API")
    _print_separator()

    start = time.time()
    token = await tm.get_token()
    elapsed = time.time() - start

    if not token:
        print("Token acquisition: FAILED")
        print("Check logs above for error details.")
        print("Common causes:")
        print("  - Invalid client_id or client_secret")
        print("  - Network unreachable (check VPN / firewall)")
        print("  - Token endpoint path incorrect")
        return False

    # Display token metadata without revealing the token itself
    token_info = tm._token
    remaining_seconds = token_info.expires_at - time.time() if token_info else 0
    remaining_minutes = remaining_seconds / 60

    print(f"Token type:       {token_info.token_type if token_info else 'unknown'}")
    print(f"Expires in:       {remaining_minutes:.1f} minutes")
    print(f"Acquisition time: {elapsed:.2f}s")
    print(f"Token (redacted): {token[:8]}...{token[-4:]} (first 8 + last 4 chars only)")
    print(f"Token acquisition: PASSED")
    return True


async def _test_cache(tm: TokenManager) -> bool:
    """Test that cached token is returned without network call. Returns True on success."""
    _print_separator()
    print("STEP 3: Verifying token cache (should not call API)")
    _print_separator()

    start = time.time()
    token2 = await tm.get_token()
    elapsed = time.time() - start

    if not token2:
        print("Cache test: FAILED (second get_token() returned None)")
        return False

    if elapsed > 0.1:
        print(f"Cache test: WARNING - took {elapsed:.3f}s (expected <0.1s for cache hit)")
    else:
        print(f"Cache hit:    {elapsed * 1000:.1f}ms (no network call)")
        print(f"Cache test:   PASSED")
    return True


async def _test_force_refresh(tm: TokenManager) -> bool:
    """Test force_refresh invalidates cache and re-acquires. Returns True on success."""
    _print_separator()
    print("STEP 4: Testing force refresh (invalidates cache, re-acquires token)")
    _print_separator()

    start = time.time()
    refreshed_token = await tm.force_refresh()
    elapsed = time.time() - start

    if not refreshed_token:
        print("Token refresh: FAILED")
        print("Check logs above for error details.")
        return False

    token_info = tm._token
    remaining_minutes = (token_info.expires_at - time.time()) / 60 if token_info else 0

    print(f"Refresh time:   {elapsed:.2f}s")
    print(f"Expires in:     {remaining_minutes:.1f} minutes")
    print(f"Token refresh:  PASSED")
    return True


async def main():
    """Run the full auth test suite."""
    settings = get_settings()

    # Configure logging (suppress structlog JSON to keep output human-readable)
    configure_logging(log_level="WARNING")

    # Ensure data directory and DB tables exist
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)

    print()
    print("=" * 60)
    print("  MDInsights — MMC Core API Auth Test")
    print("=" * 60)

    # Step 1: Configuration check
    if not _check_config(settings):
        print()
        sys.exit(2)

    tm = TokenManager()

    # Step 2: Token acquisition
    if not await _test_token_acquisition(tm):
        print()
        sys.exit(1)

    # Step 3: Cache validation
    if not await _test_cache(tm):
        print()
        sys.exit(1)

    # Step 4: Force refresh
    if not await _test_force_refresh(tm):
        print()
        sys.exit(1)

    # Summary
    _print_separator()
    print("All auth tests passed.")
    print("The TokenManager is ready for use in Phase 10-12 enterprise API calls.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
