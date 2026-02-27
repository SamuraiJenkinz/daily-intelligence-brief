# Phase 18: TTS Provider Resilience - Research

**Researched:** 2026-02-27
**Domain:** Text-to-Speech API failover and provider abstraction
**Confidence:** HIGH

## Summary

Phase 18 adds resilience to audio generation by implementing provider abstraction and automatic failover from Azure OpenAI TTS to ElevenLabs TTS. The standard approach uses the Strategy pattern with abstract base classes to create a unified TTSProvider interface, allowing providers to be swapped transparently. Failover is implemented using simple try/except blocks rather than complex circuit breakers, as TTS operations are one-shot (no repeated calls) and failures are immediately actionable.

ElevenLabs provides a well-documented Python SDK with similar API patterns to Azure OpenAI TTS (text input → MP3 output), making integration straightforward. Both providers support MP3 format, plain text input, and similar voice quality, though ElevenLabs is more expensive ($0.24-$0.30 per 1K characters vs Azure's $15-16 per 1M characters). The abstraction layer should handle authentication, voice selection, error translation, and logging while preserving the existing atomic file write and idempotent generation patterns.

**Primary recommendation:** Use abstract base class TTSProvider with AzureTTSProvider (primary) and ElevenLabsTTSProvider (fallback). Implement simple try/except failover in AudioBriefingService._convert_to_audio() with api_events logging. No circuit breaker needed for one-shot operations.

## Standard Stack

The established libraries/tools for TTS provider resilience:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| elevenlabs | Latest (2.x+) | ElevenLabs TTS SDK | Official Python SDK, well-documented, similar API to OpenAI |
| openai | 2.16.0 (existing) | Azure OpenAI TTS | Already integrated, primary provider |
| abc | stdlib | Abstract base classes | Python standard for interface definition |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | Existing | Retry with exponential backoff | Already used for Azure TTS retries, keep existing pattern |
| structlog | Existing | Structured logging | Already used, extend for failover events |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Simple try/except | Circuit breaker (pybreaker) | Circuit breaker adds complexity for one-shot operations with no benefit |
| ElevenLabs | Google Cloud TTS, Azure Speech | ElevenLabs has better quality (4.14 MOS) and simpler API than alternatives |
| Strategy pattern | Factory pattern | Factory is overkill; Strategy pattern is clearer for two providers |

**Installation:**
```bash
pip install elevenlabs
```

## Architecture Patterns

### Recommended Project Structure
```
app/services/
├── tts/
│   ├── __init__.py
│   ├── base.py              # Abstract TTSProvider base class
│   ├── azure_provider.py    # AzureTTSProvider implementation
│   └── elevenlabs_provider.py  # ElevenLabsTTSProvider implementation
├── audio_generator.py       # Updated to use TTSProvider abstraction
└── ...
```

### Pattern 1: Abstract Base Class for Provider Interface
**What:** Define TTSProvider ABC with synthesize() method that all providers implement
**When to use:** Any multi-provider integration requiring transparent swapping
**Example:**
```python
# Source: Python abc module docs + Strategy pattern best practices
from abc import ABC, abstractmethod
from pathlib import Path

class TTSProvider(ABC):
    """Abstract base class for text-to-speech providers."""

    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> dict:
        """
        Convert text to speech and write MP3 file.

        Args:
            text: Preprocessed script text
            output_path: Destination path for MP3 file

        Returns:
            dict: Metadata with path, size_bytes, size_mb, voice, model, provider

        Raises:
            TTSError: Provider-specific error translated to common exception
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name for logging (e.g., 'azure', 'elevenlabs')."""
        pass
```

### Pattern 2: Simple Failover with Try/Except
**What:** Try primary provider, catch specific errors, fall back to secondary provider
**When to use:** One-shot operations (not repeated calls in loops), clear failure modes
**Example:**
```python
# Source: Simple failover pattern best practices
def _convert_to_audio(self, script: str, output_path: Path) -> dict:
    """Convert script to audio with automatic failover."""

    # Try primary provider (Azure)
    try:
        result = self.primary_provider.synthesize(script, output_path)
        self._log_success(self.primary_provider.provider_name, result)
        return result

    except TTSError as e:
        # Log failure and attempt fallback
        self._log_failure(self.primary_provider.provider_name, str(e))
        logger.warning(
            "tts_failover_initiated",
            primary=self.primary_provider.provider_name,
            fallback=self.fallback_provider.provider_name,
            error=str(e)
        )

        # Try fallback provider (ElevenLabs)
        result = self.fallback_provider.synthesize(script, output_path)
        self._log_success(self.fallback_provider.provider_name, result, fallback=True)
        return result
```

### Pattern 3: Provider-Specific Error Translation
**What:** Translate provider-specific exceptions to common TTSError exception
**When to use:** Abstracting different API error types from multiple providers
**Example:**
```python
# Source: Exception abstraction patterns
class TTSError(Exception):
    """Common TTS error raised by all providers."""
    pass

class AzureTTSProvider(TTSProvider):
    def synthesize(self, text: str, output_path: Path) -> dict:
        try:
            # Azure-specific TTS call
            response = self.client.audio.speech.create(...)
            ...
        except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
            # Translate to common exception
            raise TTSError(f"Azure TTS failed: {e}") from e
```

### Pattern 4: API Event Logging for Failover
**What:** Log TTS API events to api_events table following existing project pattern
**When to use:** Track failover events for admin dashboard visibility
**Example:**
```python
# Source: Existing api_events pattern from app/models/api_event.py
from app.models.api_event import ApiEvent, ApiEventType

# Add new event types to ApiEventType enum
class ApiEventType(str, enum.Enum):
    # ... existing types
    TTS_SUCCESS = "tts_success"
    TTS_FALLBACK = "tts_fallback"

# Log successful TTS call
def _log_success(self, provider: str, result: dict, fallback: bool = False):
    event = ApiEvent(
        event_type=ApiEventType.TTS_FALLBACK if fallback else ApiEventType.TTS_SUCCESS,
        api_name="tts",
        success=True,
        detail=json.dumps({"provider": provider, "size_mb": result["size_mb"]}),
        run_id=self.current_run_id  # If available
    )
    db.add(event)
    db.commit()
```

### Anti-Patterns to Avoid
- **Circuit Breaker for One-Shot Operations:** Circuit breakers are designed for repeated calls to detect persistent failures. TTS generation is one-shot per briefing (4 calls per day), so circuit breaker state is never useful. Simple try/except is clearer.
- **Retry on Fallback Provider Failure:** If both providers fail, fail fast rather than retrying. Log error for manual investigation.
- **Synchronous HTTP Client for Async-Native APIs:** ElevenLabs SDK supports async; if async audio generation is needed later, use AsyncElevenLabs from the start.
- **Hardcoded Voice IDs:** Voice selection should be configurable via Settings to allow easy voice matching adjustments.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ElevenLabs API client | Custom HTTP client with requests | elevenlabs Python SDK | Official SDK handles auth, retries, streaming, model selection, error codes |
| Abstract base classes | Duck typing with isinstance checks | abc.ABC + @abstractmethod | Enforces interface at class definition time, catches errors early |
| Provider configuration | If/else chains in main code | Settings + factory pattern | Cleaner configuration, easier to add providers later |
| Audio format conversion | Custom ffmpeg wrappers | Both APIs output MP3 natively | Unnecessary complexity, both support mp3_44100_128 |
| Retry logic for ElevenLabs | Manual retry loops | tenacity (if needed) | Already used for Azure, consistent pattern |

**Key insight:** The official ElevenLabs SDK handles authentication, error codes, streaming, and model selection. Building a custom HTTP client wastes time and misses edge cases (retry headers, rate limit parsing, auth token refresh). Use the SDK.

## Common Pitfalls

### Pitfall 1: Voice Mismatch Between Providers
**What goes wrong:** Azure "nova" voice and ElevenLabs default voice sound noticeably different, breaking user experience during failover
**Why it happens:** Each provider has different voice IDs and characteristics; "nova" doesn't exist in ElevenLabs
**How to avoid:**
- Research ElevenLabs voice library for closest match to "nova" (warm, professional female voice)
- Make voice selection configurable via Settings (elevenlabs_voice_id env var)
- Document voice pairing in README for easy adjustment
**Warning signs:** User complaints about voice changes, inconsistent audio quality

### Pitfall 2: Cost Explosion from Fallback
**What goes wrong:** ElevenLabs is 10x+ more expensive than Azure ($0.24/1K chars vs $15/1M chars), causing unexpected bills
**Why it happens:** Azure pricing is per 1M characters, ElevenLabs is per 1K characters (different units)
**How to avoid:**
- Log fallback events prominently (api_events table) for cost tracking
- Alert if fallback rate exceeds threshold (e.g., >10% of requests)
- Consider fallback as temporary solution, not permanent state
- Document cost implications in runbook
**Warning signs:** Azure outage → all briefings use ElevenLabs → $100/month becomes $1000/month

### Pitfall 3: Rate Limit Differences
**What goes wrong:** Azure and ElevenLabs have different rate limits; fallback hits ElevenLabs rate limit immediately
**Why it happens:** ElevenLabs free/starter tiers have low concurrent request limits (2-3), MDInsights generates 4 briefings sequentially
**What's unclear:** Exact Azure OpenAI TTS rate limits (calculated as 6 RPM per 1000 TPM allocation)
**Recommendation:**
- Check ElevenLabs plan concurrent limits (free: 2, starter: 3, creator: 5)
- MDInsights generates 4 briefings sequentially, so needs 1 concurrent request (safe for all tiers)
- If parallel generation is added later, implement request queuing

### Pitfall 4: Incomplete Error Translation
**What goes wrong:** Provider-specific exceptions leak through abstraction, breaking encapsulation
**Why it happens:** Each provider has unique error types (openai.APIError vs elevenlabs.core.api_error.ApiError)
**How to avoid:**
- Catch all provider-specific exceptions in provider implementations
- Translate to common TTSError with original exception chained (.from e)
- Never let provider-specific exceptions propagate to AudioBriefingService
**Warning signs:** Type errors in exception handlers, provider imports in audio_generator.py

### Pitfall 5: Missing Atomic Write in Fallback Path
**What goes wrong:** Fallback provider writes directly to output_path, corrupting file if interrupted
**Why it happens:** Copy-paste from different code path, forgetting temp file pattern
**How to avoid:**
- Both providers must use temp file + rename pattern (already in Azure implementation)
- Unit tests should verify atomic writes for both providers
- Code review checklist includes atomic write verification
**Warning signs:** Corrupted MP3 files after interruptions, files smaller than 100KB

### Pitfall 6: No Validation of Fallback During Development
**What goes wrong:** Fallback path is never tested until production failure, reveals bugs during outage
**Why it happens:** Azure OpenAI is reliable, fallback seems like "insurance" that won't be used
**How to avoid:**
- Create test script that simulates Azure TTS failure (mock or env var flag)
- Verify ElevenLabs generates audio successfully
- Test api_events logging for TTS_FALLBACK event
- Run fallback test in CI/CD pipeline
**Warning signs:** No evidence of fallback testing, no test coverage for ElevenLabs provider

## Code Examples

Verified patterns from official sources:

### ElevenLabs Basic Usage
```python
# Source: https://github.com/elevenlabs/elevenlabs-python
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key="YOUR_API_KEY")

# Generate audio
audio = client.text_to_speech.convert(
    text="Hello, this is a test.",
    voice_id="JBFqnCBsd6RMkjVDRZzb",  # Example voice ID
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128"
)

# Audio is returned as bytes, write to file
with open("output.mp3", "wb") as f:
    f.write(audio)
```

### ElevenLabs with Environment Variable Auth
```python
# Source: ElevenLabs SDK documentation
import os
from elevenlabs.client import ElevenLabs

# SDK automatically reads ELEVENLABS_API_KEY environment variable
client = ElevenLabs()  # No explicit api_key needed if env var set

audio = client.text_to_speech.convert(
    text="Your text here",
    voice_id="voice_id_here",
    model_id="eleven_multilingual_v2"
)
```

### Abstract Base Class Pattern
```python
# Source: https://docs.python.org/3/library/abc.html
from abc import ABC, abstractmethod

class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> dict:
        """Convert text to speech."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name."""
        pass

# Cannot instantiate ABC directly
provider = TTSProvider()  # Raises TypeError

# Subclass must implement all abstract methods
class AzureTTSProvider(TTSProvider):
    def synthesize(self, text: str, output_path: Path) -> dict:
        # Implementation
        return {"path": str(output_path), "provider": "azure"}

    @property
    def provider_name(self) -> str:
        return "azure"
```

### Simple Failover Pattern
```python
# Source: Resilient APIs best practices + project requirements
class AudioBriefingService:
    def __init__(self):
        # Initialize providers
        self.primary_provider = AzureTTSProvider()
        self.fallback_provider = ElevenLabsTTSProvider()

    def _convert_to_audio(self, script: str, output_path: Path) -> dict:
        """Convert script to audio with automatic failover."""

        # Try primary provider
        try:
            logger.info("tts_attempting_primary", provider="azure")
            return self.primary_provider.synthesize(script, output_path)

        except TTSError as e:
            # Log primary failure
            logger.warning(
                "tts_primary_failed",
                provider="azure",
                error=str(e),
                fallback="elevenlabs"
            )

            # Log to api_events table
            self._log_api_event(
                event_type=ApiEventType.TTS_FALLBACK,
                provider="azure",
                success=False,
                detail=str(e)
            )

            # Try fallback provider
            logger.info("tts_attempting_fallback", provider="elevenlabs")
            result = self.fallback_provider.synthesize(script, output_path)

            # Log successful fallback
            self._log_api_event(
                event_type=ApiEventType.TTS_FALLBACK,
                provider="elevenlabs",
                success=True,
                detail={"size_mb": result["size_mb"]}
            )

            return result
```

### Atomic File Write Pattern (Preserve Existing)
```python
# Source: Existing app/services/audio_generator.py pattern
def synthesize(self, text: str, output_path: Path) -> dict:
    """Generate audio with atomic write."""

    # Create directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first
    temp_path = output_path.with_suffix('.tmp')

    try:
        # Generate audio (provider-specific)
        audio_bytes = self._generate_audio(text)

        # Write to temp file
        temp_path.write_bytes(audio_bytes)

        # Atomic rename to final path
        temp_path.rename(output_path)

        # Get metadata
        file_size = output_path.stat().st_size
        return {
            "path": str(output_path),
            "size_bytes": file_size,
            "size_mb": round(file_size / 1_048_576, 2),
            "provider": self.provider_name
        }

    finally:
        # Clean up temp file if exists
        if temp_path.exists():
            temp_path.unlink()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded TTS provider | Abstract provider interface | 2023+ (microservices era) | Easier provider swapping, better testing |
| Retry on all errors | Failover to secondary provider | 2024+ (multi-cloud) | Better availability, handles prolonged outages |
| Circuit breaker everywhere | Simple try/except for one-shot ops | 2025+ (pragmatic resilience) | Simpler code, circuit breaker only for repeated calls |
| Custom HTTP clients | Official SDKs | 2024+ (SDK maturity) | Fewer bugs, better error handling, free updates |
| ElevenLabs V2 | ElevenLabs V3 (70+ languages, audio tags) | 2025 | Better quality, emotion control (not needed for MDInsights) |

**Deprecated/outdated:**
- Multi-source TTS with weighted selection: Overly complex for 2-provider fallback scenario
- Building custom retry logic: tenacity library handles this better
- Circuit breaker for one-shot operations: Adds complexity with no benefit

## Open Questions

Things that couldn't be fully resolved:

1. **Exact Azure OpenAI TTS Rate Limits**
   - What we know: Calculated as 6 RPM per 1000 TPM allocation (subscription-specific)
   - What's unclear: MDInsights' actual TPM allocation and resulting RPM limit
   - Recommendation: Check Azure portal for deployment limits, likely sufficient for 4 sequential briefings

2. **Best ElevenLabs Voice to Match Azure "nova"**
   - What we know: Azure "nova" is warm, professional female voice; ElevenLabs has 5000+ voices
   - What's unclear: Which ElevenLabs voice_id most closely matches "nova" characteristics
   - Recommendation: Test 3-5 professional female voices from ElevenLabs voice library, select based on subjective quality match; make voice_id configurable for easy adjustment

3. **Should Fallback Be Temporary or Permanent?**
   - What we know: ElevenLabs is 10x+ more expensive, suggesting fallback should be temporary
   - What's unclear: Whether system should automatically revert to Azure after recovery, or continue with ElevenLabs
   - Recommendation: Keep fallback permanent for duration of run (don't revert mid-day); log fallback events for monitoring; Azure recovery happens naturally on next run

4. **Async vs Sync TTS Calls**
   - What we know: Current implementation is synchronous, ElevenLabs SDK supports async
   - What's unclear: Whether Phase 18 should implement async TTS for parallel generation
   - Recommendation: Keep synchronous for Phase 18 (4 sequential briefings, <5 min total); async can be added later if parallel generation is needed

5. **Should Circuit Breaker Be Added for Future-Proofing?**
   - What we know: Circuit breaker is standard for microservices, but adds complexity for one-shot operations
   - What's unclear: Whether daily pipeline execution pattern might change to repeated calls
   - Recommendation: No circuit breaker in Phase 18; add in later phase if execution pattern changes (e.g., hourly briefings, API endpoint for on-demand generation)

## Sources

### Primary (HIGH confidence)
- [ElevenLabs Python SDK GitHub](https://github.com/elevenlabs/elevenlabs-python) - Official SDK, installation, basic usage
- [ElevenLabs Text-to-Speech API Documentation](https://elevenlabs.io/docs/api-reference/text-to-speech/convert) - API parameters, authentication, formats, response
- [Python abc Module Documentation](https://docs.python.org/3/library/abc.html) - Abstract base class patterns
- [Azure OpenAI Service Pricing](https://azure.microsoft.com/en-us/pricing/details/azure-openai/) - TTS pricing per character
- [ElevenLabs API Pricing](https://elevenlabs.io/pricing/api) - Per-character pricing, plan limits

### Secondary (MEDIUM confidence)
- [OpenAI Error Codes Documentation](https://platform.openai.com/docs/guides/error-codes) - API error types for Azure OpenAI TTS
- [ElevenLabs Rate Limits Help](https://help.elevenlabs.io/hc/en-us/articles/14312733311761-How-many-requests-can-I-make-and-can-I-increase-it) - Concurrent request limits per plan
- [Resilient APIs: Retry Logic, Circuit Breakers, and Fallback Mechanisms](https://medium.com/@fahimad/resilient-apis-retry-logic-circuit-breakers-and-fallback-mechanisms-cfd37f523f43) - Best practices for failover patterns
- [Building Resilient Python Applications with Tenacity](https://www.amitavroy.com/articles/building-resilient-python-applications-with-tenacity-smart-retries-for-a-fail-proof-architecture) - Retry and failover strategies
- [Strategy Design Pattern in Python](https://refactoring.guru/design-patterns/strategy/python/example) - Strategy pattern implementation

### Tertiary (LOW confidence)
- [ElevenLabs vs Azure OpenAI TTS Comparison](https://aloa.co/ai/comparisons/ai-voice-comparison/elevenlabs-vs-azure-speech) - Voice quality comparison (4.14 MOS for ElevenLabs)
- [ElevenLabs Voice Library - Adult Female Voices](https://elevenlabs.io/voice-library/adult-female-voices) - Voice selection options
- [CircuitBreaker PyPI](https://pypi.org/project/circuitbreaker/) - Circuit breaker library (not recommended for Phase 18)
- [TTS Wrappers GitHub](https://github.com/VPetukhov/tts-wrappers) - Example of TTS abstraction (limited to Google, Yandex, ElevenLabs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official ElevenLabs SDK well-documented, abc module is stdlib, existing libraries proven
- Architecture: HIGH - Strategy pattern is standard for provider abstraction, simple failover well-established for one-shot operations
- Pitfalls: MEDIUM - Cost explosion and voice mismatch are known issues, but impact is project-specific; rate limits require Azure portal check

**Research date:** 2026-02-27
**Valid until:** 60 days (TTS APIs are stable, pricing changes quarterly, SDK updates monthly)
