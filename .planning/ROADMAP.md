# Roadmap: MDInsights v2.0

**Milestone:** v2.0 Audio Intelligence Briefings
**Created:** 2026-02-27
**Phases:** 4 (Phase 17-20)
**Requirements:** 16

## Phase Overview

| Phase | Name | Goal | Requirements | Success Criteria |
|-------|------|------|--------------|------------------|
| 17 | Audio Generation Foundation | Per-role podcast scripts converted to MP3 audio files | SCRPT-01, SCRPT-02, SCRPT-03, SCRPT-04, AUDIO-01, AUDIO-04, AUDIO-05 | 7 |
| 18 | TTS Provider Resilience | Multi-provider TTS with fallback and abstraction | AUDIO-02, AUDIO-03 | 3 |
| 19 | Pipeline Integration & Delivery | Audio generation in daily pipeline with email delivery | DLVR-01, DLVR-02, OPS-01, OPS-02 | 5 |
| 20 | Archive & Operations | Audio archive with playback, retention, and cost monitoring | DLVR-03, DLVR-04, OPS-03, OPS-04 | 4 |

## Phase Details

### Phase 17: Audio Generation Foundation ✓

**Goal:** System generates 2-5 minute per-role podcast-style audio briefings from classified articles with natural narration and proper pronunciation.

**Status:** Complete (2026-02-27) — human audio verification deferred pending Azure OpenAI credentials

**Plans:** 3 plans

Plans:
- [x] 17-01-PLAN.md -- Text preprocessor and script generator services
- [x] 17-02-PLAN.md -- Audio generator service with TTS conversion and CLI runner
- [x] 17-03-PLAN.md -- End-to-end verification and human audio quality check (checkpoint deferred)

**Requirements:**
- SCRPT-01: System generates a podcast-style narration script per role from the day's classified articles using GPT-4o
- SCRPT-02: Each script opens with a branded intro ("Good morning, this is your Marsh [Role] intelligence brief for [date]...") and closes with a sign-off
- SCRPT-03: Script orders content by priority (Critical / High / Medium) mirroring the HTML brief structure
- SCRPT-04: Script preprocesses insurance terminology, abbreviations, tickers, and numbers for natural speech before TTS conversion
- AUDIO-01: System converts scripts to MP3 audio using Azure OpenAI TTS (tts-1-hd model) as primary provider
- AUDIO-04: All roles use one consistent professional voice for brand identity
- AUDIO-05: Each role's audio briefing is 2-5 minutes in duration

**Success Criteria:**
1. User can run script generation for Brokers role and receive a 300-540 word podcast-style script with branded intro/outro
2. User can listen to generated MP3 audio and hear financial terms pronounced correctly (e.g., "LLC" as "L L C", "$1.2M" as "one point two million dollars")
3. User can verify all four role audio files are 2-5 minutes duration and under 3 MB file size
4. User can confirm the same professional voice is used consistently across all four role briefings
5. User can observe that script content follows priority ordering matching the HTML brief structure

**Depends on:** None (foundational phase)

---

### Phase 18: TTS Provider Resilience

**Goal:** System maintains audio generation reliability through provider abstraction and automatic failover when primary TTS provider fails.

**Requirements:**
- AUDIO-02: System falls back to ElevenLabs TTS when Azure TTS is unavailable or fails
- AUDIO-03: TTS provider abstraction layer supports both Azure and ElevenLabs with consistent interface

**Success Criteria:**
1. User can simulate Azure TTS failure and observe automatic fallback to ElevenLabs TTS with same audio quality
2. User can review code and confirm TTSClient abstraction supports both providers through unified interface
3. User can observe fallback event logged to api_events table with provider name and reason

**Depends on:** Phase 17 (requires working Azure TTS implementation to build abstraction layer)

---

### Phase 19: Pipeline Integration & Delivery

**Goal:** Audio briefings are generated automatically during daily pipeline execution and delivered via email attachment with streaming link, with email delivery guaranteed even when audio fails.

**Requirements:**
- DLVR-01: MP3 audio file is attached to the existing role-based daily email
- DLVR-02: Email includes a streaming link to play the audio in-browser from the admin dashboard
- OPS-01: Audio generation failure never blocks HTML email delivery (graceful degradation)
- OPS-02: Audio generation runs in parallel for all 4 roles within the existing delivery window

**Success Criteria:**
1. User can receive daily email and find MP3 audio file attached (2-4 MB) with proper MIME type for inline playback
2. User can click streaming link in email and play audio in browser without downloading file
3. User can simulate audio generation failure and confirm email still sends with HTML brief (no audio attachment)
4. User can observe pipeline logs showing all 4 role audio files generated in parallel within 15 seconds total
5. User can verify entire pipeline (including audio) completes within delivery window before 08:00 market open

**Depends on:** Phase 18 (requires resilient TTS with fallback before pipeline integration)

---

### Phase 20: Archive & Operations

