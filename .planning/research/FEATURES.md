# Feature Research

**Domain:** Audio intelligence briefings (podcast-style TTS)
**Researched:** 2026-02-27
**Confidence:** HIGH

## Executive Summary

Successful audio briefings in 2026 are characterized by concise duration (2-5 minutes for bulletins, 10-15 minutes for comprehensive briefings), careful content curation rather than full-text reading, natural-sounding TTS voices, and clear structural signposting. The gap between AI-generated and human voices has narrowed significantly, with modern TTS achieving near-human quality when properly implemented. Key differentiators include proper pronunciation of domain-specific terminology, strategic pacing with "breathing room," and predictable episode structure that builds listener trust.

## Feature Landscape

### Table Stakes (Listeners Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Consistent duration** | Predictability builds trust; listeners plan around known length | Low | Research shows news listeners drop off rapidly after 45 min; bulletins typically 2-5 min. Variability reduces listener confidence in planning their time. |
| **Clear structural markers** | Verbal signposting (intro/outro/transitions) guides attention during multitasking | Low | Essential for commute/multitasking scenarios. Include: "Here are today's top stories," "Moving to compliance updates," "That's your brief for today." |
| **High-quality audio** | Baseline expectation in 2026; listeners notice poor quality immediately | Medium | Modern TTS is near-indistinguishable from human. Azure OpenAI TTS supports 48kHz high-fidelity. Must avoid robotic pacing and pronunciation errors. |
| **Proper pronunciation** | Industry terminology must be correct or credibility suffers | Medium | Insurance/reinsurance jargon (e.g., "facultative," "Lloyd's," company names, "Ins. No." → "Insurance number") requires SSML pronunciation control. |
| **Natural pacing** | Generous use of commas/periods for "breathing room"; mimics conversational speech | Low | TTS writing differs from print writing. Insert commas where a human would pause. Avoid run-on sentences that sound rushed. |
| **Content curation** | Summarized highlights, not full article text read verbatim | Medium | Research shows curation saves time and increases comprehension. Select key points rather than reading complete stories. Depends on existing AI-generated summaries. |
| **Branded intro/outro** | Professional framing establishes context and routine | Low | Example: "Good morning, this is your MDInsights briefing for [role] on [date]." Signals start/end, reinforces brand. |
| **Reliable delivery** | Available at consistent time each morning | Low | Delivered alongside existing email. Archive ensures backup access. |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Role-specific voice personas** | Different voice per role creates identity and recognizability | Low | Azure OpenAI offers 400+ voices across 140+ languages. Assign distinct voice to each role (Broker, Leadership, Compliance, Underwriting) for personality. |
| **Priority-aware content ordering** | Lead with Critical/High priority items; structure mirrors importance | Low | Leverage existing priority classification. "Your top critical item today..." → "Medium priority updates..." → "Items to monitor..." |
| **Contextual emphasis** | Prosody control (SSML) for emphasis on key terms, numbers, entities | Medium | Use SSML `<emphasis>` tags for critical data points (e.g., "share price dropped 15%," entity names). Makes key info stand out audibly. |
| **Embedded entity pronunciation** | Custom lexicon for company names, products, locations | Medium | Build PLS lexicon for frequently mentioned entities. Define once, applied automatically. Prevents recurring mispronunciations. |
| **Dual delivery format** | MP3 attachment + streaming link gives flexibility | Low | Accommodates different listening preferences: download for offline (commute), stream for on-demand. Both point to same file. |
| **Audio archive access** | Historical briefings accessible via admin dashboard | Low | Extends value beyond daily consumption. Useful for missed days, reference, onboarding. Complements existing report archive. |
| **Smart content selection** | AI-driven selection of "must hear" vs. "skim text" items | High | Use existing AI classification to identify stories suitable for audio (high impact, clear narrative) vs. better suited for visual scanning (data tables, long lists). |
| **Progress indicators** | Verbal chapter markers (e.g., "Story 1 of 4") | Low | Helps listeners track position, estimate remaining time. Reduces anxiety about length during commute. |
| **Adaptive scripting** | TTS-optimized script generation (commas for pauses, phonetic spellings) | Medium | Transform existing HTML summary text into TTS-friendly script: add pauses, spell acronyms phonetically, expand abbreviations. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Interactive voice navigation** | "Skip to next story," voice commands | High complexity, low value for 2-5 min format. Requires separate voice recognition stack. Most listeners complete full brief. | Provide timestamped chapters in MP3 metadata for manual scrubbing. Keep duration short enough that skipping is unnecessary. |
| **Personalized AI voices** | "Clone my voice" or "celebrity voice" | Ethical concerns, licensing costs, brand consistency issues. Opens legal/compliance risks for financial services. | Offer 3-4 distinct professional voice personas aligned to roles. Maintain consistent brand identity. |
| **Real-time generation** | Generate audio on-demand when email opened | Increases latency, complicates delivery, risks failures during email open. Azure TTS is fast but not instant (TTFA <300ms target for real-time, not batch). | Pre-generate audio during overnight briefing creation workflow. Include in email as pre-rendered asset. |
| **Full article text narration** | "Read me everything" | Defeats curation purpose. Duration balloons to 20-40+ minutes, causing listener drop-off. Research shows bulletins should be 2-5 min. | Stick to curated summaries. Link to full text in email for deep-dive reading. Audio is overview, not replacement. |
| **Background music** | "Make it feel like a podcast" | Distracting for information-dense briefings. Reduces accessibility (harder for hearing-impaired). Complicates production pipeline. | Use brief music stinger (2-3 sec) for intro/outro only. Keep body content clean for clarity. |
| **Multiple stories per audio file** | "One file per story for sharing" | Fragments experience, creates email clutter (4+ attachments), increases storage/bandwidth. Loses narrative flow. | Single consolidated briefing per role. Use verbal transitions between stories. Easier to consume, simpler delivery. |
| **Variable playback speed controls** | "Let users speed up/slow down" | Already built into every audio player (iOS, Android, Spotify, etc.). Don't rebuild standard functionality. | Rely on native player controls. Focus effort on content quality, not player features. |
| **Transcription alongside audio** | "Provide text version too" | Already exists — it's the HTML email brief. Audio is supplementary format, not replacement. | Audio complements existing HTML brief. Users have text version already. No duplication needed. |

