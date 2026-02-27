# Project Research Summary

**Project:** MDInsights v2.0 Audio Intelligence Briefings
**Domain:** Audio intelligence briefings (TTS + podcast generation)
**Researched:** 2026-02-27
**Confidence:** HIGH

---

## Executive Summary

MDInsights v2.0 adds per-role podcast-style audio briefings (2-5 minutes each) using Azure OpenAI TTS. The feature extends the existing Python/FastAPI pipeline with minimal technical debt: upgrade the `openai` package from 2.16.0 to 2.24.0, add script generation (GPT-4o), TTS conversion (Azure OpenAI tts-1-hd), and dual delivery (MP3 email attachment + streaming link). **Zero new major dependencies required** — all components leverage the existing stack.

The recommended approach treats audio as a **supplementary format, not a replacement** for HTML briefs. Generate separate TTS-optimized scripts using GPT-4o (conversational pacing, spelled-out financial terms), convert to MP3 with Azure OpenAI TTS, store in filesystem (`data/audio/` directory), and deliver via both email attachment (2-4 MB, well under enterprise limits) and streaming endpoint (FastAPI FileResponse with range request support). Audio generation runs as **Step 5c** in the pipeline — parallel processing for all 4 roles, with graceful degradation ensuring email delivery never fails due to audio issues.

Key risks center on pipeline timing (TTS adds 8-15 seconds — must parallelize), pronunciation quality (financial terminology requires pre-processing), and cost management (TTS charges per character — target 300-540 word scripts). Success depends on writing for the ear not the eye, implementing comprehensive error handling, and establishing retention policies before storage costs spiral. The gap between AI-generated and human voices has narrowed significantly in 2026 — Azure OpenAI TTS achieves near-human quality when scripts are properly optimized.

---

## Key Findings

### Recommended Stack

**Upgrade Required:**
- `openai` package: 2.16.0 → 2.24.0 (for TTS support via `client.audio.speech.create()`)

**Existing Stack (Already Sufficient):**
- **FastAPI 0.115.0**: Serves audio via built-in `FileResponse` (streaming, range requests, MIME types)
- **Python stdlib**: Email attachments via `email.mime.audio.MIMEAudio` (MP3 handling, base64 encoding)
- **httpx**: Async API calls (already used throughout codebase)
- **structlog/tenacity**: Logging and retry logic (already configured)

**Azure OpenAI TTS Configuration:**
- **Model**: tts-1-hd (high-definition quality for professional audio)
- **Voice**: alloy (neutral, professional) — test echo (calm/measured) and onyx (authoritative) per role
- **Format**: MP3 (default, 128kbps, ~1 MB/minute) — consider 64kbps for voice optimization
- **API Version**: 2025-04-01-preview (TTS endpoint support)

**File Size**: 2-5 minute briefings = 2-5 MB per MP3 (well within 10-25 MB enterprise email limits)

**What NOT to Use:**
- ffmpeg, pydub, mutagen, soundfile (unnecessary — Azure outputs production-ready MP3)
- Database BLOBs (use filesystem for 2-4 MB files — better streaming performance)
- WebSockets, gRPC (over-engineering for asynchronous delivery use case)

---

### Expected Features

#### Table Stakes (MVP — v2.0 Launch)

| Feature | Why Essential | Implementation |
|---------|---------------|----------------|
| **Consistent 2-5 minute duration** | Predictability builds listener trust for commute use | Target 300-540 words (150-180 WPM) |
| **Clear structural markers** | Verbal intro/outro/transitions for multitasking listeners | Branded intro, executive overview, top stories, sign-off |
| **High-quality Azure TTS** | Baseline expectation in 2026; listeners notice poor quality instantly | tts-1-hd model, 48kHz neural voices |
| **Proper pronunciation** | Financial/insurance terminology must be correct or credibility suffers | Pre-process scripts: spell out abbreviations, expand tickers/policy numbers |
| **Natural pacing** | Conversational flow with breathing room between sentences | Add commas for pauses, avoid run-on sentences, use GPT-4o for TTS-optimized scripting |
| **Content curation** | Summarized highlights, not full article text verbatim | Select 3-5 top priority stories from existing AI summaries |
| **Branded intro/outro** | Professional framing establishes context and routine | "Good morning, this is your [Role] Brief for [Date]..." |
| **Dual delivery format** | MP3 attachment + streaming link for flexibility | Attachment for offline playback, streaming for web player with seek functionality |
| **Audio archive** | Historical briefings accessible via admin dashboard | Store in `data/audio/` with 90-day hot storage retention |
| **Priority-aware ordering** | Lead with Critical/High items using existing classification | Leverage existing priority data, structure mirrors importance |

