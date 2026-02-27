# Stack Research: Audio Intelligence Briefings

**Domain:** Audio intelligence briefings (TTS + podcast generation)
**Researched:** 2026-02-27
**Confidence:** HIGH

## Executive Summary

Add Azure OpenAI TTS capability to existing MDInsights Python/FastAPI stack with **minimal dependencies**. Azure OpenAI provides native MP3 output via `/audio/speech` endpoint, eliminating need for audio manipulation libraries. Existing `openai` package supports TTS, FastAPI's `FileResponse` handles streaming, Python's stdlib `email.mime` handles attachments. **Zero new major dependencies required** - only need to upgrade `openai` package from 2.16.0 → 2.24.0.

---

## Recommended Stack

### Core Technologies (Upgrade Only)

| Technology | Current Version | New Version | Purpose | Why Recommended |
|------------|-----------------|-------------|---------|-----------------|
| `openai` | 2.16.0 | **2.24.0** | Azure OpenAI TTS via `client.audio.speech.create()` | Official SDK, mature API, native MP3 output, Windows compatible |

**Rationale:** The existing `openai` package already includes TTS support via `client.audio.speech.create()` method. Upgrading to 2.24.0 (latest as of Feb 2026) ensures access to newest models and bug fixes.

### Existing Stack (Already Sufficient)

| Technology | Current Version | Purpose | Why Already Sufficient |
|------------|-----------------|---------|------------------------|
| FastAPI | 0.115.0 | Serve audio files via `FileResponse` | Built-in `FileResponse` handles streaming, MIME types, and browser compatibility |
| Python stdlib | 3.11+ | Email attachments via `email.mime.audio.MIMEAudio` | Standard library handles MP3 attachments, base64 encoding, MIME types |
| httpx | (current) | HTTP client for TTS API calls | Already used throughout codebase, supports async operations |
| structlog | (current) | Logging TTS operations | Already used for structured logging |
| tenacity | (current) | Retry logic for TTS API failures | Already used for retry logic |

---

## Azure OpenAI TTS API Specifications

### Models Available

| Model | Quality | Latency | Use Case |
|-------|---------|---------|----------|
| **tts-1** | Standard | Low (~200-400ms) | Real-time, streaming applications |
| **tts-1-hd** | High-definition | Higher | High-quality podcast/briefing production |
| gpt-4o-mini-tts | Customizable | Variable | Advanced voice control (instructions support) |

**Recommendation:** Use **tts-1-hd** for insurance briefings. Quality matters more than latency for asynchronous morning delivery. tts-1-hd provides professional audio quality suitable for business use.

### Voices Available

| Voice | Characteristics | Recommendation |
|-------|----------------|----------------|
| alloy | Neutral, balanced | ✅ Good default for professional briefings |
| echo | Calm, measured | ✅ Suitable for compliance/serious content |
| fable | Expressive, storytelling | Consider for engaging broker content |
| onyx | Deep, authoritative | ✅ Good for leadership briefings |
| nova | Friendly, warm | Consider for general audience |
| shimmer | Soft, clear | Consider for detailed analysis |

**Recommendation:** Test `alloy` (neutral professional), `echo` (calm/measured), and `onyx` (authoritative) for insurance audience. Avoid overly expressive voices for market intelligence content.

### Audio Formats

| Format | Default | Compression | File Size | Browser Support | Recommendation |
|--------|---------|-------------|-----------|-----------------|----------------|
| **mp3** | ✅ Yes | Lossy | ~1 MB/min @ 128kbps | Universal | ✅ **Use this** |
| opus | No | Lossy | ~0.5 MB/min | Modern browsers | Skip (compatibility) |
| aac | No | Lossy | ~1 MB/min | Good | Skip (MP3 more universal) |
| flac | No | Lossless | ~5 MB/min | Limited | Skip (unnecessary size) |
| wav | No | Uncompressed | ~10 MB/min | Universal | Skip (massive size) |
| pcm16 | No | Raw audio | ~10 MB/min | No direct playback | Skip (requires processing) |