## Feature Dependencies

```
Existing Features (Built)
├── AI-generated role summaries → TTS script source (HIGH)
├── Priority classification → Content ordering (MEDIUM)
├── Entity extraction → Pronunciation lexicon (MEDIUM)
├── Email delivery infrastructure → Audio attachment delivery (HIGH)
├── Admin dashboard → Audio archive integration (LOW)
└── Role-based segmentation → Voice persona assignment (LOW)

New Features (v2.0)
├── TTS script generation
│   ├── Requires: AI-generated summaries (existing)
│   ├── Requires: Content curation logic (new)
│   └── Enables: Audio synthesis
├── Azure OpenAI TTS integration
│   ├── Requires: TTS-optimized scripts
│   ├── Requires: SSML markup for pronunciation
│   └── Produces: MP3 audio files
├── Pronunciation lexicon
│   ├── Requires: Entity extraction (existing)
│   └── Enables: Custom pronunciation via SSML
├── Audio file management
│   ├── Requires: MP3 generation
│   └── Enables: Archive, streaming, email attachment
└── Email delivery enhancement
    ├── Requires: Audio file URLs
    └── Extends: Existing email templates

Future Enhancements (v2.x+)
├── Contextual emphasis (SSML prosody)
│   └── Requires: Sentiment/impact scores (existing)
├── Smart content selection
│   └── Requires: Audio-suitability scoring (new)
└── Progress indicators
    └── Requires: Story count metadata (trivial)
```

## MVP Definition

### Launch With (v2.0)

- [x] **Consistent 2-5 minute duration** — Essential for commute use case; builds listener trust through predictability
- [x] **Clear structural markers** — Intro/outro/transitions for multitasking listeners; minimal complexity
- [x] **High-quality Azure OpenAI TTS** — 48kHz neural voices; baseline expectation in 2026
- [x] **Basic pronunciation handling** — SSML phonetic spelling for common insurance terms; prevents credibility loss
- [x] **Natural pacing** — Script preprocessing: add commas for pauses, avoid run-on sentences
- [x] **Content curation** — Select key points from existing AI summaries; don't read full articles
- [x] **Branded intro/outro** — Professional framing with date, role, source attribution
- [x] **Dual delivery format** — MP3 attachment + streaming link in email
- [x] **Audio archive** — Store in admin dashboard alongside existing report archive
- [x] **Priority-aware ordering** — Lead with Critical/High items using existing classification

**Rationale:** These features form the minimum viable listening experience. They leverage existing infrastructure (summaries, priorities, email, dashboard) while adding essential audio-specific elements (pacing, pronunciation, structure). Complexity is deliberately kept low for v2.0 launch.