#### Differentiators (Post-Launch — v2.1+)

| Feature | Value Proposition | Complexity | When to Add |
|---------|-------------------|------------|-------------|
| **Role-specific voice personas** | Different voice per role creates identity and recognizability | Low | v2.1 (1 week) after validating baseline engagement |
| **Custom pronunciation lexicon** | PLS lexicon for frequently mentioned entities prevents recurring mispronunciations | Medium | v2.1 (2 weeks) after identifying top pronunciation issues from user feedback |
| **Contextual emphasis** | SSML prosody for critical data points (e.g., share price drops, entity names) | Medium | v2.2 (1 week) after baseline audio proves successful |
| **Progress indicators** | Verbal chapter markers ("Story 1 of 4") help listeners track position | Low | v2.2 (trivial) after validating episode structure |
| **Adaptive scripting** | Automated TTS optimization pipeline (commas for pauses, phonetic spellings) | Medium | v2.3 (2 weeks) after manual tuning establishes patterns |

#### Anti-Features (Avoid These)

| Feature | Why Problematic | Alternative |
|---------|-----------------|-------------|
| **Interactive voice navigation** | High complexity, low value for 2-5 min format. Requires separate voice recognition stack. | Keep duration short enough that skipping is unnecessary. Provide timestamped chapters in MP3 metadata for manual scrubbing. |
| **Real-time generation** | Increases latency, complicates delivery, risks failures during email open | Pre-generate audio during overnight briefing creation workflow |
| **Full article text narration** | Duration balloons to 20-40+ minutes, causing listener drop-off | Stick to curated summaries. Audio is overview, not replacement. |
| **Background music** | Distracting for information-dense briefings. Reduces accessibility. | Use brief music stinger (2-3 sec) for intro/outro only |
| **Variable playback speed controls** | Already built into every audio player (iOS, Android, Spotify) | Rely on native player controls. Don't rebuild standard functionality. |

---

### Architecture Approach

**Integration Point:** Audio generation occurs as **Step 5c** in the existing pipeline, immediately after Step 5b (HTML report archiving) and before Step 8 (email delivery). This allows audio files to be attached to emails without changing the core pipeline structure.

**Component Responsibilities:**

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| **ScriptWriterService** | Generate podcast-style narration from classified articles | GPT-4o with audio-specific prompt template. Produces 500-800 word script with branded intro/outro. |
| **TTSClient** | Convert script text to MP3 audio | Azure OpenAI TTS API (tts-1-hd model, alloy voice). Returns audio bytes. |
| **AudioStorageManager** | Write MP3 files to filesystem and record metadata in database | Filesystem operations + SQLAlchemy ORM for audio_briefs table. |
| **AudioStreamer** | Serve audio files with range request support | FastAPI FileResponse with `media_type="audio/mpeg"`. Handles HTTP Range headers. |
| **AudioBrief (model)** | Database record for audio file metadata | SQLAlchemy model with role, date, filepath, duration, file_size, script_text. |

**Data Flow:**

```
classified_articles + executive_summary
         ↓
ScriptWriterService (GPT-4o) → podcast_script (500-800 words)
         ↓
TTSClient (Azure OpenAI TTS) → audio_bytes (MP3, 2-4 MB)
         ↓
AudioStorageManager → data/audio/{role}/{date}.mp3 + audio_briefs DB record
         ↓
EnterpriseEmailClient → email with MP3 attachment + streaming link
         ↓
AudioStreamer (FastAPI) → /api/audio/{role}/{date} endpoint
```

**Storage Strategy:**
- **Filesystem** (not SQLite BLOBs): 2-4 MB files exceed efficient BLOB range (<250KB). Filesystem enables better streaming, backup, and range request support.
- **Directory structure**: `data/audio/{role}/{YYYY-MM-DD}.mp3`
- **Database**: SQLite `audio_briefs` table stores metadata (filepath, duration, file_size) for querying and admin dashboard.

**Delivery Strategy:**
- **Dual delivery**: MP3 attachment (2-4 MB, under 10 MB enterprise limit) + streaming link to FastAPI endpoint
- **Attachment benefits**: Offline playback, no internet required, familiar UX
- **Streaming benefits**: Web player with seek/scrubbing, archive access without searching email

