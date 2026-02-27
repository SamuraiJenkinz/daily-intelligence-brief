# Phase 17: Audio Generation Foundation - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

System generates 2-5 minute per-role podcast-style audio briefings from classified articles. Covers script generation (GPT-4o), terminology preprocessing for speech, and TTS conversion to MP3 (Azure OpenAI tts-1-hd). Four roles, one consistent voice, priority-ordered content. Provider fallback, pipeline integration, email delivery, and archive are separate phases (18-20).

</domain>

<decisions>
## Implementation Decisions

### Script style & structure
- Synthesised overview narration — articles grouped by theme and woven into a flowing brief, not narrated individually per article
- Content ordered by priority (Critical / High / Medium) per SCRPT-03 requirement
- Branded intro: "Good morning, this is your Marsh [Role] intelligence brief for [date]..."
- Sign-off: Brief and professional — "That's your [Role] brief for today. Stay informed." style
- Source attribution included — "Reuters reports that..." / "According to the Financial Times..." adds credibility
- Full natural language for financial figures — "one point two million dollars", "fifteen point three percent"

### Voice & audio character
- Female, authoritative voice — clear, confident, professional broadcast quality
- Conversational pacing — natural speaking speed, brisk but clear, fits more content in the 2-5 min window
- Subtle tonal variation between roles — achieved through script language/style, not TTS voice changes (same voice for all four roles per AUDIO-04)

### Terminology preprocessing
- Financial figures spoken in full natural language ("$1.2M" → "one point two million dollars")
- Source names included in speech ("According to Reuters...")
- Abbreviation and ticker handling at Claude's discretion — build a pronunciation dictionary based on industry conventions

### Output & file management
- File naming: date-role pattern — `2026-02-27_brokers.mp3`
- Storage path: `output/audio/YYYY-MM-DD/` — alongside existing HTML brief output, organized by date
- Intermediate scripts discarded after TTS conversion — only final MP3 retained
- Re-run behavior: skip if today's audio already exists for a role (saves API costs on pipeline retries)

### Claude's Discretion
- Priority tier depth weighting — balance airtime per tier based on the day's content volume and significance
- Transitions between priority tiers — decide whether explicit callouts or subtle tonal shifts sound more natural
- Role-specific script style — craft role-appropriate language based on each role's content domain
- Abbreviation pronunciation rules — build dictionary of insurance/financial terms with correct spoken forms
- Ticker symbol handling — determine most natural way to reference companies in spoken audio
- Azure TTS voice selection — choose the specific Azure voice that best fits "female, authoritative, professional"

</decisions>

<specifics>
## Specific Ideas

- Briefings should feel like a professional morning intelligence podcast — think Bloomberg or Reuters audio briefings
- Source attribution adds credibility: "Reuters reports that..." not just bare facts
- Sign-off should be clean and consistent, not forward-looking or teaser-style
- Same voice across all roles, but script language naturally adapts to the domain (broking vs claims vs equity)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-audio-generation-foundation*
*Context gathered: 2026-02-27*