**Goal:** Historical audio briefings are browsable and playable via admin dashboard with automated retention policies and cost monitoring for sustainable operations.

**Requirements:**
- DLVR-03: Admin dashboard includes an audio archive for browsing past audio briefings
- DLVR-04: Admin dashboard includes an HTML5 audio player widget for playback
- OPS-03: System tracks TTS API character usage per role per day for cost monitoring
- OPS-04: Audio files are automatically cleaned up after a configurable retention period

**Success Criteria:**
1. User can browse admin dashboard audio archive and see list of past briefings organized by role and date
2. User can click any archived briefing and hear it play using HTML5 audio player with seek/scrubbing controls
3. User can view TTS cost dashboard showing character counts per role per day with monthly budget alerts
4. User can configure 90-day retention policy and verify audio files older than threshold are automatically deleted

**Depends on:** Phase 19 (requires pipeline-generated audio files and streaming endpoint before archive/monitoring)

---

## Requirement Coverage

| Requirement | Phase | Description |
|-------------|-------|-------------|
| SCRPT-01 | 17 | System generates a podcast-style narration script per role from the day's classified articles using GPT-4o |
| SCRPT-02 | 17 | Each script opens with a branded intro and closes with a sign-off |
| SCRPT-03 | 17 | Script orders content by priority (Critical / High / Medium) mirroring the HTML brief structure |
| SCRPT-04 | 17 | Script preprocesses insurance terminology, abbreviations, tickers, and numbers for natural speech before TTS conversion |
| AUDIO-01 | 17 | System converts scripts to MP3 audio using Azure OpenAI TTS (tts-1-hd model) as primary provider |
| AUDIO-02 | 18 | System falls back to ElevenLabs TTS when Azure TTS is unavailable or fails |
| AUDIO-03 | 18 | TTS provider abstraction layer supports both Azure and ElevenLabs with consistent interface |
| AUDIO-04 | 17 | All roles use one consistent professional voice for brand identity |
| AUDIO-05 | 17 | Each role's audio briefing is 2-5 minutes in duration |
| DLVR-01 | 19 | MP3 audio file is attached to the existing role-based daily email |
| DLVR-02 | 19 | Email includes a streaming link to play the audio in-browser from the admin dashboard |
| DLVR-03 | 20 | Admin dashboard includes an audio archive for browsing past audio briefings |
| DLVR-04 | 20 | Admin dashboard includes an HTML5 audio player widget for playback |
| OPS-01 | 19 | Audio generation failure never blocks HTML email delivery (graceful degradation) |
| OPS-02 | 19 | Audio generation runs in parallel for all 4 roles within the existing delivery window |
| OPS-03 | 20 | System tracks TTS API character usage per role per day for cost monitoring |
| OPS-04 | 20 | Audio files are automatically cleaned up after a configurable retention period |

**Coverage:** 16/16 requirements mapped

## Phase Dependencies

```
Phase 17 (Audio Generation Foundation)
   |
Phase 18 (TTS Provider Resilience)
   |
Phase 19 (Pipeline Integration & Delivery)
   |
Phase 20 (Archive & Operations)
```

**Dependency Rationale:**

- **Phase 17 -> 18:** Must have working Azure TTS implementation before building provider abstraction layer and fallback logic
- **Phase 18 -> 19:** Must have resilient TTS with fallback before integrating into production pipeline (prevents cascading failures)
- **Phase 19 -> 20:** Must have pipeline-generated audio files and streaming endpoints working before building archive browser and cost monitoring

---

## Research Integration

This roadmap aligns with research findings from `.planning/research/SUMMARY.md`:

**Critical Pitfalls Addressed:**

| Pitfall | Prevention Strategy | Phase |
|---------|-------------------|-------|
| TTS Pronunciation Catastrophe | SCRPT-04 requirement for terminology preprocessing | Phase 17 |
| Writing for Eye Not Ear | SCRPT-01 GPT-4o audio-specific script generation | Phase 17 |
| Cost Explosion from Unoptimized Scripts | AUDIO-05 duration limits + OPS-03 cost monitoring | Phase 17, 20 |
| Silent Audio Failure | OPS-01 graceful degradation requirement | Phase 19 |
| Pipeline Timing Cascade Failure | OPS-02 parallel processing requirement | Phase 19 |
| Audio Storage Growth Explosion | OPS-04 retention policy requirement | Phase 20 |

**Technology Decisions:**

- Azure OpenAI TTS (tts-1-hd) as primary provider (AUDIO-01)
- ElevenLabs as fallback provider (AUDIO-02)
- Filesystem storage for MP3 files (implied by DLVR-02 streaming endpoint)
- Parallel processing for all 4 roles (OPS-02)
- 2-5 minute duration target (AUDIO-05)

---

*Roadmap created: 2026-02-27*
*Milestone: v2.0 Audio Intelligence Briefings*
*Starting phase: 17 (continues from v1.2)*