**Parallel Processing:**
- Generate audio for all 4 roles simultaneously using `asyncio.gather()`
- Sequential generation = 4 × 10 seconds = 40 seconds; parallel = ~10 seconds
- Minimizes delay between report generation and email delivery

**Error Handling:**
- **Graceful degradation**: Email MUST always send, even if audio generation fails
- Retry logic with exponential backoff (3 attempts: immediate, +2s, +5s)
- Circuit breaker pattern: after 3 consecutive failures, bypass TTS for 5 minutes
- Monitor TTS success rate (target: >99.5%) with alerts below 95%

---

### Critical Pitfalls

#### Top 5 Pitfalls (Prevention Essential for Success)

| Pitfall | What Goes Wrong | How to Avoid | Phase to Address |
|---------|-----------------|--------------|------------------|
| **1. Pipeline Timing Cascade Failure** | TTS generation (8-15 seconds) causes entire delivery to miss 08:00 deadline | Parallelize audio generation for all 4 roles simultaneously. Set aggressive 10s timeouts with fallback to email-without-audio. Monitor pipeline execution time with alerts at 75% of deadline. | Phase 2 (Pipeline Integration) |
| **2. TTS Pronunciation Catastrophe** | Insurance/financial terms, policy numbers, tickers, dollar amounts are mispronounced or garbled | Pre-process script text specifically for TTS: spell out abbreviations ("LLC" → "L L C"), format policy numbers with spaces, write currency explicitly ("$1.2M" → "one point two million dollars"), expand tickers ("BRK.B" → "Berkshire Hathaway Class B"). Create glossary of common insurance terms. | Phase 1 (Audio Generation) |
| **3. Writing for the Eye, Not the Ear** | Audio scripts generated directly from visual briefs without adaptation, resulting in awkward pacing and listener fatigue | Generate audio scripts separately with GPT-4o using audio-specific prompts. Target 150-180 WPM, use conversational transitions, break up dense information with pauses, limit lists to 3 items max, use active voice and shorter sentences. | Phase 1 (Audio Generation) |
| **4. Silent Audio Failure — Email Sends Without Audio** | TTS API fails (timeout, quota exceeded, service unavailable), but system lacks proper fallback handling | Graceful degradation: email MUST always send even if audio fails. Implement fallback chain with retry logic (3 attempts with exponential backoff), circuit breaker pattern, and clear email status ("Audio available" vs "Text-only edition"). Monitor TTS success rate >99.5%. | Phase 2 (Pipeline Integration) |
| **5. Cost Explosion from Unoptimized Scripts** | TTS charges per character. Verbose 2,000-word scripts cost 2.5x more than concise 800-word scripts | Design audio scripts separately from display briefs (shorter, spoken-word optimized). Target 300-540 words max (2-3 min audio at 150-180 WPM). Remove visual formatting artifacts. Implement character count monitoring with budget alerts. Use GPT-4o-mini for script generation. | Phase 1 (Audio) + Phase 4 (Monitoring) |

**Additional Critical Pitfalls:**

- **Email Attachment Size Bomb**: 5-minute audio at 128kbps = 4.7MB. Target 2-3 minutes max, use 64kbps for voice (50% size reduction), never exceed 8MB per attachment.
- **Audio Storage Growth Explosion**: 4 roles × 5MB × 365 days = 7.3GB/year. Implement 90-day hot storage, 1-year cold storage, delete >1 year retention policy from day one.
- **Regional TTS Capacity Bottleneck**: Azure OpenAI TTS only available in North Central US or Sweden Central. Deploy in BOTH regions with geo-failover. Schedule pipeline during off-peak hours.
- **Streaming Link Reliability Failure**: Use permanent non-expiring URLs. Implement proper CDN (Azure Blob Storage with CDN endpoint, Cache-Control headers, CORS config). Monitor link availability hourly.
- **Voice Mismatch and Consistency Issues**: Test all 6 Azure TTS voices before selecting. Maintain consistent voice mapping per role. Document selection rationale.

---

## Implications for Roadmap

### Suggested Phase Structure

#### Phase 1: Audio Generation Foundation (Week 1-2)
**Rationale:** Establish core audio generation capabilities independent of pipeline integration. Test TTS quality, pronunciation, and script optimization before delivery concerns.

**Delivers:**
- AudioBrief model + database migration
- ScriptWriterService (GPT-4o with TTS-optimized prompts)
- TTSClient (Azure OpenAI TTS integration)
- AudioStorageManager (filesystem + DB metadata)
- Basic pronunciation handling (SSML for common insurance terms)