### Add After Validation (v2.x)

- [ ] **Role-specific voice personas** — Assign distinct voices per role after validating listener engagement with default voice (v2.1 — 1 week effort)
- [ ] **Custom pronunciation lexicon** — Build PLS lexicon for frequently mentioned entities after identifying top pronunciation issues from user feedback (v2.1 — 2 weeks)
- [ ] **Contextual emphasis** — SSML prosody for critical data points after baseline audio proves successful (v2.2 — 1 week)
- [ ] **Progress indicators** — Verbal chapter markers ("Story 1 of 4") after validating episode structure (v2.2 — trivial)
- [ ] **Adaptive scripting** — Automated TTS optimization pipeline after manual tuning establishes patterns (v2.3 — 2 weeks)

**Validation Triggers:**
- Listener engagement metrics: play rate >40%, completion rate >70%
- User feedback: pronunciation issues, pacing complaints, duration feedback
- Technical stability: audio generation reliability >95%, delivery success >98%

### Future Consideration (v3+)

- [ ] **Smart content selection** — AI-driven audio suitability scoring (requires ML model training on listener engagement data)
- [ ] **MP3 chapter markers** — Embedded metadata for manual scrubbing (requires validation that listeners want navigation in short-form format)
- [ ] **Multi-language support** — Azure supports 140+ languages, but requires localized content pipeline (depends on business expansion)
- [ ] **Integration with podcast platforms** — RSS feed for Apple Podcasts, Spotify (requires assessment of distribution strategy vs. email-only)

**Why Defer:**
- Smart content selection: Requires months of listener data to train effectively
- Chapter markers: Unclear value for 2-5 min format; assess demand first
- Multi-language: No current requirement; build when market expands
- Podcast platforms: Strategic decision needed on public vs. private distribution

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Consistent duration | HIGH | LOW | P0 (MVP) |
| Clear structural markers | HIGH | LOW | P0 (MVP) |
| High-quality TTS | HIGH | MEDIUM | P0 (MVP) |
| Content curation | HIGH | MEDIUM | P0 (MVP) |
| Branded intro/outro | MEDIUM | LOW | P0 (MVP) |
| Proper pronunciation (basic) | HIGH | MEDIUM | P0 (MVP) |
| Natural pacing | HIGH | LOW | P0 (MVP) |
| Dual delivery format | MEDIUM | LOW | P0 (MVP) |
| Audio archive | MEDIUM | LOW | P0 (MVP) |
| Priority-aware ordering | HIGH | LOW | P0 (MVP) |
| Role-specific voices | MEDIUM | LOW | P1 (v2.1) |
| Custom pronunciation lexicon | HIGH | MEDIUM | P1 (v2.1) |
| Contextual emphasis | MEDIUM | MEDIUM | P2 (v2.2) |
| Progress indicators | LOW | LOW | P2 (v2.2) |
| Adaptive scripting | MEDIUM | HIGH | P2 (v2.3) |
| Smart content selection | HIGH | HIGH | P3 (v3.0) |
| MP3 chapter markers | LOW | MEDIUM | P4 (Future) |
| Multi-language support | LOW | HIGH | P4 (Future) |
| Podcast platform integration | MEDIUM | MEDIUM | P4 (Future) |

**Priority Legend:**
- **P0 (MVP)**: Must have for v2.0 launch; forms minimum viable listening experience
- **P1 (Post-Launch)**: Add within 1-2 months after launch based on user feedback
- **P2 (Enhancement)**: Add within 3-6 months if engagement metrics support investment
- **P3 (Advanced)**: Requires significant data collection or technical investment
- **P4 (Future)**: Dependent on strategic decisions or market expansion

## Implementation Notes

### Complexity Drivers

**LOW Complexity:**
- Structural markers (templated text)
- Duration control (content selection)
- Intro/outro (static scripts)
- Priority ordering (existing data)
- Dual delivery (storage + CDN)
- Archive integration (existing dashboard)
- Progress indicators (calculated metadata)
- Role-specific voices (API parameter)

**MEDIUM Complexity:**
- High-quality TTS (Azure integration, error handling)
- Basic pronunciation (SSML tagging common terms)
- Content curation (selection logic from existing summaries)
- Custom lexicon (PLS file creation, entity mapping)
- Contextual emphasis (SSML prosody rules)
- Adaptive scripting (text transformation pipeline)
- MP3 chapter markers (metadata embedding)

**HIGH Complexity:**
- Smart content selection (ML model for audio-suitability scoring)
- Multi-language support (localized content pipeline, translation workflow)
- Real-time generation (streaming TTS, latency optimization) — ANTI-FEATURE

