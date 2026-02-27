# Pitfalls Research

**Domain:** Audio intelligence briefings (TTS integration)
**Researched:** 2026-02-27
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Pipeline Timing Cascade Failure

**What goes wrong:** Adding TTS generation (typically 1-2 seconds per operation) to an existing tight pipeline causes the entire delivery to miss the 08:00 deadline. The system appears to work in testing but fails under production load.

**Why it happens:** Azure OpenAI TTS introduces latency that wasn't accounted for in the original pipeline design. Chaining Azure STT → Azure OpenAI (GPT-4o) → Azure TTS introduces cumulative 1-2 second lag per operation. With 4 roles × script generation + audio generation, this adds 8+ seconds minimum, potentially 15-30 seconds under load.

**How to avoid:**
- Measure current pipeline execution time end-to-end before adding audio
- Add TTS generation as parallel operations, not sequential
- Implement async/concurrent audio generation for all 4 roles simultaneously
- Set aggressive timeouts (e.g., 10s per TTS call) with fallback to email-without-audio
- Add monitoring for pipeline execution time with alerts at 75% of deadline

**Warning signs:**
- Pipeline occasionally misses 08:00 deadline after audio feature deployed
- Audio generation time varies significantly between runs
- System works fine in testing but struggles in production
- Increased Azure API latency during peak hours

**Phase to address:** Phase 2 (Pipeline Integration) — Must be architected from the start with parallel processing and timeouts.

---

### Pitfall 2: Email Attachment Size Bomb

**What goes wrong:** MP3 attachments exceed the 20-25MB email limit, causing delivery failures or auto-conversion to cloud links that expire, breaking the user experience.

**Why it happens:** A 5-minute audio brief at standard quality (128kbps) produces ~4.7MB MP3. Enterprise emails typically cap at 20-25MB total. When emails are encoded for sending, attachments grow ~30% larger. 4 emails × 5MB = 20MB, dangerously close to limits before encoding overhead.

**How to avoid:**
- Target 2-3 minute audio length maximum (2-3MB per file)
- Use 64kbps bitrate for spoken-word audio (indistinguishable quality, 50% size reduction)
- Never attach audio directly — use streaming links with archived MP3 as backup
- Implement MP3 compression optimization (VBR, mono channel for voice)
- Add file size validation before email sending (block if >8MB per attachment)

**Warning signs:**
- Email delivery failures with "attachment too large" errors
- Gmail auto-uploads files to Drive instead of attaching
- Users complain about expired cloud links
- Bounce rates increase after audio feature launch

**Phase to address:** Phase 1 (Audio Generation) — Audio encoding settings must be correct from day one.

---

### Pitfall 3: TTS Pronunciation Catastrophe (Financial Terms)

**What goes wrong:** Insurance and financial terminology, policy numbers, equity tickers, and dollar amounts are mispronounced or garbled, making audio briefings sound unprofessional and confusing.

**Why it happens:** Streaming TTS loses 5-20x context versus batch processing, causing pronunciation failures on alphanumeric IDs. Abbreviations like "LLC", "CEO", policy numbers like "POL-2024-12345", and tickers like "BRK.B" are misinterpreted. Numbers in different contexts (dates vs. amounts) require different pronunciation that TTS models miss.

**How to avoid:**
- Pre-process script text specifically for TTS:
  - Spell out all abbreviations: "LLC" → "L L C" or "Limited Liability Company"
  - Format policy numbers with spaces: "POL-2024-12345" → "Policy number P O L 2 0 2 4 1 2 3 4 5"
  - Write currency explicitly: "$1.2M" → "one point two million dollars"
  - Expand tickers: "BRK.B" → "Berkshire Hathaway Class B"
  - Spell out ranges: "20-30%" → "twenty to thirty percent"
- Create glossary of common insurance terms with phonetic replacements
- Use Azure OpenAI GPT-4o to generate TTS-optimized scripts (separate prompt from display script)
- Implement quality check: listen to first 30 seconds of each audio before sending

**Warning signs:**
- Users report audio is "hard to follow" or "confusing"
- Complaints about specific terms being garbled
- Audio sounds robotic despite using HD voices
- Policy numbers sound like random letters

**Phase to address:** Phase 1 (Audio Generation) — Script preprocessing must be built into the generation pipeline.

---