**Recommendation:** Use **MP3 (default)**. Azure OpenAI outputs MP3 natively at 128kbps (~1 MB/min), providing excellent quality-to-size ratio. Universal browser support, no transcoding needed.

### File Size Estimates

| Duration | MP3 @ 128kbps | MP3 @ 192kbps | Email Impact |
|----------|---------------|---------------|--------------|
| 2 minutes | ~2 MB | ~3 MB | ✅ Well within 10MB limit |
| 5 minutes | ~5 MB | ~7.5 MB | ✅ Comfortable margin |
| 10 minutes | ~10 MB | ~15 MB | ⚠️ Approaching limits |

**Analysis:** 2-5 minute briefings = 2-5 MB per MP3. With 4 role-based briefings, total audio payload = 8-20 MB. Each email contains only ONE role's audio (~2-5 MB), staying well within typical 10-25 MB email attachment limits.

### API Endpoints

**Text-to-Speech Endpoint:**
```
POST {azure_endpoint}/openai/deployments/{deployment_name}/audio/speech
API Version: 2025-04-01-preview
```

**Required Parameters:**
- `model`: "tts-1" or "tts-1-hd"
- `voice`: "alloy", "echo", "fable", "onyx", "nova", "shimmer"
- `input`: Text to synthesize (max length TBD - test with 500-1000 words)

**Optional Parameters:**
- `response_format`: "mp3" (default), "opus", "aac", "flac", "wav", "pcm"
- `speed`: 0.25 to 4.0 (default 1.0) - consider 1.1x for time savings

**Response:** Binary audio data (MP3 bytes)

---

## Installation

### Upgrade Existing Package

```bash
# Upgrade openai package to latest
pip install --upgrade openai==2.24.0

# Or update requirements.txt:
# openai==2.24.0  # (upgraded from 2.16.0 for TTS support)
```

**No new packages required.** All other functionality uses existing stack.

---

## Integration Points

### 1. Azure OpenAI Client (Existing)

```python
from openai import AzureOpenAI

# Use existing Azure OpenAI client initialization pattern
client = AzureOpenAI(
    api_key=settings.azure_openai_api_key,
    api_version="2025-04-01-preview",  # Add TTS-specific version
    azure_endpoint=settings.azure_openai_endpoint
)

# Generate audio
response = client.audio.speech.create(
    model="tts-1-hd",  # Deploy this model in Azure
    voice="alloy",
    input="Your briefing text here...",
    response_format="mp3"
)

# Save to file
with open("briefing.mp3", "wb") as f:
    f.write(response.content)
```

**Integration:** Reuse existing `AzureOpenAI` client setup. Add TTS-specific API version for audio endpoint. Binary response writes directly to file.

### 2. FastAPI Audio Serving (Existing)

```python
from fastapi import FastAPI
from fastapi.responses import FileResponse

@app.get("/audio/{briefing_id}.mp3")
async def stream_audio(briefing_id: str):
    audio_path = f"./audio/{briefing_id}.mp3"
    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=f"briefing_{briefing_id}.mp3"
    )
```