### Technical Dependencies

**Azure OpenAI TTS Capabilities:**
- 400+ neural voices across 140+ languages
- 48kHz high-fidelity audio output (24kHz also available)
- SSML support for pronunciation, prosody, emphasis, pauses
- TTFA <300ms for real-time (not needed for batch generation)
- Per-word timestamps (useful for future chapter markers)
- Voice cloning available but not recommended (compliance risk)

**SSML Features for v2.0:**
- `<phoneme>` tags for pronunciation control
- `<break>` tags for strategic pauses
- `<emphasis>` tags for critical data points (v2.2)
- `<prosody>` for rate/pitch/volume control (v2.2)
- PLS lexicon reference for entity pronunciation (v2.1)

**Content Selection Strategy:**
- Use existing AI-generated role summaries as base
- Extract key points from "What to Watch" sections
- Prioritize narrative-friendly content (avoid dense tables)
- Target 3-5 stories per briefing for 2-5 min duration
- Calculate words-per-minute: ~150 WPM for clear TTS = ~300-750 words total

### Quality Assurance Checklist

**Audio Quality:**
- [ ] No pronunciation errors on insurance/reinsurance terminology
- [ ] Natural pacing with appropriate pauses between sentences
- [ ] Consistent volume levels across entire briefing
- [ ] No clipping or distortion in generated audio
- [ ] Clear enunciation of numbers, percentages, currency values

**Content Quality:**
- [ ] Duration within 2-5 minute target (±15 seconds)
- [ ] All stories include clear attribution and date context
- [ ] Transition phrases between stories are smooth and logical
- [ ] Intro establishes role, date, source clearly
- [ ] Outro provides clear sign-off and next-steps guidance

**Delivery Quality:**
- [ ] MP3 file size reasonable for email attachment (<5MB target)
- [ ] Streaming link accessible without authentication errors
- [ ] Audio plays correctly on iOS Mail, Android Gmail, Outlook
- [ ] Archive retrieval works from admin dashboard
- [ ] File naming convention supports easy identification

## Research Insights

### Key Findings from Competitive Analysis

**Successful Audio Briefing Patterns (2026):**
- **NPR Up First**: 10-15 minutes, 3-4 stories, tight scripting, zero fluff, weekday 6:30am release
- **The Daily (NYT)**: 20-25 minutes, single deep-dive story (different model — not applicable)
- **TIME AI Audio Brief**: Editor-curated selection, not comprehensive coverage
- **Huxe (Google NotebookLM engineers)**: On-demand audio briefings from email/interests

**Common Success Factors:**
- Predictable duration and structure builds listener trust
- Tightly scripted bulletins deliver "who, what, where, when, why" efficiently
- Morning delivery aligns with commute and pre-work routines
- Attention earned through quality and consistency, not hype
- Curation valued over comprehensiveness

### TTS Quality Benchmarks (2026)

**State of the Art:**
- Gap between AI voice and human voice nearly eliminated
- Most listeners won't notice TTS unless actively listening for it
- Perceptual quality, pronunciation accuracy, speaker similarity all at high levels
- Azure/OpenAI neural voices achieve near-human synthesis

**Quality Killers:**
- Mispronounced domain terminology (destroys credibility instantly)
- Robotic pacing from insufficient punctuation
- Reading text verbatim without conversational adaptation
- Poor recording environment (echoes, background noise) — not applicable to TTS
- Substandard equipment — not applicable with cloud TTS

### Listener Expectations (Business Professionals)

**Primary Use Cases:**
- Commute listening (car, train, walking)
- Multitasking consumption (getting ready, exercising)
- Quick catch-up between meetings
- Offline listening (downloaded for travel)

**Convenience Factors:**
- 64% of business leaders say effective communication boosts productivity
- Audio eliminates need for dedicated reading time or additional meetings
- Instant access via email attachment + archive
- Searchable archive for reference and missed days

**Content Preferences:**
- Short, focused updates distilling complex information
- Time-sensitive insights curated for relevance
- Strategic information consumable while on the move
- Complementary to (not replacement for) detailed written reports

## Sources

