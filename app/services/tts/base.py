"""
Abstract base class for TTS providers.

Defines the TTSProvider interface that all TTS implementations must follow,
enabling transparent provider swapping for failover resilience.
"""
from abc import ABC, abstractmethod
from pathlib import Path


class TTSError(Exception):
    """Common exception raised by all TTS providers on failure."""
    pass


class TTSProvider(ABC):
    """
    Abstract base class for text-to-speech providers.

    All TTS provider implementations (Azure, ElevenLabs) must inherit from this
    class and implement the synthesize() method and provider_name property.

    This enables the Strategy pattern where providers can be swapped transparently
    for automatic failover from primary to fallback provider.
    """

    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> dict:
        """
        Convert text to speech and write MP3 file.

        Implementations must:
        - Create parent directories if needed
        - Use atomic file writes (temp file + rename) to prevent corruption
        - Translate all provider-specific exceptions to TTSError
        - Return metadata dict with standard keys

        Args:
            text: Preprocessed script text (TTS-ready, already normalized)
            output_path: Destination path for MP3 file

        Returns:
            dict: Metadata with keys:
                - path (str): Final MP3 file path
                - size_bytes (int): File size in bytes
                - size_mb (float): File size in megabytes (rounded to 2 decimals)
                - provider (str): Provider name ("azure" or "elevenlabs")
                - voice (str): Voice ID/name used
                - model (str): Model ID used

        Raises:
            TTSError: Provider-specific error translated to common exception
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Return provider name for logging and metrics.

        Returns:
            str: Provider identifier ("azure" or "elevenlabs")
        """
        pass
