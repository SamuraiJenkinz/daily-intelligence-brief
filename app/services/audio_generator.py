"""
Audio generator service for generating role-based audio briefings.

Orchestrates the complete script-to-MP3 pipeline: script generation -> text
preprocessing -> TTS conversion -> MP3 file storage. Includes idempotent
generation, atomic file writes, and automatic provider failover.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import structlog

from app.config import get_settings
from app.services.script_generator import ScriptGenerator
from app.services.text_preprocessor import TextPreprocessor
from app.services.tts import AzureTTSProvider, ElevenLabsTTSProvider, TTSError
from app.models.api_event import ApiEvent, ApiEventType
from app.database import SessionLocal


logger = structlog.get_logger(__name__)

# Project root constant (same pattern as pipeline.py)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUDIO_DIR = os.path.join(PROJECT_ROOT, "data", "audio")


class AudioBriefingService:
    """
    Service for generating audio briefings from classified articles.

    Orchestrates the full pipeline:
    1. Generate podcast-style script (ScriptGenerator via GPT-4o)
    2. Preprocess text for TTS (TextPreprocessor via num2words)
    3. Convert to MP3 audio (Azure OpenAI TTS)
    4. Store to filesystem (data/audio/YYYY-MM-DD/{role}.mp3)

    Includes idempotent generation (skip if file exists), atomic file writes,
    retry logic, and structured logging.
    """

    def __init__(self):
        """
        Initialize audio briefing service with script generator, text preprocessor,
        and TTS providers (primary + fallback).
        """
        settings = get_settings()

        # Initialize script generator (handles GPT-4o script generation)
        self.script_generator = ScriptGenerator()

        # Initialize text preprocessor (handles num2words normalization)
        self.text_preprocessor = TextPreprocessor()

        # Initialize TTS providers (primary + fallback)
        try:
            self.primary_provider = AzureTTSProvider()
        except TTSError:
            self.primary_provider = None
            logger.warning("azure_tts_not_configured", msg="Primary TTS provider unavailable")

        if settings.is_elevenlabs_configured():
            try:
                self.fallback_provider = ElevenLabsTTSProvider()
            except TTSError:
                self.fallback_provider = None
                logger.warning("elevenlabs_tts_not_configured", msg="Fallback TTS provider unavailable")
        else:
            self.fallback_provider = None

        # Create audio directory if doesn't exist
        os.makedirs(AUDIO_DIR, exist_ok=True)

    def generate_briefing(self, role: str, articles: List[dict], report_date: datetime) -> dict:
        """
        Generate complete audio briefing for a single role.

        Runs the full pipeline:
        1. Check if audio already exists (idempotent)
        2. Generate script via GPT-4o
        3. Preprocess text for TTS
        4. Validate word count (250-600 words)
        5. Convert to MP3 via TTS
        6. Return metadata

        Args:
            role: Role name (Brokers, Leadership, Compliance, Underwriting)
            articles: List of classified article dictionaries (pre-filtered for role)
            report_date: Date of the report

        Returns:
            dict: Metadata including path, size, word_count, generated flag, etc.
        """
        date_str = report_date.strftime("%Y-%m-%d")

        # Step 1: Idempotent check
        if not self._should_generate(role, date_str):
            audio_path = Path(AUDIO_DIR) / date_str / f"{role.lower()}.mp3"
            file_size = audio_path.stat().st_size
            logger.info(
                "audio_exists_skipping",
                role=role,
                date=date_str,
                path=str(audio_path),
                size_mb=round(file_size / 1_048_576, 2)
            )
            return {
                "role": role,
                "date": date_str,
                "path": str(audio_path),
                "size_bytes": file_size,
                "size_mb": round(file_size / 1_048_576, 2),
                "generated": False,
                "reason": "already_exists"
            }

        try:
            # Step 2: Generate script
            logger.info("generating_script", role=role, date=date_str, article_count=len(articles))
            script = self.script_generator.generate_script(role, articles, report_date)

            # Step 3: Preprocess text for TTS
            logger.info("preprocessing_script", role=role, original_length=len(script))
            preprocessed_script = self.text_preprocessor.preprocess(script)
            character_count = len(preprocessed_script)

            # Step 4: Validate word count
            word_count = len(preprocessed_script.split())
            if word_count < 250 or word_count > 600:
                logger.warning(
                    "word_count_out_of_range",
                    role=role,
                    word_count=word_count,
                    expected_range="250-600"
                )

            # Step 5: Convert to audio
            output_path = Path(AUDIO_DIR) / date_str / f"{role.lower()}.mp3"
            audio_metadata = self._convert_to_audio(preprocessed_script, output_path, role=role, character_count=character_count)

            # Step 6: Return complete metadata
            result = {
                "role": role,
                "date": date_str,
                "word_count": word_count,
                "generated": True,
                **audio_metadata
            }

            logger.info(
                "audio_briefing_complete",
                role=role,
                date=date_str,
                word_count=word_count,
                size_mb=result["size_mb"]
            )

            return result

        except Exception as e:
            logger.error(
                "audio_briefing_failed",
                role=role,
                date=date_str,
                article_count=len(articles),
                error=str(e)
            )
            return {
                "role": role,
                "date": date_str,
                "generated": False,
                "error": str(e),
                "reason": "generation_failed"
            }

    def _convert_to_audio(self, script: str, output_path: Path, role: str = "", character_count: int = 0) -> dict:
        """
        Convert preprocessed script to MP3 audio with automatic provider failover.

        Tries primary provider (Azure) first, then falls back to ElevenLabs on failure.
        All TTS events are logged to api_events table for dashboard visibility.

        Args:
            script: Preprocessed script text (TTS-ready)
            output_path: Destination path for MP3 file
            role: Role name for logging (default: "")
            character_count: Number of characters in script for cost tracking (default: 0)

        Returns:
            dict: File metadata (path, size_bytes, size_mb, provider, voice, model)

        Raises:
            RuntimeError: If no TTS providers are configured or all providers fail
        """
        if self.primary_provider is None and self.fallback_provider is None:
            raise RuntimeError("No TTS providers configured")

        # Try primary provider (Azure)
        if self.primary_provider is not None:
            try:
                logger.info("tts_attempting", provider=self.primary_provider.provider_name)
                result = self.primary_provider.synthesize(script, output_path)
                self._log_tts_event(
                    event_type=ApiEventType.TTS_SUCCESS,
                    provider=self.primary_provider.provider_name,
                    success=True,
                    detail={"size_mb": result["size_mb"], "character_count": character_count, "role": role}
                )
                return result
            except TTSError as e:
                logger.warning(
                    "tts_primary_failed",
                    provider=self.primary_provider.provider_name,
                    error=str(e),
                    fallback=self.fallback_provider.provider_name if self.fallback_provider else "none"
                )

        # Try fallback provider (ElevenLabs)
        if self.fallback_provider is not None:
            try:
                logger.info("tts_attempting_fallback", provider=self.fallback_provider.provider_name)
                result = self.fallback_provider.synthesize(script, output_path)
                self._log_tts_event(
                    event_type=ApiEventType.TTS_FALLBACK,
                    provider=self.fallback_provider.provider_name,
                    success=True,
                    detail={
                        "size_mb": result["size_mb"],
                        "reason": "primary_failed",
                        "primary_provider": self.primary_provider.provider_name if self.primary_provider else "none",
                        "character_count": character_count,
                        "role": role
                    }
                )
                logger.warning(
                    "tts_fallback_succeeded",
                    provider=self.fallback_provider.provider_name,
                    size_mb=result["size_mb"],
                    msg="COST ALERT: ElevenLabs is 10x more expensive than Azure TTS"
                )
                return result
            except TTSError as fallback_error:
                logger.error(
                    "tts_fallback_failed",
                    provider=self.fallback_provider.provider_name,
                    error=str(fallback_error)
                )
                raise RuntimeError(
                    f"All TTS providers failed. Primary: {self.primary_provider.provider_name if self.primary_provider else 'none'}. "
                    f"Fallback: {self.fallback_provider.provider_name}"
                ) from fallback_error

        # Only primary was configured and it failed
        raise RuntimeError("Primary TTS provider failed and no fallback configured")

    def _log_tts_event(self, event_type: ApiEventType, provider: str, success: bool, detail: dict) -> None:
        """Log TTS event to api_events table for dashboard visibility."""
        try:
            with SessionLocal() as session:
                event = ApiEvent(
                    event_type=event_type,
                    api_name="tts",
                    success=success,
                    detail=json.dumps({"provider": provider, **detail})
                )
                session.add(event)
                session.commit()
        except Exception as e:
            # Never let logging failure break audio generation
            logger.error("tts_event_logging_failed", error=str(e))

    def _should_generate(self, role: str, date_str: str) -> bool:
        """
        Check if audio should be generated (idempotent check).

        Returns False if valid audio already exists for this role and date.
        Returns True if audio doesn't exist or is corrupted (too small).

        Args:
            role: Role name (Brokers, Leadership, Compliance, Underwriting)
            date_str: Date string in YYYY-MM-DD format

        Returns:
            bool: True if should generate, False if should skip
        """
        audio_path = Path(AUDIO_DIR) / date_str / f"{role.lower()}.mp3"

        if audio_path.exists():
            file_size = audio_path.stat().st_size
            # Validate minimum size (100KB for valid 2-minute audio)
            if file_size > 100_000:
                return False
            else:
                logger.warning(
                    "audio_corrupted_deleting",
                    role=role,
                    date=date_str,
                    path=str(audio_path),
                    size_bytes=file_size
                )
                audio_path.unlink()

        return True

    def generate_all_briefings(self, articles: List[dict], report_date: datetime) -> dict:
        """
        Generate audio briefings for all four roles.

        Iterates over [Brokers, Leadership, Compliance, Underwriting] and generates
        audio for each role. Filters articles per role before calling generate_briefing.

        Args:
            articles: List of classified article dictionaries
            report_date: Date of the report

        Returns:
            dict: Summary with results list, total_generated, total_skipped, total_failed
        """
        roles = ["Brokers", "Leadership", "Compliance", "Underwriting"]
        results = []
        total_generated = 0
        total_skipped = 0
        total_failed = 0

        logger.info(
            "generating_all_briefings",
            roles=roles,
            total_articles=len(articles),
            date=report_date.strftime("%Y-%m-%d")
        )

        for role in roles:
            try:
                # Filter articles for this role (same logic as reporter.py)
                role_articles = [a for a in articles if role in a.get('roles', [])]

                logger.info(
                    "generating_role_briefing",
                    role=role,
                    article_count=len(role_articles)
                )

                # Generate briefing for role
                result = self.generate_briefing(role, role_articles, report_date)
                results.append(result)

                # Update counters
                if result.get("generated"):
                    total_generated += 1
                elif result.get("reason") == "already_exists":
                    total_skipped += 1
                else:
                    total_failed += 1

            except Exception as e:
                logger.error(
                    "role_briefing_failed",
                    role=role,
                    error=str(e)
                )
                results.append({
                    "role": role,
                    "generated": False,
                    "error": str(e),
                    "reason": "exception"
                })
                total_failed += 1

        logger.info(
            "all_briefings_complete",
            total_generated=total_generated,
            total_skipped=total_skipped,
            total_failed=total_failed
        )

        return {
            "results": results,
            "total_generated": total_generated,
            "total_skipped": total_skipped,
            "total_failed": total_failed
        }