### Pitfall 4: Cost Explosion from Unoptimized Scripts

**What goes wrong:** TTS API costs spiral out of control because scripts contain unnecessary verbosity, repeated content, or haven't been optimized for per-character billing.

**Why it happens:** Azure OpenAI TTS charges per character. A verbose 2,000-word script (~12,000 characters) costs significantly more than a concise 800-word script (~4,800 characters) — 2.5x cost difference. Without monitoring and optimization, costs can reach $50-200/month per user or $2,400-9,600/year for 200 users.

**How to avoid:**
- Design audio scripts separately from display briefs (shorter, spoken-word optimized)
- Target 150-180 words per minute (2-3 min audio = 300-540 words max)
- Remove visual formatting artifacts (bullets, headers, tables) from audio scripts
- Implement character count monitoring with alerts at budget thresholds
- Use GPT-4o-mini for script generation (cheaper) + TTS standard (not HD) for most roles
- Cache frequently used audio segments (intro/outro) to reduce API calls
- Set monthly TTS budget limits per role with automatic throttling

**Warning signs:**
- TTS API bills increasing month-over-month without user growth
- Audio briefings consistently exceeding 5 minutes
- Scripts contain repeated boilerplate text
- No visibility into per-role TTS costs

**Phase to address:** Phase 1 (Audio Generation) AND Phase 4 (Monitoring) — Cost controls must be implemented from start with ongoing monitoring.

---

### Pitfall 5: Silent Audio Failure — Email Sends Without Audio

**What goes wrong:** TTS API fails (timeout, quota exceeded, service unavailable), but the system doesn't have proper fallback handling. Either the email doesn't send at all (breaking the existing reliable delivery), or it sends with broken audio links, frustrating users.

**Why it happens:** External API integrations are inherently unreliable. Azure OpenAI TTS can fail due to insufficient backend capacity (HTTP 429 errors), regional service limits, network timeouts, or quota exhaustion. Without proper error handling, these failures cascade into user-facing problems.

**How to avoid:**
- **Graceful degradation**: Email MUST always send, even if audio generation fails
- Implement fallback chain:
  1. Try TTS generation (10s timeout)
  2. On failure, send email without audio attachment/link
  3. Log failure for retry attempt
  4. Send follow-up email with audio if retry succeeds within 30 minutes
- Add retry logic with exponential backoff (3 attempts: immediate, +2s, +5s)
- Implement circuit breaker pattern: after 3 consecutive failures, bypass TTS for 5 minutes
- Monitor TTS success rate (target: >99.5%) with alerts below 95%
- Display clear status in email: "Audio available" vs "Audio processing" vs "Text-only edition"

**Warning signs:**
- Users report missing audio attachments
- Increased email delivery failures after audio feature launch
- TTS API timeout errors in logs
- No monitoring dashboard for TTS success rate

**Phase to address:** Phase 2 (Pipeline Integration) — Error handling must be comprehensive from launch.

---

### Pitfall 6: Audio Storage Growth Explosion

**What goes wrong:** Audio files accumulate indefinitely without retention policies, causing storage costs to grow exponentially and admin dashboard to slow down as it tries to load hundreds of archived files.

**Why it happens:** 4 roles × 5MB audio × 365 days = 7.3GB/year. Over 3 years: 22GB. Without compression or cleanup, storage costs and retrieval performance degrade. Most email providers store backups of sent emails indefinitely, doubling effective storage needs.

**How to avoid:**
- Implement retention policy from day one:
  - Keep last 90 days in hot storage (admin dashboard)
  - Move 90+ days to cold storage (archive)
  - Delete audio files >1 year old (retain metadata/transcripts only)
- Use cloud storage with lifecycle policies (Azure Blob Storage cold tier)
- Compress audio files: 64kbps VBR instead of 128kbps = 50% reduction
- Store audio files separately from database (blob storage, not SQL)
- Implement pagination in admin dashboard (load 30 files at a time)
- Add storage usage monitoring with alerts at 80% capacity

**Warning signs:**
- Admin dashboard loads slowly or times out
- Storage costs increasing faster than user growth
- Backup times increasing significantly
- Database performance degrading over time

**Phase to address:** Phase 3 (Admin Dashboard) AND Phase 4 (Monitoring) — Retention policies must be implemented before accumulation becomes a problem.

---

