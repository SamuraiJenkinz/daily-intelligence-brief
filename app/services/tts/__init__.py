"""
TTS provider abstraction package for text-to-speech provider resilience.

Provides abstract TTSProvider interface and implementations for Azure OpenAI TTS
and ElevenLabs TTS with automatic failover support.
"""
from app.services.tts.base import TTSProvider, TTSError
from app.services.tts.azure_provider import AzureTTSProvider
from app.services.tts.elevenlabs_provider import ElevenLabsTTSProvider

__all__ = ["TTSProvider", "TTSError", "AzureTTSProvider", "ElevenLabsTTSProvider"]
