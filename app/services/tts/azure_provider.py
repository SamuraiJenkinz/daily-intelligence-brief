"""
Azure OpenAI TTS provider implementation.

Extracts TTS logic from audio_generator.py into standalone provider class
that implements TTSProvider interface for use in failover system.
"""
from pathlib import Path

import structlog
from openai import AzureOpenAI, OpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError

from app.config import get_settings
from app.services.tts.base import TTSProvider, TTSError


logger = structlog.get_logger(__name__)


class AzureTTSProvider(TTSProvider):
    """
    Azure OpenAI TTS provider implementation.

    Uses the same corporate proxy pattern and atomic file write strategy
    as the original audio_generator.py implementation. Translates all
    Azure OpenAI exceptions to common TTSError.

    This is the primary TTS provider for MDInsights.
    """

    def __init__(self):
        """
        Initialize Azure OpenAI TTS client.

        Raises:
            TTSError: If Azure OpenAI is not configured
        """
        settings = get_settings()

        if not settings.is_azure_openai_configured():
            raise TTSError("Azure OpenAI TTS not configured")

        # Initialize TTS client using corporate proxy pattern from audio_generator.py
        endpoint = settings.azure_openai_endpoint
        if '/deployments/' in endpoint:
            # Corporate proxy - endpoint is full URL, use standard client
            base_url = endpoint.rstrip('/')
            if base_url.endswith('/chat/completions'):
                base_url = base_url[:-len('/chat/completions')]
            # For TTS, keep base_url as-is (uses different path than chat)
            self.client = OpenAI(base_url=base_url, api_key=settings.azure_openai_api_key)
        else:
            # Standard Azure OpenAI endpoint
            self.client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version
            )

        # TTS settings
        self.model = "tts-1-hd"
        self.voice = settings.tts_voice if hasattr(settings, 'tts_voice') and settings.tts_voice else "nova"
        self.response_format = "mp3"
        self.speed = 1.0

        logger.info(
            "azure_tts_provider_initialized",
            model=self.model,
            voice=self.voice,
            response_format=self.response_format
        )

    def synthesize(self, text: str, output_path: Path) -> dict:
        """
        Convert text to speech using Azure OpenAI TTS.

        Uses atomic file write pattern (temp file + rename) to prevent
        corruption from interrupted generation. Wraps all Azure OpenAI
        exceptions in TTSError for consistent error handling.

        Args:
            text: Preprocessed script text
            output_path: Destination path for MP3 file

        Returns:
            dict: Metadata with path, size_bytes, size_mb, provider, voice, model

        Raises:
            TTSError: Azure OpenAI API error (wrapped from APIError, RateLimitError, etc.)
        """
        # Create directory if doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare temp file path for atomic write
        temp_path = output_path.with_suffix('.tmp')

        logger.info(
            "azure_tts_synthesize_started",
            output_path=str(output_path),
            text_length=len(text),
            voice=self.voice,
            model=self.model
        )

        try:
            # Call Azure OpenAI TTS
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                response_format=self.response_format,
                speed=self.speed
            )

            # Stream to temp file first (atomic write step 1)
            response.stream_to_file(str(temp_path))

            # Atomic rename to final path (atomic write step 2)
            temp_path.rename(output_path)

            # Get file metadata
            file_size = output_path.stat().st_size

            logger.info(
                "azure_tts_synthesize_complete",
                output_path=str(output_path),
                size_bytes=file_size,
                size_mb=round(file_size / 1_048_576, 2)
            )

            return {
                "path": str(output_path),
                "size_bytes": file_size,
                "size_mb": round(file_size / 1_048_576, 2),
                "provider": "azure",
                "voice": self.voice,
                "model": self.model
            }

        except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
            # Translate Azure OpenAI exceptions to common TTSError
            logger.error(
                "azure_tts_api_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise TTSError(f"Azure OpenAI TTS failed: {e}") from e

        except Exception as e:
            # Catch any other exceptions (file I/O errors, etc.)
            logger.error(
                "azure_tts_unexpected_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise TTSError(f"Azure TTS unexpected error: {e}") from e

        finally:
            # Clean up temp file if exists
            if temp_path.exists():
                temp_path.unlink()

    @property
    def provider_name(self) -> str:
        """Return provider name for logging."""
        return "azure"