### Pitfall 7: Writing for the Eye, Not the Ear

**What goes wrong:** Audio scripts are generated directly from visual briefs without adaptation for spoken delivery, resulting in awkward pacing, unnatural phrasing, and listener fatigue.

**Why it happens:** Written content optimized for scanning (bullets, headers, dense paragraphs) translates poorly to audio. Visual formatting like tables, charts, and bullet points sound repetitive when read aloud. Dense financial prose requires re-reading when visual, but can't be "re-heard" in audio format.

**How to avoid:**
- Generate audio scripts separately with GPT-4o using audio-specific prompts:
  - "Write a conversational 2-minute audio briefing for [role]..."
  - "Use natural spoken transitions and pacing..."
  - "Avoid lists of more than 3 items..."
- Audio script optimization rules:
  - Target 150-180 words per minute (natural speaking pace)
  - Use conversational transitions: "Moving on to..." "Now, regarding..." "Finally..."
  - Break up dense information with pauses (use punctuation: periods, commas, em-dashes)
  - Replace visual references: "as shown below" → "for example"
  - Limit lists to 3 items maximum (more becomes incomprehensible)
  - Use active voice and shorter sentences
- Add explicit pacing markers: "— pause — " between sections

**Warning signs:**
- User feedback that audio is "hard to follow"
- Audio sounds like someone reading a document
- Scripts contain phrases like "see below" or "as shown"
- Listeners report needing to replay sections frequently

**Phase to address:** Phase 1 (Audio Generation) — Script generation prompts must be designed for audio from the start.

---

### Pitfall 8: Regional TTS Capacity Bottleneck

**What goes wrong:** Azure OpenAI TTS resources are only available in North Central US or Sweden Central regions. HTTP 429 errors occur due to insufficient backend capacity during peak usage times, causing inconsistent delivery.

**Why it happens:** Azure OpenAI TTS has strict regional limitations and capacity constraints. If the pipeline runs at 07:45 AM Eastern (peak usage time in North Central US region), TTS API calls may be throttled or fail entirely due to regional capacity limits.

**How to avoid:**
- Deploy TTS resources in BOTH North Central US AND Sweden Central regions
- Implement geo-failover: primary region fails → automatically retry in secondary region
- Schedule pipeline execution during off-peak hours for target region (e.g., 06:30 AM Eastern vs 07:45 AM)
- Monitor regional capacity: track 429 errors by region and time of day
- Implement request queuing with jitter to spread load over 5-10 minutes
- Use batch processing where possible to reduce concurrent API calls
- Pre-generate audio night before for non-time-sensitive content

**Warning signs:**
- HTTP 429 "Insufficient backend capacity" errors in logs
- TTS failures clustered around same time each day
- Success rate varies significantly by day of week
- Pipeline execution time highly variable

**Phase to address:** Phase 2 (Pipeline Integration) — Regional architecture must be designed for reliability from start.

---

### Pitfall 9: Streaming Link Reliability Failure

**What goes wrong:** Audio streaming links break due to CDN failures, authentication issues, or file path changes, leaving users with non-functional audio links in their emails.

**Why it happens:** Streaming audio via CDN requires additional infrastructure (CDN configuration, authentication, CORS headers, proper caching). Cloud storage links often expire after 24-48 hours if not properly configured. Email is permanent, but cloud links are temporary by default.

**How to avoid:**
- Use permanent, non-expiring URLs for audio files (not pre-signed URLs)
- Implement proper CDN for audio delivery:
  - Azure Blob Storage with CDN endpoint
  - Cache-Control headers: `public, max-age=86400` (24 hours)
  - CORS headers configured for email client playback
- Provide both streaming link AND direct download fallback in email
- Test audio links from multiple email clients (Outlook, Gmail, Apple Mail)
- Monitor link availability: automated hourly checks that streaming URLs resolve
- Use consistent URL structure: `https://cdn.mdinsights.com/audio/YYYY-MM-DD/role-name.mp3`
- Implement 301 redirects if URL structure changes

**Warning signs:**
- Users report "audio not playing" in emails
- High rate of direct MP3 downloads vs streaming
- CDN error logs show 404s or 403s on audio files
- Audio works when sent but breaks after 24-48 hours

**Phase to address:** Phase 3 (Email Delivery) — Streaming infrastructure must be production-ready from launch.

---

