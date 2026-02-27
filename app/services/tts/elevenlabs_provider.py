"""
ElevenLabs TTS provider implementation.

Fallback TTS provider using ElevenLabs API for resilience when Azure OpenAI
TTS is unavailable. Implements TTSProvider interface for transparent swapping.
"""
from pathlib import Path

import structlog
from elevenlabs.client import ElevenLabs

from app.config import get_settings
from app.services.tts.base import TTSProvider, TTSError


logger = structlog.get_logger(__name__)


class ElevenLabsTTSProvider(TTSProvider):
    """
    ElevenLabs TTS provider implementation.

    Uses ElevenLabs text-to-speech API as fallback provider when Azure OpenAI
    TTS fails. Implements same atomic file write pattern and exception
    translation as AzureTTSProvider.

    This is the fallback TTS provider for MDInsights (10x+ more expensive
    than Azure, so only used during Azure outages).
    """

    def __init__(self):
        """
        Initialize ElevenLabs TTS client.

        Raises:
            TTSError: If ElevenLabs is not configured (missing API key or voice ID)
        """
        settings = get_settings()

        if not settings.is_elevenlabs_configured():
            raise TTSError("ElevenLabs TTS not configured (missing API key or voice ID)")

        # Initialize ElevenLabs client
        self.client = ElevenLabs(api_key=settings.elevenlabs_api_key)
        self.voice_id = settings.elevenlabs_voice_id
        self.model_id = "eleven_multilingual_v2"

        logger.info(
            "elevenlabs_tts_provider_initialized",
            voice_id=self.voice_id,
            model_id=self.model_id
        )

    def synthesize(self, text: str, output_path: Path) -> dict:
        """
        Convert text to speech using ElevenLabs TTS.

        Uses atomic file write pattern (temp file + rename) to prevent
        corruption from interrupted generation. Wraps all ElevenLabs
        exceptions in TTSError for consistent error handling.

        Args:
            text: Preprocessed script text
            output_path: Destination path for MP3 file

        Returns:
            dict: Metadata with path, size_bytes, size_mb, provider, voice, model

        Raises:
            TTSError: ElevenLabs API error (wrapped from any exception)
        """
        # Create directory if doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare temp file path for atomic write
        temp_path = output_path.with_suffix('.tmp')

        logger.info(
            "elevenlabs_tts_synthesize_started",
            output_path=str(output_path),
            text_length=len(text),
            voice_id=self.voice_id,
            model_id=self.model_id
        )

        try:
            # Call ElevenLabs text-to-speech API
            audio = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model_id,
                output_format="mp3_44100_128"
            )

            # Write audio chunks to temp file (atomic write step 1)
            # ElevenLabs SDK returns audio as iterator of byte chunks
            with open(temp_path, 'wb') as temp_file:
                for chunk in audio:
                    temp_file.write(chunk)

            # Atomic rename to final path (atomic write step 2)
            temp_path.rename(output_path)

            # Get file metadata
            file_size = output_path.stat().st_size

            logger.info(
                "elevenlabs_tts_synthesize_complete",
                output_path=str(output_path),
                size_bytes=file_size,
                size_mb=round(file_size / 1_048_576, 2)
            )

            return {
                "path": str(output_path),
                "size_bytes": file_size,
                "size_mb": round(file_size / 1_048_576, 2),
                "provider": "elevenlabs",
                "voice": self.voice_id,
                "model": self.model_id
            }

        except Exception as e:
            # Catch all ElevenLabs exceptions (ApiError, etc.) and translate to TTSError
            # ElevenLabs SDK may raise various exceptions - catching broadly ensures
            # nothing leaks through the abstraction
            logger.error(
                "elevenlabs_tts_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise TTSError(f"ElevenLabs TTS failed: {e}") from e

        finally:
            # Clean up temp file if exists
            if temp_path.exists():
                temp_path.unlink()

    @property
    def provider_name(self) -> str:
        """Return provider name for logging."""
        return "elevenlabs"
