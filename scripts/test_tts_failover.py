"""
TTS Provider Failover Test Script

Tests the TTS provider failover system end-to-end:
1. Verify provider initialization (Azure + ElevenLabs)
2. Test primary provider (Azure) with short text
3. Test fallback provider (ElevenLabs) directly
4. Test failover behavior (simulated Azure failure)
5. Verify api_events table has TTS events

Run: python scripts/test_tts_failover.py
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Now import app modules
from app.services.audio_generator import AudioBriefingService
from app.services.tts import AzureTTSProvider, ElevenLabsTTSProvider, TTSError
from app.models.api_event import ApiEvent, ApiEventType
from app.database import SessionLocal

# Test configuration
TEST_TEXT = "Good morning, this is a test of the Marsh intelligence briefing audio system."
TEST_DIR = PROJECT_ROOT / "data" / "audio" / "test"
TEST_DIR.mkdir(parents=True, exist_ok=True)


def print_status(step: int, msg: str):
    """Print test step status."""
    print(f"[{step}] {msg}")


def print_result(status: str, msg: str):
    """Print test result."""
    print(f"[{status}] {msg}")


def test_provider_initialization():
    """Test 1: Verify provider initialization."""
    print_status(1, "Testing provider initialization...")

    try:
        primary = AzureTTSProvider()
        print_result("OK", f"Primary provider: azure (configured)")
    except TTSError:
        print_result("X", "Primary provider: azure (not configured)")
        primary = None

    try:
        fallback = ElevenLabsTTSProvider()
        print_result("OK", f"Fallback provider: elevenlabs (configured)")
    except TTSError:
        print_result("X", "Fallback provider: elevenlabs (not configured)")
        fallback = None

    return primary, fallback


def test_primary_provider(provider):
    """Test 2: Test primary provider (Azure) with short text."""
    print_status(2, "Testing primary provider (Azure)...")

    if provider is None:
        print_result("SKIP", "Azure not configured")
        return False

    try:
        output_path = TEST_DIR / "primary_test.mp3"
        result = provider.synthesize(TEST_TEXT, output_path)
        size_kb = result["size_bytes"] / 1024
        print_result("OK", f"Primary: {size_kb:.0f}KB, provider={result['provider']}")
        return True
    except Exception as e:
        print_result("X", f"Primary failed: {e}")
        return False


def test_fallback_provider(provider):
    """Test 3: Test fallback provider (ElevenLabs) directly."""
    print_status(3, "Testing fallback provider (ElevenLabs)...")

    if provider is None:
        print_result("SKIP", "ElevenLabs not configured")
        return False

    try:
        output_path = TEST_DIR / "fallback_test.mp3"
        result = provider.synthesize(TEST_TEXT, output_path)
        size_kb = result["size_bytes"] / 1024
        print_result("OK", f"Fallback: {size_kb:.0f}KB, provider={result['provider']}")
        return True
    except Exception as e:
        print_result("X", f"Fallback failed: {e}")
        return False


def test_failover_behavior():
    """Test 4: Test failover via AudioBriefingService with simulated Azure failure."""
    print_status(4, "Testing failover (simulated Azure failure)...")

    try:
        service = AudioBriefingService()

        # Simulate Azure failure by setting primary_provider to None
        original_primary = service.primary_provider
        service.primary_provider = None

        if service.fallback_provider is None:
            print_result("SKIP", "ElevenLabs not configured for failover test")
            return False

        # Call _convert_to_audio which should fall back to ElevenLabs
        output_path = TEST_DIR / "failover_test.mp3"
        result = service._convert_to_audio(TEST_TEXT, output_path)

        size_kb = result["size_bytes"] / 1024
        print_result("OK", f"Failover worked: {size_kb:.0f}KB, provider={result['provider']}")

        # Restore original primary
        service.primary_provider = original_primary
        return True

    except Exception as e:
        print_result("X", f"Failover failed: {e}")
        return False


def test_api_events():
    """Test 5: Verify api_events table has TTS events."""
    print_status(5, "Checking api_events...")

    try:
        with SessionLocal() as session:
            # Query for TTS events
            tts_success_count = session.query(ApiEvent).filter_by(
                api_name="tts",
                event_type=ApiEventType.TTS_SUCCESS
            ).count()

            tts_fallback_count = session.query(ApiEvent).filter_by(
                api_name="tts",
                event_type=ApiEventType.TTS_FALLBACK
            ).count()

            total_events = tts_success_count + tts_fallback_count

            if total_events > 0:
                print_result("OK", f"Found {total_events} TTS events in api_events table")
                print(f"    TTS_SUCCESS: {tts_success_count}")
                print(f"    TTS_FALLBACK: {tts_fallback_count}")
                return True
            else:
                print_result("WARN", "No TTS events found in api_events table")
                return False

    except Exception as e:
        print_result("X", f"api_events check failed: {e}")
        return False


def cleanup_test_files():
    """Clean up test audio files."""
    print_status("*", "Cleaning up test files...")

    try:
        for test_file in TEST_DIR.glob("*.mp3"):
            test_file.unlink()
        print_result("OK", "Test files cleaned up")
    except Exception as e:
        print_result("WARN", f"Cleanup failed: {e}")


def main():
    """Run all TTS failover tests."""
    print("[*] TTS Provider Failover Test")
    print()

    # Test 1: Provider initialization
    primary, fallback = test_provider_initialization()
    print()

    # Test 2: Primary provider
    if primary:
        test_primary_provider(primary)
        print()

    # Test 3: Fallback provider
    if fallback:
        test_fallback_provider(fallback)
        print()

    # Test 4: Failover behavior
    test_failover_behavior()
    print()

    # Test 5: api_events
    test_api_events()
    print()

    # Cleanup
    cleanup_test_files()
    print()

    print("[*] Test complete")


if __name__ == "__main__":
    main()