### Pitfall 10: Voice Mismatch and Consistency Issues

**What goes wrong:** Different Azure TTS voices are used for different roles without testing, resulting in inconsistent brand experience. Or voice doesn't match target audience (e.g., US accent for Australian brokers).

**Why it happens:** Azure OpenAI TTS offers multiple voices (alloy, echo, fable, onyx, nova, shimmer) but not all are suitable for professional business content. Voice selection is often arbitrary without user testing. Regional accent mismatches go unnoticed until deployment.

**How to avoid:**
- Test all 6 Azure TTS voices with representative content before selecting
- Maintain consistent voice mapping:
  - Brokers: Professional, energetic voice (e.g., "alloy")
  - Leadership: Authoritative voice (e.g., "onyx")
  - Compliance: Clear, neutral voice (e.g., "nova")
  - Underwriting: Analytical voice (e.g., "echo")
- Document voice selection rationale in config
- Use same voice consistently per role (no variation day-to-day)
- Consider regional requirements: check if audience expects specific accent
- Implement voice preview in admin dashboard before production use
- A/B test voices with small user group before full rollout

**Warning signs:**
- User feedback about voice being "off-brand" or "unprofessional"
- Inconsistent voice experience between roles
- Regional users complaining about accent mismatch
- Frequent requests to change voice

**Phase to address:** Phase 1 (Audio Generation) — Voice selection must be tested and configured before launch.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip TTS error handling | Faster implementation | Email delivery failures, user complaints, lost reliability reputation | Never — this is core functionality |
| Attach MP3 instead of streaming | Simpler architecture | Email size limits, storage costs, poor mobile experience | Testing only, never production |
| Use same script for visual + audio | No script adaptation work | Poor audio experience, listener fatigue, low adoption | Never — defeats purpose of audio feature |
| No audio retention policy | Defer storage planning | Exponential storage costs, performance degradation, expensive migration | Never — implement from day one |
| Single-region TTS deployment | Simpler setup | Regional capacity failures, unpredictable delivery, 429 errors | POC only, never production |
| No cost monitoring | Faster development | Surprise bills, no cost control, budget overruns | Never — costs can spiral quickly |
| Skip pronunciation optimization | Faster script generation | Unprofessional audio, user confusion, low adoption | MVP only, must fix before scaling |
| No A/B testing of voices | Faster launch | Wrong voice choice, inconsistent brand, costly rework | Small user base (<10), must test before scaling |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **Pipeline timing** | Adding TTS sequentially after existing steps | Parallelize audio generation for all 4 roles simultaneously |
| **Email attachment** | Attaching MP3 directly to email | Stream audio via CDN, include download link as fallback |
| **TTS failure** | Pipeline fails entirely if TTS fails | Graceful degradation: email sends without audio, log for retry |
| **Script generation** | Reusing display brief text for audio | Generate separate TTS-optimized script with GPT-4o |
| **Cost tracking** | No monitoring of TTS API usage | Character-level monitoring with budget alerts per role |
| **Storage** | Storing audio in database | Use blob storage with lifecycle policies and CDN |
| **Voice selection** | Choosing voice arbitrarily | Test all voices with sample content, maintain consistent mapping |
| **Regional capacity** | Single-region deployment | Multi-region failover (North Central US + Sweden Central) |
| **File size** | Default TTS quality settings | Optimize for voice: 64kbps VBR, mono channel, 2-3 min max |
| **Pronunciation** | Raw text sent directly to TTS | Pre-process: spell out abbreviations, expand financial terms |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **Sequential TTS calls** | Pipeline takes 20-30+ seconds | Parallelize all 4 audio generations with asyncio/concurrent.futures | Under production load with tight deadline |
| **Synchronous email sending** | Email sending blocks pipeline | Async email delivery or queue-based sending | High user count (>100) |
| **No TTS timeout** | Pipeline hangs indefinitely on TTS failure | Set aggressive 10-second timeout per TTS call | Any TTS API slowdown or failure |
| **Loading all audio in dashboard** | Admin dashboard times out or crashes | Implement pagination, lazy loading, and date filters | >90 days of audio files |
| **Uncompressed audio** | 10MB+ files, slow downloads | 64kbps VBR, mono channel, 2-3 min max length | Mobile users, poor connections |
| **No CDN caching** | Slow audio streaming, high bandwidth costs | Proper Cache-Control headers, CDN endpoint | Multiple users accessing same audio |
| **No retry logic** | Single TTS failure = permanent failure | Exponential backoff retry (3 attempts) | Network blips, transient API issues |
| **No circuit breaker** | TTS failures cascade, slow recovery | Circuit breaker: bypass TTS after 3 failures for 5 min | Prolonged TTS API outages |