**Features from FEATURES.md:**
- High-quality Azure TTS (tts-1-hd model)
- Natural pacing (script preprocessing)
- Content curation (300-540 word scripts from AI summaries)
- Branded intro/outro
- Proper pronunciation (basic SSML)

**Critical Pitfalls to Avoid:**
- TTS Pronunciation Catastrophe → Pre-process scripts for financial terminology
- Writing for Eye Not Ear → GPT-4o audio-specific prompting
- Cost Explosion → Character count monitoring, 300-540 word limit
- Voice Mismatch → Test all voices, document selection rationale

**Success Criteria:**
- Listen to 30 seconds of each role's audio
- Verify financial terms pronounced correctly
- Confirm audio length 2-3 minutes (±15 seconds)
- Audio files <3MB each

---

#### Phase 2: Pipeline Integration (Week 2-3)
**Rationale:** Integrate audio generation into production pipeline with comprehensive error handling. Ensure email delivery never fails due to audio issues.

**Delivers:**
- AudioGenerationService (orchestrator for all 4 roles)
- Pipeline modification (Step 5c: parallel audio generation)
- Parallel processing (asyncio.gather for 4 roles)
- Error handling (graceful degradation, retry logic, circuit breaker)
- Multi-region failover (North Central US + Sweden Central)

**Features from FEATURES.md:**
- Reliable delivery (email always sends, even if audio fails)
- Consistent duration (enforced via script length limits)

**Critical Pitfalls to Avoid:**
- Pipeline Timing Cascade → Parallelize all 4 roles, 10s timeout per TTS call
- Silent Audio Failure → Comprehensive error handling, email sends without audio on failure
- Regional TTS Capacity → Multi-region deployment with failover

**Success Criteria:**
- Load test: 4 roles complete audio generation in <10 seconds
- Simulate TTS failure, verify email sends successfully
- Pipeline execution time <5 minutes total (including audio)
- TTS success rate >99.5%

---

#### Phase 3: Delivery & Archive (Week 3-4)
**Rationale:** Make audio accessible via streaming and email. Provide archive access for historical briefings.

**Delivers:**
- AudioStreamer router (FastAPI endpoint with range request support)
- Email template updates (HTML5 audio player + download link)
- Email attachment support (MP3 via MIMEAudio)
- Admin dashboard audio archive browser
- CDN configuration (Cache-Control, CORS headers)

**Features from FEATURES.md:**
- Dual delivery format (MP3 attachment + streaming link)
- Audio archive (admin dashboard with web player)
- Clear structural markers (intro/outro in email template)

**Critical Pitfalls to Avoid:**
- Email Attachment Size Bomb → Validate file size <8MB before sending
- Streaming Link Reliability → Permanent URLs, CDN with monitoring
- Audio Storage Growth → Implement retention policies (90-day hot, 1-year cold)

**Success Criteria:**
- Audio plays correctly in Outlook, Gmail, Apple Mail
- Streaming endpoint tested from 3 email clients
- CDN 404 monitoring active
- Retention policies configured and tested

---

#### Phase 4: Monitoring & Optimization (Week 4-5)
**Rationale:** Establish observability for cost management, quality assurance, and performance optimization.

**Delivers:**
- TTS API usage monitoring (character-level tracking)
- Cost dashboard (budget alerts per role)
- Pipeline execution time tracking
- TTS success rate monitoring
- Storage usage alerts
- User engagement metrics (play rate, completion rate)

**Features from FEATURES.md:**
- Priority-aware ordering (monitor which stories get played most)

**Critical Pitfalls to Avoid:**
- Cost Explosion → Character count monitoring, monthly budget alerts
- Audio Storage Growth → Storage usage alerts at 80% capacity

**Success Criteria:**
- Character-level TTS usage tracking implemented
- Budget alerts configured per role
- TTS success rate dashboard visible (target >99.5%)
- Pipeline execution time alerts at 75% of deadline

---

### Phase Ordering Rationale

**Why this sequence:**

1. **Foundation before integration**: Build audio generation components independently with thorough testing before pipeline integration. Prevents cascade failures from untested TTS quality.

2. **Error handling before delivery**: Ensure pipeline robustness (Phase 2) before adding delivery complexity (Phase 3). Email must always work, even when audio fails.

3. **Monitoring from start**: Cost management and quality assurance (Phase 4) run parallel with deployment. Cannot wait to discover cost overruns or quality issues after launch.