**Podcast Best Practices:**
- [The 11 Best Daily News Podcasts to Listen to in 2026](https://podcastreview.org/list/best-daily-news-podcasts/)
- [The Podcast Formats Winning Attention in 2026](https://www.podcastvideos.com/articles/podcast-formats-winning-attention-2026/)
- [Journalism, media, and technology trends and predictions 2026 | Reuters Institute](https://reutersinstitute.politics.ox.ac.uk/journalism-media-and-technology-trends-and-predictions-2026)

**TTS Quality & Expectations:**
- [Text-to-Speech Voice AI Model Guide 2026 | Camb.ai](https://www.camb.ai/blog-post/text-to-speech-voice-ai-model-guide)
- [Best Text-to-Speech AI 2026 | AI/ML API Blog](https://aimlapi.com/blog/best-text-to-speech-ai)
- [The state of audio AI in 2026 | Tutorials Dojo](https://tutorialsdojo.com/the-state-of-audio-ai-in-2026-open-source-models-and-the-shift-to-edge-computing/)

**Structure & Pacing:**
- [Daily news podcasts: building new habits | Reuters Institute](https://reutersinstitute.politics.ox.ac.uk/daily-news-podcasts-building-new-habits-shadow-coronavirus)
- [Podcast Episode Length: What Performs Best in 2026? | Podcast Studio Glasgow](https://www.podcaststudioglasgow.com/podcast-studio-glasgow-blog/podcast-episode-length-what-performs-best-in-2026)
- [The Secrets Behind Podcast Structure & Listener Retention | Gray Line Media](https://graylinemedia.com/the-secrets-behind-podcast-structure-listener-retention/)
- [Up First from NPR](https://www.npr.org/podcasts/510318/up-first)
- [Up First - Wikipedia](https://en.wikipedia.org/wiki/Up_First)

**Azure TTS Technical:**
- [OpenAI Text-to-Speech API](https://platform.openai.com/docs/guides/text-to-speech)
- [Best Text to Speech APIs for Developers | Fish Audio Blog](https://fish.audio/blog/top-tts-apis-developer-comparison-2026/)
- [Azure AI Speech: Technology Overview & Best Practices | IT Magination](https://www.itmagination.com/technologies/azure-ai-speech)
- [Text to speech overview - Azure AI services | Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/text-to-speech)

**Audio Production Best Practices:**
- [What are best practices for Text-to-Speech? | Resemble.ai](https://knowledge.resemble.ai/what-are-best-practices-for-text-to-speech)
- [8 Mistakes to Avoid When Producing Professional Audio Content | Metapress](https://metapress.com/8-mistakes-to-avoid-when-producing-professional-audio-content/)
- [Top Tips for Using Text-to-Speech (TTS) in Storyline 360 | Articulate](https://community.articulate.com/blog/articles/top-tips-for-using-text-to-speech-tts-in-storyline-360/1149512)

**Executive Briefing Use Cases:**
- [How to Deliver Internal Executive Briefings via Audio | Hello Audio](https://helloaudio.fm/internal-executive-briefings-via-audio/)
- [Executive News Briefings | Bulletin Intelligence](https://www.bulletinintelligence.com/executive-news-briefings/)
- [Why Every Executive Needs A Personalised News Briefing Service | A Data Pro](https://adata.pro/blog/why-every-executive-needs-a-personalised-news-briefing-service/)

**Content Curation vs. Full Reading:**
- [A comparison of text versus audio for information comprehension | PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6603442/)
- [What is audio content: the one post you need to read | Trinity Audio](https://www.trinityaudio.ai/what-is-audio-content-the-one-post-you-need-to-read-or-listen-to)
- [How the TIME AI Audio Brief Was Built | TIME](https://time.com/7294142/time-ai-audio-brief/)
- [What's the difference between content aggregation and content curation? | Vable](https://www.vable.com/blog/whats-the-difference-between-content-aggregation-and-content-curation?hs_amp=true)

**SSML Pronunciation Control:**
- [Speech Synthesis Markup Language (SSML) overview | Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup)
- [Pronunciation with SSML | Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-pronunciation)
- [Speech Synthesis Markup Language (SSML) | Google Cloud](https://docs.cloud.google.com/text-to-speech/docs/ssml)
- [What is Speech Synthesis Markup Language (SSML)? | Pertama Partners](https://www.pertamapartners.com/glossary/speech-synthesis-markup-language-ssml)
- [Voice Gateway: Using Lexicons to Improve Pronunciation | Cognigy.AI](https://support.cognigy.com/hc/en-us/articles/16307295492124-Voice-Gateway-Using-Lexicons-to-Improve-Pronunciation-in-LLMs-and-Other-Use-Cases)

---
*Feature research for: Audio intelligence briefings*
*Researched: 2026-02-27*
*Confidence: HIGH*
