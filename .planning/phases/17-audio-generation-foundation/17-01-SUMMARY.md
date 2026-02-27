---
phase: 17-audio-generation-foundation
plan: 01
subsystem: audio
tags: [openai-tts, gpt-4o, text-preprocessing, num2words, audio-generation, podcast-scripts]

# Dependency graph
requires:
  - phase: 01-mvp-core-pipeline
    provides: Azure OpenAI client initialization patterns (reporter.py, classifier.py)
  - phase: 02-brief-generation
    provides: Article dict structure from reporter.py _prepare_articles
provides:
  - Text preprocessing service for TTS-ready financial terminology normalization
  - GPT-4o script generator for 300-540 word podcast-style narration
  - num2words dependency for number-to-words conversion
affects: [17-02, 17-03, 19-pipeline-integration]

# Tech tracking
tech-stack:
  added: [num2words>=0.5.13]
  patterns: [Text preprocessing for TTS, GPT-4o podcast script generation, Priority-ordered content synthesis]

key-files:
  created: [app/services/text_preprocessor.py, app/services/script_generator.py]
  modified: [requirements.txt]

key-decisions:
  - "All pronunciation control via text preprocessing (OpenAI TTS does not support SSML)"
  - "Same Azure OpenAI client pattern as reporter.py (corporate proxy support)"
  - "Role-specific tone guidance in system prompts (not TTS voice changes)"
  - "Branded intro and sign-off for consistent Marsh identity"
  - "Articles use same dict structure as reporter.py output (no custom schema)"

patterns-established:
  - "Five-category text preprocessing: currency, percentages, abbreviations, tickers, company names"
  - "Priority-ordered script generation: Critical -> High -> Medium"
  - "Synthesized overview narration: group by theme, not per-article"
  - "Natural language for all figures: write for listening, not reading"
  - "Graceful fallback when Azure OpenAI not configured"

# Metrics
duration: 9min
completed: 2026-02-27
---

# Phase 17 Plan 01: Audio Generation Foundation Summary

**Text preprocessing service converts financial terminology to TTS-ready natural speech, GPT-4o generates 300-540 word podcast-style scripts with role-specific tone and priority-ordered content**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-27T11:09:09Z
- **Completed:** 2026-02-27T11:17:48Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- TextPreprocessor normalizes financial figures ($1.2B → "one point two billion dollars"), percentages (15.3% → "fifteen point three percent"), abbreviations (LLC → "L L C"), tickers ((AAPL) → "A A P L"), and company names (Aon → "A-on") for natural speech
- ScriptGenerator creates 300-540 word podcast-style scripts using GPT-4o with branded intro ("Good morning, this is your Marsh [Role] intelligence brief..."), priority-ordered content, source attribution, and role-specific tone
- num2words library installed for robust number-to-words conversion with currency support

## Task Commits

Each task was committed atomically:

1. **Task 1: Create text preprocessor service and install num2words** - `9a760ee` (feat)
2. **Task 2: Create script generator service** - `346d48c` (feat)

## Files Created/Modified
- `requirements.txt` - Added num2words>=0.5.13 dependency after tenacity line
- `app/services/text_preprocessor.py` - TextPreprocessor with five normalization categories and transformation tracking
- `app/services/script_generator.py` - ScriptGenerator with GPT-4o integration, retry logic, and role-specific tone guidance

## Decisions Made

All decisions followed plan as specified:
- Text preprocessing handles all pronunciation control (OpenAI TTS does not support SSML)
- Azure OpenAI client initialization follows reporter.py pattern (corporate proxy with /deployments/ support)
- Role-specific tone achieved via script language in GPT-4o prompts, not TTS voice parameter changes
- Branded intro and sign-off ensure consistent Marsh identity across all roles
- Articles reuse reporter.py _prepare_articles dict structure (keys: title, description, source_name, priority, summary, sentiment, category, roles)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all components implemented smoothly following established patterns from classifier.py and reporter.py.

## User Setup Required

None - no external service configuration required. Services gracefully handle missing Azure OpenAI configuration by returning fallback text.

## Next Phase Readiness

**Ready for Phase 17-02 (TTS Conversion):**
- Text preprocessing service available for normalizing GPT-4o scripts before TTS
- Script generator produces TTS-ready scripts (no SSML, natural language figures)
- Both services follow established project patterns (structlog, tenacity, Settings-based config)

**Ready for Phase 19 (Pipeline Integration):**
- ScriptGenerator accepts same article dict structure as reporter.py uses
- Can be called with filtered articles per role
- Graceful fallback ensures pipeline won't break if Azure OpenAI unavailable

**No blockers or concerns** - foundation services complete and verified.

---
*Phase: 17-audio-generation-foundation*
*Completed: 2026-02-27*