---

## "Looks Done But Isn't" Checklist

### Audio Generation
- [ ] TTS script is optimized for spoken delivery (not copied from display brief)
- [ ] Financial terms, policy numbers, and tickers are spelled out for pronunciation
- [ ] Currency amounts are written in words ("one point two million dollars")
- [ ] Abbreviations are expanded or spelled with spaces ("L L C")
- [ ] Audio length is 2-3 minutes maximum (300-540 words)
- [ ] Bitrate is optimized for voice (64kbps VBR, mono channel)
- [ ] Voice selection has been tested and documented per role
- [ ] Intro/outro branding segments are cached (not re-generated daily)

### Pipeline Integration
- [ ] Audio generation runs in parallel for all 4 roles (not sequential)
- [ ] TTS API calls have 10-second timeout limits
- [ ] Exponential backoff retry logic implemented (3 attempts)
- [ ] Circuit breaker pattern prevents cascade failures
- [ ] Email sends successfully even if TTS fails (graceful degradation)
- [ ] Pipeline execution time monitored with alerts at 75% of deadline
- [ ] Multi-region failover configured (North Central US + Sweden Central)
- [ ] Peak-time capacity tested (07:00-08:00 AM Eastern)

### Email Delivery
- [ ] Audio files never attached directly (streaming links only)
- [ ] Streaming URLs are permanent and non-expiring
- [ ] CDN configured with proper Cache-Control and CORS headers
- [ ] Download fallback link provided in email
- [ ] Email tested in Outlook, Gmail, and Apple Mail
- [ ] File size validated before sending (<8MB per attachment if used)
- [ ] Email status clearly indicates audio availability
- [ ] Failed TTS attempts trigger follow-up email with audio when successful

### Cost Management
- [ ] Character-level TTS usage monitoring implemented
- [ ] Budget alerts configured per role
- [ ] Monthly TTS spending dashboard visible to admins
- [ ] Cost per user tracked and compared to budget
- [ ] GPT-4o-mini used for script generation (not GPT-4o)
- [ ] TTS-standard used for most roles (TTS-HD only if required)
- [ ] Intro/outro segments cached to reduce API calls

### Storage & Archival
- [ ] Audio files stored in blob storage (not database)
- [ ] 90-day hot storage, 1-year cold storage retention policy configured
- [ ] Lifecycle policies automatically move/delete old files
- [ ] Storage usage monitoring with 80% capacity alerts
- [ ] Admin dashboard pagination implemented (30 files per page)
- [ ] Audio archive date filters functional
- [ ] Backup strategy accounts for blob storage (not just database)

### Quality Assurance
- [ ] First 30 seconds of each audio manually reviewed before launch
- [ ] Pronunciation tested for common financial terms
- [ ] Policy numbers and tickers sound correct when spoken
- [ ] Audio pacing sounds natural (not rushed or robotic)
- [ ] Voice matches target role audience
- [ ] Audio transcription available for accessibility
- [ ] Silence/pauses between sections implemented
- [ ] User feedback mechanism for audio quality issues

### Monitoring & Alerting
- [ ] TTS API success rate monitored (target >99.5%)
- [ ] Pipeline execution time tracked per run
- [ ] Regional 429 errors logged and alerted
- [ ] Audio file size distribution tracked
- [ ] Streaming link availability checked hourly
- [ ] Cost per audio generation tracked daily
- [ ] User engagement metrics tracked (play rate, completion rate)
- [ ] Error logs reviewed daily for TTS issues

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| **Pipeline timing cascade** | Phase 2 (Pipeline Integration) | Load test: 4 roles complete in <5 minutes under production load |
| **Email size bomb** | Phase 1 (Audio Generation) | All audio files <3MB, encoding settings verified |
| **TTS pronunciation** | Phase 1 (Audio Generation) | Listen to 30 seconds of each role, test financial terms |
| **Cost explosion** | Phase 1 (Audio) + Phase 4 (Monitoring) | Character count tracking, budget alerts configured |
| **Silent failure** | Phase 2 (Pipeline Integration) | Simulate TTS failure, verify email sends successfully |
| **Storage growth** | Phase 3 (Admin) + Phase 4 (Monitoring) | Retention policies configured, lifecycle tested |
| **Writing for eye not ear** | Phase 1 (Audio Generation) | Side-by-side comparison of display vs audio scripts |
| **Regional capacity** | Phase 2 (Pipeline Integration) | Multi-region failover tested, 429 errors monitored |
| **Streaming reliability** | Phase 3 (Email Delivery) | CDN tested from 3 email clients, 404 monitoring active |
| **Voice mismatch** | Phase 1 (Audio Generation) | All 6 voices tested, selection documented and approved |

