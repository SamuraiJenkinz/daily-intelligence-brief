# Requirements: MDInsights v2.0

**Defined:** 2026-02-27
**Core Value:** Each audience at Marsh receives only the intelligence relevant to their decisions, priority-ranked and AI-summarised, delivered daily with zero manual effort.

## v2.0 Requirements

Requirements for Audio Intelligence Briefings. Each maps to roadmap phases.

### Script Generation

- [ ] **SCRPT-01**: System generates a podcast-style narration script per role from the day's classified articles using GPT-4o
- [ ] **SCRPT-02**: Each script opens with a branded intro ("Good morning, this is your Marsh [Role] intelligence brief for [date]...") and closes with a sign-off
- [ ] **SCRPT-03**: Script orders content by priority (Critical / High / Medium) mirroring the HTML brief structure
- [ ] **SCRPT-04**: Script preprocesses insurance terminology, abbreviations, tickers, and numbers for natural speech before TTS conversion

### Audio Generation

- [ ] **AUDIO-01**: System converts scripts to MP3 audio using Azure OpenAI TTS (tts-1-hd model) as primary provider
- [ ] **AUDIO-02**: System falls back to ElevenLabs TTS when Azure TTS is unavailable or fails
- [ ] **AUDIO-03**: TTS provider abstraction layer supports both Azure and ElevenLabs with consistent interface
- [ ] **AUDIO-04**: All roles use one consistent professional voice for brand identity
- [ ] **AUDIO-05**: Each role's audio briefing is 2-5 minutes in duration

### Delivery

- [ ] **DLVR-01**: MP3 audio file is attached to the existing role-based daily email
- [ ] **DLVR-02**: Email includes a streaming link to play the audio in-browser from the admin dashboard
- [ ] **DLVR-03**: Admin dashboard includes an audio archive for browsing past audio briefings
- [ ] **DLVR-04**: Admin dashboard includes an HTML5 audio player widget for playback

### Operations

- [ ] **OPS-01**: Audio generation failure never blocks HTML email delivery (graceful degradation)
- [ ] **OPS-02**: Audio generation runs in parallel for all 4 roles within the existing delivery window
- [ ] **OPS-03**: System tracks TTS API character usage per role per day for cost monitoring
- [ ] **OPS-04**: Audio files are automatically cleaned up after a configurable retention period

## Future Requirements

Deferred to v2.1+ based on post-launch feedback and engagement data.

### Voice Personalisation

- **VOICE-01**: Distinct voice persona per audience role (e.g., authoritative for Leadership, calm for Compliance)
- **VOICE-02**: Admin-configurable voice selection per role from available TTS voices
- **VOICE-03**: SSML prosody control for contextual emphasis on critical data points

### Advanced Audio Features

- **ADV-01**: Custom pronunciation lexicon for frequently mentioned entities and companies
- **ADV-02**: Smart content selection via AI-driven audio-suitability scoring
- **ADV-03**: MP3 chapter markers for in-audio navigation
- **ADV-04**: Adaptive script length based on daily news volume

## Out of Scope

| Feature | Reason |
|---------|--------|
| Interactive voice navigation | Too complex for 2-5 min format, listeners are multitasking |
| Personalised/celebrity AI voices | Compliance risk, brand inconsistency |
| Real-time on-demand generation | Pre-generate during overnight pipeline; on-demand adds latency and cost |
| Full article text narration | Defeats curation purpose, causes listener drop-off |
| Background music/jingles | Distracting for information-dense professional content |
| Variable playback speed controls | Already built into every audio player/email client |
| Transcription alongside audio | HTML email already provides text version of the brief |
| Multi-language audio | Single English deployment for Marsh; defer to future if needed |
| Podcast platform distribution | Internal delivery only; no Spotify/Apple Podcasts integration |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCRPT-01 | Phase 17 | Pending |
| SCRPT-02 | Phase 17 | Pending |
| SCRPT-03 | Phase 17 | Pending |
| SCRPT-04 | Phase 17 | Pending |
| AUDIO-01 | Phase 17 | Pending |
| AUDIO-02 | Phase 18 | Pending |
| AUDIO-03 | Phase 18 | Pending |
| AUDIO-04 | Phase 17 | Pending |
| AUDIO-05 | Phase 17 | Pending |
| DLVR-01 | Phase 19 | Pending |
| DLVR-02 | Phase 19 | Pending |
| DLVR-03 | Phase 20 | Pending |
| DLVR-04 | Phase 20 | Pending |
| OPS-01 | Phase 19 | Pending |
| OPS-02 | Phase 19 | Pending |
| OPS-03 | Phase 20 | Pending |
| OPS-04 | Phase 20 | Pending |

**Coverage:**
- v2.0 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0
- Coverage: 100% ✓

---
*Requirements defined: 2026-02-27*
*Last updated: 2026-02-27 after roadmap creation*