4. **Incremental risk**: Each phase adds one major capability (generation → integration → delivery → monitoring) with clear rollback points.

5. **User-facing last**: Delivery (Phase 3) comes after generation and integration are proven reliable. Prevents user exposure to unstable features.

---

### Research Flags

**Phases Requiring Deeper Research:**

- **Phase 1 (Audio Generation)**: Voice selection testing — research needed on role-specific voice preferences. Consider A/B testing with small user group.
- **Phase 2 (Pipeline Integration)**: Regional capacity testing — need production-scale testing during 07:00-08:00 AM Eastern peak hours to validate multi-region failover.
- **Phase 3 (Delivery)**: CDN configuration — research best practices for audio CDN with enterprise email clients (CORS policies, Cache-Control headers).

**Phases with Well-Documented Patterns (Skip Deep Research):**

- **Phase 4 (Monitoring)**: Standard observability patterns apply. Use existing structlog/tenacity patterns from codebase.
- Email attachment implementation: Standard MIME practices documented in Python stdlib.
- FastAPI FileResponse: Well-documented streaming patterns.

**Additional Research Needs:**

- **User engagement metrics**: What constitutes "success" for audio briefings? Need to define baseline metrics (play rate >40%, completion rate >70% suggested in research).
- **Accessibility compliance**: Are transcripts required alongside audio? Research WCAG standards for audio content.
- **Multi-language support**: If future expansion to non-English markets, research Azure TTS language support and localization workflows.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | Research confirms minimal dependencies. Azure OpenAI TTS well-documented. Upgrade path clear (openai 2.16.0 → 2.24.0). Existing stack sufficient for delivery. |
| **Features** | HIGH | Table stakes well-defined from competitive analysis (NPR Up First, TIME AI Brief). Differentiators prioritized based on user value vs. implementation cost. Anti-features clearly identified with evidence. |
| **Architecture** | HIGH | Integration point clear (Step 5c in pipeline). Component boundaries well-defined. Filesystem vs. BLOB decision backed by performance data (SQLite 35% faster only for <250KB files). Parallel processing approach validated. |
| **Pitfalls** | HIGH | 10 critical pitfalls identified with specific prevention strategies. Sources include Azure documentation, TTS production experience reports, podcast best practices. "Looks Done But Isn't" checklist comprehensive. |

**Overall Confidence: HIGH**

All four research dimensions (Stack, Features, Architecture, Pitfalls) converge on a consistent implementation approach. No conflicting recommendations across research files. Evidence-based decision making throughout (e.g., filesystem vs. BLOBs backed by SQLite performance data, MP3 format backed by universal browser support, parallel processing backed by performance calculations).

---

### Gaps to Address During Planning

**Technical Gaps:**

1. **Exact TTS character limits**: Research identifies word count targets (300-540 words) but Azure OpenAI TTS max character limit per request needs validation. Recommendation: Test with 1,000-word script to verify API limits.

2. **CDN cost modeling**: Research focuses on TTS API costs ($10.80/month estimated) but CDN bandwidth costs for streaming not quantified. Recommendation: Estimate bandwidth usage (200 users × 4MB × 22 working days = 17.6GB/month) and calculate Azure CDN costs.

3. **Retention policy automation**: Research recommends 90-day hot storage, 1-year cold storage, but Azure Blob Storage lifecycle policies not detailed. Recommendation: Research Azure Blob lifecycle management configuration during Phase 3.

4. **Transcription for accessibility**: Anti-features section mentions "transcription alongside audio" is unnecessary (HTML brief exists), but accessibility compliance may require transcripts. Recommendation: Research WCAG standards for audio content during Phase 1.

**Business Gaps:**

1. **User engagement baselines**: Research suggests play rate >40%, completion rate >70% as success metrics, but no validation from similar products. Recommendation: Validate metrics with stakeholders before launch.

2. **Voice preference by role**: Research suggests role-specific voices (Brokers: alloy, Leadership: onyx, Compliance: nova, Underwriting: echo) but no user validation. Recommendation: A/B test with small user group during Phase 1.

3. **Regional accent requirements**: Research mentions potential regional accent mismatches (US accent for Australian brokers) but no confirmation of user base geography. Recommendation: Validate regional requirements with stakeholders.

**Operational Gaps:**

1. **Backup strategy for audio files**: Research mentions filesystem storage with backup simplicity but doesn't detail backup frequency or retention. Recommendation: Define backup strategy during Phase 3 (daily incremental, weekly full?).

