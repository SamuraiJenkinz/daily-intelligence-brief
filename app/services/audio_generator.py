"""
Audio generator service for generating role-based audio briefings.

Orchestrates the complete script-to-MP3 pipeline: script generation -> text
preprocessing -> TTS conversion -> MP3 file storage. Includes idempotent
generation, atomic file writes, and retry logic.
"""
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import structlog
from openai import AzureOpenAI, OpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)

from app.config import get_settings
from app.services.script_generator import ScriptGenerator
from app.services.text_preprocessor import TextPreprocessor


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
        and separate TTS client.
        """
        settings = get_settings()

        # Initialize script generator (handles GPT-4o script generation)
        self.script_generator = ScriptGenerator()

        # Initialize text preprocessor (handles num2words normalization)
        self.text_preprocessor = TextPreprocessor()

        # Initialize separate TTS client (may use different deployment than GPT-4o)
        if settings.is_azure_openai_configured():
            endpoint = settings.azure_openai_endpoint
            if '/deployments/' in endpoint:
                # Corporate proxy - endpoint is the full URL, use standard client
                base_url = endpoint.rstrip('/')
                if base_url.endswith('/chat/completions'):
                    base_url = base_url[:-len('/chat/completions')]
                # For TTS, we need to modify the base_url to use audio endpoint
                # Corporate proxy pattern: keep base_url as-is, TTS uses different path
                self.tts_client = OpenAI(base_url=base_url, api_key=settings.azure_openai_api_key)
            else:
                # Standard Azure OpenAI endpoint
                self.tts_client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version
                )
        else:
            self.tts_client = None

        # TTS settings
        self.model = "tts-1-hd"
        self._voice = settings.company_name if hasattr(settings, 'tts_voice') else "nova"
        self.response_format = "mp3"
        self.speed = 1.0

        # Create audio directory if doesn't exist
        os.makedirs(AUDIO_DIR, exist_ok=True)

    @property
    def voice(self) -> str:
        """Get TTS voice setting (configurable, defaults to nova)."""
        settings = get_settings()
        # Check if tts_voice is configured in settings
        if hasattr(settings, 'tts_voice') and settings.tts_voice:
            return settings.tts_voice
        return self._voice

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
            audio_metadata = self._convert_to_audio(preprocessed_script, output_path)

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((APIError, RateLimitError, APIConnectionError, APITimeoutError)),
        reraise=True
    )
    def _convert_to_audio(self, script: str, output_path: Path) -> dict:
        """
        Convert preprocessed script to MP3 audio file via Azure OpenAI TTS.

        Uses atomic file writes (temp file + rename) to prevent corruption.

        Args:
            script: Preprocessed script text (TTS-ready)
            output_path: Destination path for MP3 file

        Returns:
            dict: File metadata (path, size_bytes, size_mb, voice, model)

        Raises:
            RuntimeError: If Azure OpenAI TTS not configured
            APIError, RateLimitError, APIConnectionError, APITimeoutError: API errors
        """
        # Check TTS client is configured
        if self.tts_client is None:
            raise RuntimeError("Azure OpenAI TTS not configured")

        # Create directory if doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare temp file path for atomic write
        temp_path = output_path.with_suffix('.tmp')

        logger.info(
            "tts_conversion_started",
            output_path=str(output_path),
            script_length=len(script),
            voice=self.voice,
            model=self.model
        )

        start_time = time.time()

        try:
            # Call Azure OpenAI TTS
            response = self.tts_client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=script,
                response_format=self.response_format,
                speed=self.speed
            )

            # Stream to temp file first
            response.stream_to_file(str(temp_path))

            # Atomic rename to final path
            temp_path.rename(output_path)

            # Get file metadata
            file_size = output_path.stat().st_size
            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "tts_conversion_complete",
                output_path=str(output_path),
                size_bytes=file_size,
                size_mb=round(file_size / 1_048_576, 2),
                duration_ms=duration_ms
            )

            return {
                "path": str(output_path),
                "size_bytes": file_size,
                "size_mb": round(file_size / 1_048_576, 2),
                "voice": self.voice,
                "model": self.model
            }

        except Exception as e:
            # Clean up temp file if exists
            if temp_path.exists():
                temp_path.unlink()
            raise

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