---

## Sources

**Azure OpenAI TTS Issues:**
- [Azure Cognitive Speech Alternatives in 2026](https://dasha.ai/tips/azure-cognitive-speech-alternatives)
- [Azure OpenAI Text to Speech Quickstart](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/text-to-speech-quickstart?view=foundry-classic)
- [Text to Speech FAQ - Azure AI Services](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/faq-tts)

**Podcast Pipeline Best Practices:**
- [Podcast Pipeline Automation - ThePod.fm](https://thepod.fm/resources/blog/podcast-pipeline-automation)
- [How to Trace Audio Processing Pipelines with OpenTelemetry](https://oneuptime.com/blog/post/2026-02-06-trace-audio-podcast-processing-pipelines-opentelemetry/view)

**TTS Script Writing:**
- [How to Write Effective Voice Over Scripts - Resemble AI](https://www.resemble.ai/effective-voice-over-script-writing/)
- [7 Best Practices: Writing for Text To Speech Voices](https://blog.videate.io/7-best-practices-writing-for-text-to-speech-voices)

**Email Attachment Limits:**
- [Google Workspace: 50MB Limits for Enterprise Plus](https://workspaceupdates.googleblog.com/2026/02/ending-larger-attachments-in-gmail-new-50MB-limit-for-Enterprise-Plus.html)
- [How Big of a File Can You Email in 2026](https://www.emailsettingspot.com/how-big-of-a-file-can-you-email/)

**TTS Cost Management:**
- [OpenAI TTS API Pricing Calculator (Feb 2026)](https://costgoat.com/pricing/openai-tts)
- [Cheapest Real-Time TTS APIs in 2026](https://www.camb.ai/blog-post/cheapest-real-time-tts-apis)
- [OpenAI Cost Optimization Strategies](https://www.cloudzero.com/blog/openai-cost-optimization/)

**TTS Pronunciation Issues:**
- [Streaming TTS Latency Accuracy Tradeoff 2026](https://deepgram.com/learn/streaming-tts-latency-accuracy-tradeoff-2026)
- [Why Numbers, Dates, Symbols and Acronyms Not Properly Pronounced - Hypernatural](https://intercom.help/hypernatural/en/articles/12430528-why-are-numbers-dates-symbols-and-acronyms-not-properly-pronounced)

**Audio Storage Management:**
- [How Podcasters Backup Their Audio Files](https://www.crashplan.com/blog/how-podcasters-backup-their-audio-files/)
- [Monthly Podcast Storage Options Explained - Libsyn](https://libsyn.com/monthly-storage/)

**TTS Error Handling:**
- [Error Handling Best Practices for Production LLM Applications](https://markaicode.com/llm-error-handling-production-guide/)
- [Fix TTS Error Handling and Add Fallback System](https://huggingface.co/spaces/bravedims/AI_Avatar_Chat/commit/be8c03f024364f7c309ec2a85b970c0a7bde72b0)

**Audio Streaming & CDN:**
- [TOP 6 CDN for Audio Delivery](https://blog.blazingcdn.com/en-us/top-6-cdn-for-audio-delivery)
- [CDN Optimization for Audio Streaming Services](https://blog.blazingcdn.com/en-us/cdn-optimization-for-audio-streaming-services-a-comprehensive-guide)

---

*Pitfalls research for: Audio intelligence briefings (TTS integration to existing automated content pipeline)*
*Researched: 2026-02-27*
*Confidence: HIGH*
*Sources: Azure documentation, TTS production experience reports, podcast pipeline best practices, enterprise email standards*