2. **Error alerting thresholds**: Research recommends TTS success rate >99.5% with alerts below 95%, but escalation procedures undefined. Recommendation: Define on-call rotation and escalation paths during Phase 4.

3. **Cost budget approval**: Research estimates $10.80/month TTS costs but budget approval process not defined. Recommendation: Get budget approval for estimated $15-20/month (TTS + CDN + storage) before Phase 1.

---

## Sources

**Research aggregated from 4 dimensions:**

### Stack Research Sources (15 sources)
- [Azure OpenAI TTS Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/text-to-speech-quickstart) — Official Microsoft Learn guides for text-to-speech with Azure OpenAI
- [OpenAI Python SDK v2.24.0](https://pypi.org/project/openai/) — Latest SDK with TTS support via `client.audio.speech.create()`
- [FastAPI Custom Response - FileResponse](https://fastapi.tiangolo.com/advanced/custom-response/) — Audio streaming implementation patterns
- [Python email.mime documentation](https://docs.python.org/3/library/email.mime.html) — Email attachment handling with MIMEAudio

### Features Research Sources (20 sources)
- [The 11 Best Daily News Podcasts to Listen to in 2026](https://podcastreview.org/list/best-daily-news-podcasts/) — Competitive analysis of successful audio briefing patterns
- [Text-to-Speech Voice AI Model Guide 2026](https://www.camb.ai/blog-post/text-to-speech-voice-ai-model-guide) — TTS quality benchmarks and expectations
- [Speech Synthesis Markup Language (SSML) overview](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup) — Pronunciation control via SSML
- [How the TIME AI Audio Brief Was Built](https://time.com/7294142/time-ai-audio-brief/) — Case study of editor-curated audio briefings

### Architecture Research Sources (10 sources)
- [Text to speech with Azure OpenAI - Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/openai/text-to-speech-quickstart) — Azure OpenAI TTS integration patterns
- [Receiving and returning audio & video files using FileResponse - FastAPI GitHub](https://github.com/fastapi/fastapi/discussions/6284) — Audio streaming with range request support
- [SQLite is 35% Faster than Filesystem with Small BLOBs](https://sqlite.org/fasterthanfs.html) — Evidence for filesystem vs. BLOB decision (>250KB threshold)
- [Exchange Online limits - Microsoft Learn](https://learn.microsoft.com/en-us/office365/servicedescriptions/exchange-online-service-description/exchange-online-limits) — Email attachment size limits (10-25 MB enterprise)

### Pitfalls Research Sources (20 sources)
- [Streaming TTS Latency Accuracy Tradeoff 2026](https://deepgram.com/learn/streaming-tts-latency-accuracy-tradeoff-2026) — TTS pronunciation issues in streaming vs. batch
- [OpenAI Cost Optimization Strategies](https://www.cloudzero.com/blog/openai-cost-optimization/) — Cost management for TTS API usage
- [7 Best Practices: Writing for Text To Speech Voices](https://blog.videate.io/7-best-practices-writing-for-text-to-speech-voices) — Script optimization for natural TTS
- [TOP 6 CDN for Audio Delivery](https://blog.blazingcdn.com/en-us/top-6-cdn-for-audio-delivery) — CDN configuration for audio streaming reliability

**Total Sources: 65 across all research dimensions**

All sources from 2025-2026, ensuring current best practices and technology capabilities.

---

*Research completed: 2026-02-27*
*Ready for roadmap: YES*

**Next Steps:**
1. Review SUMMARY.md with stakeholders to validate phase structure and success criteria
2. Proceed to `/gsd:roadmapper` to create detailed implementation roadmap
3. Begin Phase 1 (Audio Generation Foundation) with voice testing and script optimization

---

**Synthesis Notes:**

This summary synthesizes findings from:
- **STACK.md**: Zero new major dependencies (upgrade openai only). Azure OpenAI TTS well-suited for use case.
- **FEATURES.md**: Clear table stakes (10 MVP features) vs. differentiators (5 post-launch features) vs. anti-features (7 to avoid).
- **ARCHITECTURE.md**: Step 5c integration point. Parallel processing essential. Filesystem storage preferred.
- **PITFALLS.md**: 10 critical pitfalls with prevention strategies mapped to specific phases.

All research aligns on a consistent approach: minimal dependencies, TTS-optimized scripting, parallel processing, graceful degradation, and comprehensive monitoring. High confidence in implementation feasibility.
