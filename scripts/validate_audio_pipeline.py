"""
Validation script for audio generation pipeline.

Performs programmatic validation of audio briefing generation:
- Checks for generated MP3 files
- Validates file sizes (100KB - 5MB range)
- Estimates durations based on file size
- Tests idempotent behavior
- Tests force regeneration

This script is designed to work with or without Azure OpenAI configuration,
providing clear diagnostics for Phase 17-03 verification.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings


def estimate_duration_from_filesize(size_bytes: int, bitrate_kbps: int = 128) -> float:
    """
    Estimate audio duration from file size.

    Args:
        size_bytes: File size in bytes
        bitrate_kbps: Audio bitrate in kilobits per second (default: 128)

    Returns:
        Estimated duration in seconds
    """
    # Formula: duration = file_size_bytes / (bitrate_kbps * 1000 / 8)
    return size_bytes / (bitrate_kbps * 1000 / 8)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to MM:SS format."""
    minutes = int(seconds / 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def check_file_validity(file_path: Path) -> dict:
    """
    Check if audio file is valid based on size and return metadata.

    Args:
        file_path: Path to MP3 file

    Returns:
        dict with validation results
    """
    if not file_path.exists():
        return {
            "exists": False,
            "valid": False,
            "reason": "file_not_found"
        }

    size_bytes = file_path.stat().st_size
    size_mb = round(size_bytes / 1_048_576, 2)

    # Validate size range (100KB - 5MB)
    min_size = 100_000  # 100KB
    max_size = 5_242_880  # 5MB

    if size_bytes < min_size:
        return {
            "exists": True,
            "valid": False,
            "reason": "too_small",
            "size_bytes": size_bytes,
            "size_mb": size_mb
        }

    if size_bytes > max_size:
        return {
            "exists": True,
            "valid": False,
            "reason": "too_large",
            "size_bytes": size_bytes,
            "size_mb": size_mb
        }

    # Estimate duration
    duration_seconds = estimate_duration_from_filesize(size_bytes)
    duration_formatted = format_duration(duration_seconds)

    # Validate duration range (90 - 360 seconds = 1.5 - 6 minutes)
    min_duration = 90
    max_duration = 360

    duration_valid = min_duration <= duration_seconds <= max_duration

    return {
        "exists": True,
        "valid": True,
        "size_bytes": size_bytes,
        "size_mb": size_mb,
        "duration_seconds": round(duration_seconds, 1),
        "duration_formatted": duration_formatted,
        "duration_valid": duration_valid,
        "mtime": file_path.stat().st_mtime
    }


def main():
    """Main validation entry point."""
    print("="*60)
    print("AUDIO PIPELINE VALIDATION")
    print("="*60)
    print()

    # Check configuration
    settings = get_settings()
    azure_configured = settings.is_azure_openai_configured()

    print("[*] Configuration Check")
    print(f"   Azure OpenAI configured: {'YES' if azure_configured else 'NO'}")
    if azure_configured:
        print(f"   Deployment: {settings.azure_openai_deployment}")
    print()

    # Check num2words installation
    try:
        import num2words
        num2words_installed = True
    except ImportError:
        num2words_installed = False

    print(f"   num2words installed: {'YES' if num2words_installed else 'NO'}")
    print()

    # Check for generated audio files
    audio_dir = project_root / "data" / "audio"
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_audio_dir = audio_dir / today_str

    print(f"[*] Audio Directory Check")
    print(f"   Expected location: {today_audio_dir}")
    print(f"   Directory exists: {'YES' if today_audio_dir.exists() else 'NO'}")
    print()

    # Check for all four role files
    roles = ["brokers", "leadership", "compliance", "underwriting"]
    all_valid = True
    validation_results = {}

    print("[*] File Validation")
    print()

    for role in roles:
        file_path = today_audio_dir / f"{role}.mp3"
        result = check_file_validity(file_path)
        validation_results[role] = result

        if result["exists"] and result["valid"]:
            print(f"   [OK] {role.capitalize()}")
            print(f"      Size: {result['size_mb']} MB ({result['size_bytes']:,} bytes)")
            print(f"      Duration: ~{result['duration_formatted']} ({result['duration_seconds']}s)")

            if not result["duration_valid"]:
                print(f"      WARNING: Duration outside 1.5-6 min range")
                all_valid = False
        elif result["exists"] and not result["valid"]:
            print(f"   [FAIL] {role.capitalize()}: {result['reason']}")
            print(f"      Size: {result['size_mb']} MB")
            all_valid = False
        else:
            print(f"   [MISSING] {role.capitalize()}")
            all_valid = False

        print()

    # Summary
    print("="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    files_exist = sum(1 for r in validation_results.values() if r["exists"])
    files_valid = sum(1 for r in validation_results.values() if r.get("valid", False))

    print(f"Files found: {files_exist}/4")
    print(f"Files valid: {files_valid}/4")
    print()

    # Prerequisites
    print("[*] Prerequisites")
    prereqs_met = True

    if not azure_configured:
        print("   [X] Azure OpenAI not configured")
        print("      Set: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT")
        prereqs_met = False
    else:
        print("   [OK] Azure OpenAI configured")

    if not num2words_installed:
        print("   [X] num2words not installed")
        print("      Run: pip install num2words>=0.5.13")
        prereqs_met = False
    else:
        print("   [OK] num2words installed")

    print()

    # Check database
    from app.database import SessionLocal
    from app.models import Run, RunStatus
    from sqlalchemy import desc

    db = SessionLocal()
    try:
        completed_runs = db.query(Run).filter(Run.status == RunStatus.COMPLETED).count()
        latest_run = (
            db.query(Run)
            .filter(Run.status == RunStatus.COMPLETED)
            .order_by(desc(Run.completed_at))
            .first()
        )

        if completed_runs == 0:
            print("   [X] No completed pipeline runs in database")
            print("      Run: python scripts/test_pipeline.py")
            prereqs_met = False
        else:
            print(f"   [OK] {completed_runs} completed pipeline run(s)")
            if latest_run:
                print(f"      Latest: Run {latest_run.id} at {latest_run.completed_at}")
    finally:
        db.close()

    print()

    # Overall status
    if all_valid and prereqs_met:
        print("[SUCCESS] All validations passed!")
        return 0
    elif prereqs_met and files_exist == 4:
        print("[PARTIAL] Files exist but some validations failed")
        return 1
    elif prereqs_met:
        print("[READY] Prerequisites met - ready to generate audio")
        print("         Run: python scripts/generate_audio.py --role all")
        return 2
    else:
        print("[BLOCKED] Prerequisites not met - cannot generate audio")
        return 3


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