**Integration:** FastAPI's `FileResponse` handles:
- Streaming (reads file in chunks, doesn't load into memory)
- MIME type (`audio/mpeg` for MP3)
- Browser compatibility (modern browsers support HTML5 `<audio>` tag)
- Range requests (for seekable playback) - built into `FileResponse`

### 3. Email Attachments (Python stdlib)

```python
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio

# Create email
msg = MIMEMultipart()
msg['Subject'] = "Your Daily Insurance Intelligence Brief"

# Add HTML body (existing Jinja2 template)
html_part = MIMEText(html_content, 'html')
msg.attach(html_part)

# Add MP3 attachment
with open("briefing.mp3", "rb") as audio_file:
    audio_data = audio_file.read()
    audio_part = MIMEAudio(audio_data, _subtype="mpeg")
    audio_part.add_header(
        'Content-Disposition',
        'attachment',
        filename='daily_briefing.mp3'
    )
    msg.attach(audio_part)

# Send via existing email client (MMC Core API or Graph API)
```

**Integration:** Python's `email.mime.audio.MIMEAudio` handles:
- MP3 MIME type (`audio/mpeg`)
- Base64 encoding (automatic)
- Proper Content-Disposition headers
- Works with existing MMC Core API email sending

### 4. Browser Audio Player (HTML5)

```html
<!-- Add to existing Jinja2 email template -->
<audio controls style="width: 100%; max-width: 500px;">
    <source src="{{ audio_streaming_url }}" type="audio/mpeg">
    Your browser does not support the audio element.
    <a href="{{ audio_streaming_url }}" download>Download Audio Briefing</a>
</audio>
```

**Integration:** HTML5 `<audio>` element provides:
- Play/pause controls
- Seek bar (scrubbing)
- Volume control
- Download fallback
- Universal browser support (Chrome, Firefox, Safari, Edge)

---

## Alternatives Considered

| Recommended | Alternative | Why Not Alternative |
|-------------|-------------|---------------------|
| **Azure OpenAI TTS** | ElevenLabs API | More expensive, external dependency, no Azure integration |
| **Azure OpenAI TTS** | Google Cloud TTS | Different cloud provider, migration complexity, no existing credentials |
| **Azure OpenAI TTS** | AWS Polly | Different cloud provider, less natural voices |
| **Azure OpenAI TTS** | Azure Speech Services | Separate SDK, less natural voices, more complex API |
| **MP3 format** | Opus format | Limited browser support, compatibility risk |
| **MP3 format** | WAV format | 10x larger files, email size limits |
| **FastAPI FileResponse** | Custom streaming implementation | FileResponse already handles range requests, chunking |
| **Python email.mime** | Third-party email library | Standard library sufficient, no need for external dependency |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **ffmpeg** | Unnecessary - Azure outputs MP3 directly | Native Azure OpenAI MP3 output |
| **pydub** | Audio manipulation not needed | Direct binary file handling |
| **mutagen** | Metadata editing not required for streaming | Standard file operations |
| **soundfile** | Format conversion not needed | Azure outputs target format |
| **Custom audio processing** | Over-engineering, adds complexity | Use Azure's native MP3 output |
| **WebSocket streaming** | Unnecessary for async delivery | Simple file attachment + streaming URL |
| **gRPC for audio** | Over-complicated for use case | REST API + FastAPI FileResponse |

**Key Insight:** Azure OpenAI TTS outputs production-ready MP3 files. No audio processing, transcoding, or manipulation needed. Treat as binary blob: generate → save → serve/attach.

---

## Version Compatibility

### Python Package Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| openai 2.24.0 | Python 3.8+ | Compatible with Python 3.11+ (MDInsights) |
| openai 2.24.0 | azure-identity (current) | Works with existing Azure auth |
| openai 2.24.0 | httpx (current) | SDK uses httpx internally |
| openai 2.24.0 | pydantic 2.11.0 | Compatible with Pydantic v2 |
| FastAPI 0.115.0 | FileResponse audio streaming | Native support, no upgrade needed |
| Python 3.11+ | email.mime.audio | Standard library, no version issues |

### Azure OpenAI API Compatibility

| API Version | TTS Support | Status | Recommendation |
|-------------|-------------|--------|----------------|
| 2024-02-01 | No | Deprecated | Do not use |
| 2024-08-01-preview | Partial | Preview | Skip |
| **2025-04-01-preview** | ✅ Full TTS | Current | ✅ **Use this** |

**Note:** API version for TTS (`2025-04-01-preview`) is separate from chat completions version. Can use different versions for different endpoints.

### Windows Compatibility

| Component | Windows Server | Windows 11 Dev | Notes |
|-----------|----------------|----------------|-------|
| openai 2.24.0 | ✅ Compatible | ✅ Compatible | Pure Python, no platform-specific deps |
| MP3 file handling | ✅ Compatible | ✅ Compatible | Binary file I/O, no OS-specific codecs |
| FastAPI FileResponse | ✅ Compatible | ✅ Compatible | Uses Starlette, Windows-compatible |
| email.mime | ✅ Compatible | ✅ Compatible | Python stdlib, cross-platform |

**Windows Server on AWS:** No compatibility issues. All stack components are pure Python or stdlib, no Linux-specific dependencies.

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **Azure OpenAI Studio** | Test TTS voices and models | Web UI for experimenting with voices before coding |
| **Browser DevTools** | Test audio playback | Verify HTML5 audio element works across browsers |
| **Email testing services** | Test MP3 attachments | Use Mailtrap/MailHog to verify attachments render correctly |
| **File size monitoring** | Track MP3 sizes | Ensure 2-5 min briefings stay under email limits |

---

## Performance Considerations

### TTS Generation Time

| Model | Speed | Typical Time for 500 words |
|-------|-------|---------------------------|
| tts-1 | ~10x realtime | ~30 seconds |
| tts-1-hd | ~5x realtime | ~60 seconds |

**Implication:** Generating 4 role-based briefings (500-1000 words each) takes 2-5 minutes total. Acceptable for asynchronous morning delivery workflow.

### Concurrency

- **Sequential generation:** 5 minutes for 4 briefings
- **Parallel generation:** 1-2 minutes for 4 briefings (httpx async support)

**Recommendation:** Use async/await with existing `httpx` async client for parallel TTS generation. Existing codebase already uses async patterns.

### Caching Strategy

- **Cache key:** `hash(briefing_text + voice + model)`
- **Cache duration:** 24 hours (briefings regenerated daily)
- **Cache storage:** Local filesystem (same as current briefing cache)
- **Cache hit benefit:** Skip TTS API call, serve cached MP3

**Implication:** If briefing content hasn't changed, reuse cached audio. Reduces API costs and generation time.

---

## Cost Analysis

### Azure OpenAI TTS Pricing

**As of 2026:** ~$15 per 1 million characters (standard rate for neural TTS)

**MDInsights Usage Estimate:**
- 4 briefings/day × 1000 words/briefing = 4,000 words/day
- 4,000 words × 6 characters/word = 24,000 characters/day
- 24,000 characters × 30 days = 720,000 characters/month
- Cost: ~$10.80/month for TTS

**Conclusion:** TTS cost is negligible compared to GPT-4o summarization costs (which already process thousands of articles daily).

---

## Security Considerations

### Audio File Storage

- **Location:** Same security boundary as HTML briefings
- **Access control:** Authenticated endpoints (existing auth middleware)
- **Retention:** Same 30-day retention policy as briefings
- **Encryption:** HTTPS for streaming, encrypted storage (Windows EFS or Azure Storage)

### Email Attachment Security

- **MIME type validation:** Enforce `audio/mpeg` only
- **File size limits:** Reject files >25 MB (email server limits)
- **Malware scanning:** Same antivirus scanning as existing email attachments

### API Key Management

- **Existing pattern:** Azure OpenAI key already in environment variables
- **No changes needed:** Same key works for chat completions and TTS

---

## Testing Strategy

### Unit Tests

```python
# Test TTS generation
def test_generate_audio_briefing():
    audio_bytes = generate_tts(text="Test briefing", voice="alloy")
    assert len(audio_bytes) > 0
    assert audio_bytes[:3] == b'ID3'  # MP3 header

# Test audio serving
def test_audio_endpoint():
    response = client.get("/audio/test_briefing.mp3")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"

# Test email attachment
def test_email_with_audio():
    email = create_briefing_email(html_content, audio_path="test.mp3")
    assert any(part.get_content_type() == "audio/mpeg" for part in email.walk())
```

### Integration Tests

- **End-to-end:** Generate briefing → TTS → Save MP3 → Serve via FastAPI → Verify playback
- **Email delivery:** Send test email with MP3 attachment → Verify receipt in test inbox
- **Browser compatibility:** Test HTML5 audio playback in Chrome, Firefox, Safari, Edge

---

## Migration Path

### Phase 1: Setup (No breaking changes)

1. Upgrade `openai` package: `pip install --upgrade openai==2.24.0`
2. Deploy TTS model in Azure OpenAI Studio (tts-1-hd)
3. Add API version to environment: `AZURE_OPENAI_TTS_API_VERSION=2025-04-01-preview`

### Phase 2: Audio Generation

1. Create `audio_generator.py` module using existing patterns
2. Integrate with existing briefing pipeline (after HTML generation)
3. Save MP3 files to `./audio/` directory (same pattern as HTML storage)

### Phase 3: Serving & Delivery

1. Add FastAPI endpoint for audio streaming (5 lines of code)
2. Modify Jinja2 email template to include `<audio>` element
3. Update email sending to attach MP3 (use `MIMEAudio`)

### Phase 4: Testing & Rollout

1. A/B test: Send audio to subset of users
2. Monitor email delivery rates (attachment size impact)
3. Collect feedback on voice/quality preferences
4. Full rollout

---

## Open Questions (For Implementation Phase)

1. **Voice selection per role:** Should Brokers get "alloy", Leadership get "onyx", etc.? Or unified voice?
2. **Speech speed:** Default 1.0x or faster (1.1-1.2x) to reduce listening time?
3. **Intro/outro audio:** Add standard opening/closing phrases? ("Good morning, here's your daily insurance intelligence brief...")
4. **Error handling:** If TTS fails, send email without audio or retry? (Recommendation: Send without, log error)
5. **File naming:** Use briefing ID, date, role in filename? (Recommendation: `briefing_{role}_{date}.mp3`)

---

## Sources

### Azure OpenAI TTS Documentation
- [Text to speech with Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/text-to-speech-quickstart?view=foundry-classic)
- [Audio speech endpoint](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/openai-speech)
- [Azure OpenAI audio concepts](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/audio?view=foundry-classic)
- [OpenAI Text to Speech API](https://platform.openai.com/docs/guides/text-to-speech)

### Python SDK & Implementation
- [OpenAI Python SDK v2.24.0](https://pypi.org/project/openai/)
- [OpenAI audio.speech.create API reference](https://platform.openai.com/docs/api-reference/audio/createSpeech)
- [GitHub: Azure OpenAI TTS SDK examples](https://github.com/LazaUK/AOAI-TextToSpeech-SDKv1)

### FastAPI Audio Streaming
- [FastAPI Custom Response - FileResponse](https://fastapi.tiangolo.com/advanced/custom-response/)
- [FastAPI audio/video FileResponse discussion](https://github.com/fastapi/fastapi/discussions/6284)
- [Streaming Responses in FastAPI](https://hassaanbinaslam.github.io/posts/2025-01-19-streaming-responses-fastapi.html)

### Python Email & Attachments
- [Python email.mime documentation](https://docs.python.org/3/library/email.mime.html)
- [Python email examples](https://docs.python.org/3/library/email-examples.html)
- [Definitive guide to email attachments in Python 3](https://kitson-consulting.co.uk/blog/definitive-guide-creating-emails-attachments-python-3)

### Audio Format & File Size
- [Audio file size calculations](https://www.audiomountain.com/tech/audio-file-size.html)
- [192kbps vs 128kbps guide](https://www.oreateai.com/blog/192kbps-vs-128kbps-decoding-audio-quality-and-file-size/638ab242881c34cfc72be17714380507)

### OpenAI TTS Models & Voices
- [Introducing next-generation audio models](https://openai.com/index/introducing-our-next-generation-audio-models/)
- [Best TTS APIs for developers 2026](https://www.gladia.io/blog/best-tts-apis-for-developers-in-2026-top-7-text-to-speech-services)

---

*Stack research for: Audio intelligence briefings (TTS + podcast generation)*
*Researched: 2026-02-27*
*Confidence: HIGH*
*Researcher: GSD Project Researcher (Audio Stack Dimension)*
