# Phase 17: Audio Generation Foundation - Research

**Researched:** 2026-02-27
**Domain:** Azure OpenAI TTS, GPT-4o script generation, text preprocessing for speech
**Confidence:** HIGH

## Summary

Azure OpenAI TTS (tts-1-hd) provides production-ready text-to-speech with six professional voices suitable for enterprise audio briefings. The service generates MP3 audio through a simple Python SDK API, with nova or shimmer voices recommended for the required female authoritative tone. Script generation leverages GPT-4o's proven podcast narration capabilities, while text preprocessing uses the num2words library for financial terminology normalization (e.g., "$1.2M" → "one point two million dollars"). Audio duration follows industry standards: 150-160 words per minute yields 300-540 words for 2-5 minute briefings, with MP3 files at 128kbps producing approximately 2-5 MB file sizes.

Key technical finding: OpenAI TTS does not support SSML markup, so all pronunciation control must happen via text preprocessing before TTS conversion. The existing OpenAI SDK (version 2.16.0) in requirements.txt already includes TTS capabilities through the `client.audio.speech.create()` method.

**Primary recommendation:** Build three-step pipeline: (1) GPT-4o script generation with role-specific system prompts, (2) num2words-based text normalization for financial/insurance terms, (3) Azure OpenAI TTS conversion using nova voice with streaming to MP3 files.

## Standard Stack

The established libraries/tools for Azure OpenAI TTS and podcast script generation:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | 2.16.0 | Azure OpenAI TTS client | Already in project requirements.txt, official Python SDK with TTS support via audio.speech API |
| azure-identity | latest | Azure authentication | Already in project requirements.txt, required for Azure OpenAI service authentication |
| num2words | 0.5.13+ | Number to text conversion | Industry standard for financial figure pronunciation (42+ languages, currency support, actively maintained) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.11.0 | Script validation models | Already in project, use for script structure validation before TTS |
| structlog | latest | Audio pipeline logging | Already in project, use for tracking TTS operations and errors |
| tenacity | latest | Retry logic | Already in project, use for Azure OpenAI API resilience |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Azure OpenAI TTS | ElevenLabs API | ElevenLabs offers more voice customization and emotionality but requires separate API integration, higher cost per character, and less Azure ecosystem integration (reserved for Phase 18 fallback) |
| num2words | inflect library | inflect handles pluralization but weaker on currency conversion and lacks the multilingual support of num2words |
| Text preprocessing | SSML markup | OpenAI TTS does not support SSML, so preprocessing is the only viable approach for pronunciation control |

**Installation:**
```bash
pip install num2words
# openai, azure-identity, pydantic, structlog, tenacity already installed
```

## Architecture Patterns

### Recommended Project Structure
```
app/services/
├── audio_generator.py          # New: TTS orchestration service
├── script_generator.py          # New: GPT-4o script creation
├── text_preprocessor.py         # New: Terminology normalization
└── reporter.py                  # Existing: HTML brief generation

output/
├── html/
│   └── YYYY-MM-DD/              # Existing HTML brief storage
└── audio/
    └── YYYY-MM-DD/              # New audio file storage
        ├── brokers.mp3
        ├── leadership.mp3
        ├── compliance.mp3
        └── underwriting.mp3
```

### Pattern 1: Three-Stage Pipeline
**What:** Separate script generation, preprocessing, and TTS conversion into distinct services
**When to use:** Enterprise audio generation requiring quality control and retry logic at each stage
**Example:**
```python
# Source: Azure OpenAI best practices + GPT-4o documentation
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from num2words import num2words
import re
from pathlib import Path

class ScriptGenerator:
    """Stage 1: Generate podcast-style narration scripts"""

    def __init__(self, client: AzureOpenAI):
        self.client = client

    def generate_script(self, role: str, articles: list[dict], date: str) -> str:
        """Generate 300-540 word podcast script for role"""
        system_prompt = self._build_system_prompt(role)
        user_prompt = self._build_user_prompt(articles, date, role)

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,  # Moderate creativity for natural narration
            max_tokens=800    # ~540 words with safety margin
        )
        return response.choices[0].message.content

    def _build_system_prompt(self, role: str) -> str:
        """Role-specific podcast narrator persona"""
        return f"""You are a professional intelligence briefing narrator creating audio scripts for {role}.

Style: Bloomberg/Reuters broadcast quality - authoritative, clear, conversational
Tone: Female voice, professional, confident but not robotic
Structure:
- Branded intro: "Good morning, this is your Marsh {role} intelligence brief for [date]..."
- Priority-ordered content (Critical → High → Medium)
- Source attribution: "Reuters reports..." "According to Financial Times..."
- Clean sign-off: "That's your {role} brief for today. Stay informed."

Requirements:
- 300-540 words (2-5 minute audio at 150 wpm)
- Group articles by theme, don't list individually
- Write for speech, not reading (contractions OK, short sentences)
- Include full natural language for all figures and numbers
"""

    def _build_user_prompt(self, articles: list[dict], date: str, role: str) -> str:
        """Construct prompt with classified articles"""
        # Group by priority
        critical = [a for a in articles if a["priority"] == "Critical"]
        high = [a for a in articles if a["priority"] == "High"]
        medium = [a for a in articles if a["priority"] == "Medium"]

        prompt = f"Create audio script for {date}. Articles by priority:\n\n"

        if critical:
            prompt += "CRITICAL:\n" + "\n".join([f"- {a['headline']} ({a['source']}): {a['summary']}" for a in critical]) + "\n\n"
        if high:
            prompt += "HIGH:\n" + "\n".join([f"- {a['headline']} ({a['source']}): {a['summary']}" for a in high]) + "\n\n"
        if medium:
            prompt += "MEDIUM:\n" + "\n".join([f"- {a['headline']} ({a['source']}): {a['summary']}" for a in medium])

        return prompt


class TextPreprocessor:
    """Stage 2: Normalize financial/insurance terminology for speech"""

    def preprocess(self, script: str) -> str:
        """Convert figures, abbreviations, tickers to speakable text"""
        text = script

        # Financial figures: $1.2M → "one point two million dollars"
        text = self._normalize_currency(text)

        # Percentages: 15.3% → "fifteen point three percent"
        text = self._normalize_percentages(text)

        # Abbreviations: LLC → "L L C"
        text = self._normalize_abbreviations(text)

        # Ticker symbols: (AAPL) → "ticker A A P L" or "Apple"
        text = self._normalize_tickers(text)

        return text

    def _normalize_currency(self, text: str) -> str:
        """Convert $X.XM/B/T to full natural language"""
        patterns = {
            r'\$(\d+\.?\d*)\s?[Bb]illion': lambda m: f"{num2words(float(m.group(1)))} billion dollars",
            r'\$(\d+\.?\d*)\s?[Mm]illion': lambda m: f"{num2words(float(m.group(1)))} million dollars",
            r'\$(\d+\.?\d*)\s?[Kk]': lambda m: f"{num2words(float(m.group(1)))} thousand dollars",
            r'\$(\d+\.?\d*)': lambda m: f"{num2words(float(m.group(1)))} dollars"
        }

        for pattern, replacement in patterns.items():
            text = re.sub(pattern, replacement, text)
        return text

    def _normalize_percentages(self, text: str) -> str:
        """Convert X.X% to spoken form"""
        def replace_percent(match):
            num = float(match.group(1))
            # Handle decimals specially for natural speech
            if '.' in match.group(1):
                integer, decimal = match.group(1).split('.')
                return f"{num2words(int(integer))} point {num2words(int(decimal))} percent"
            return f"{num2words(int(num))} percent"

        return re.sub(r'(\d+\.?\d*)\s?%', replace_percent, text)

    def _normalize_abbreviations(self, text: str) -> str:
        """Expand common insurance/financial abbreviations"""
        # Dictionary of common terms
        replacements = {
            r'\bLLC\b': 'L L C',
            r'\bCEO\b': 'C E O',
            r'\bCFO\b': 'C F O',
            r'\bIPO\b': 'I P O',
            r'\bM&A\b': 'M and A',
            r'\bESG\b': 'E S G',
            r'\bQ[1-4]\b': lambda m: f"Q {m.group(0)[-1]}",  # Q1 → "Q one"
        }

        for pattern, replacement in replacements.items():
            if callable(replacement):
                text = re.sub(pattern, replacement, text)
            else:
                text = re.sub(pattern, replacement, text)
        return text

    def _normalize_tickers(self, text: str) -> str:
        """Handle stock ticker symbols"""
        # Pattern: (AAPL) or AAPL: → spell out as letters
        def spell_ticker(match):
            ticker = match.group(1)
            return " ".join(ticker)  # AAPL → "A A P L"

        text = re.sub(r'\(([A-Z]{2,5})\)', spell_ticker, text)
        return text


class AudioGenerator:
    """Stage 3: Convert preprocessed scripts to MP3 via Azure OpenAI TTS"""

    def __init__(self, client: AzureOpenAI, deployment_name: str = "tts-1-hd"):
        self.client = client
        self.deployment_name = deployment_name
        self.voice = "nova"  # Female, authoritative professional voice

    def generate_audio(self, script: str, output_path: Path) -> dict:
        """Stream TTS audio directly to MP3 file"""
        response = self.client.audio.speech.create(
            model=self.deployment_name,
            voice=self.voice,
            input=script,
            response_format="mp3",  # Default format
            speed=1.0  # Normal speaking pace (150-160 wpm)
        )

        # Stream response to file
        response.stream_to_file(str(output_path))

        # Return metadata
        file_size = output_path.stat().st_size
        return {
            "path": str(output_path),
            "size_bytes": file_size,
            "size_mb": round(file_size / 1_048_576, 2),
            "voice": self.voice,
            "model": self.deployment_name
        }
```

### Pattern 2: Idempotent Audio Generation
**What:** Skip TTS generation if output file already exists for the date/role
**When to use:** Pipeline retries to avoid duplicate API costs
**Example:**
```python
# Source: Azure OpenAI cost optimization patterns
def should_generate_audio(output_dir: Path, role: str, date: str) -> bool:
    """Check if audio already exists for this role and date"""
    audio_file = output_dir / date / f"{role}.mp3"

    if audio_file.exists():
        file_size = audio_file.stat().st_size
        # Validate file is not corrupted (at least 100 KB for 2min audio)
        if file_size > 100_000:
            logger.info(f"Audio exists for {role} on {date}, skipping generation")
            return False
        else:
            logger.warning(f"Audio file corrupted for {role} on {date}, regenerating")
            audio_file.unlink()

    return True
```

### Pattern 3: Retry Logic with Exponential Backoff
**What:** Resilient API calls using tenacity library (already in project)
**When to use:** All Azure OpenAI API calls (GPT-4o script gen + TTS conversion)
**Example:**
```python
# Source: OpenAI best practices + tenacity documentation
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import APIError, RateLimitError, APIConnectionError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIError, RateLimitError, APIConnectionError)),
    reraise=True
)
def generate_with_retry(client, method, **kwargs):
    """Retry wrapper for Azure OpenAI API calls"""
    return method(**kwargs)

# Usage:
response = generate_with_retry(
    client,
    client.audio.speech.create,
    model="tts-1-hd",
    voice="nova",
    input=preprocessed_script
)
```

### Anti-Patterns to Avoid
- **Generating scripts after TTS conversion:** Script must be preprocessed for pronunciation before TTS, not after
- **Using SSML markup:** OpenAI TTS does not support SSML; all pronunciation control via text preprocessing
- **Hardcoded word counts:** Calculate target based on desired duration (150 wpm × 2-5 min = 300-800 words)
- **Storing intermediate scripts:** Discard scripts after TTS to avoid clutter; only retain final MP3
- **Combining all roles into one audio:** Each role must have separate audio file per requirements

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Number to words conversion | Custom regex-based converter | num2words library | Handles edge cases (decimals, fractions, ordinals, currency), supports 42+ languages, battle-tested for financial applications |
| TTS retry logic | Manual sleep/retry loops | tenacity library (already in project) | Exponential backoff, jitter, configurable stop conditions, exception filtering |
| Audio file validation | Custom file size/format checks | Pathlib + MP3 metadata validation | Standard library for file operations, avoid reinventing binary format parsing |
| Date-based directory structure | String concatenation for paths | pathlib.Path with date objects | Cross-platform path handling, automatic directory creation with .mkdir(parents=True) |
| Script word counting | len(text.split()) | Proper tokenization considering contractions | "don't" is 1 word for audio duration, not 2 tokens |
| Pronunciation dictionary | Hardcoded string replacements | Centralized config with regex patterns | Maintainable, testable, extensible for future terms |

**Key insight:** Text preprocessing for TTS is more complex than it appears. Financial figures require context-aware conversion ("$1.2M" in isolation vs. in a sentence), abbreviations need industry-specific knowledge (LLC vs L.L.C. vs "limited liability company"), and ticker symbols require company name lookups for natural speech. num2words handles the numeric complexity; focus custom logic on domain-specific abbreviations.

## Common Pitfalls

### Pitfall 1: Underestimating Script Length Variability
**What goes wrong:** Scripts that are perfectly 300 words may run 1:45 or 2:15 depending on content complexity (numbers, pauses, source attribution)
**Why it happens:** TTS speaking rate varies by content type: complex financial terms slow down, simple narrative flows faster
**How to avoid:**
- Target 300-540 word range (not exact count) to allow 2-5 minute flexibility
- Test actual audio duration during development with sample scripts
- Include word count in GPT-4o system prompt as guidance, not hard constraint
- Log actual duration vs. word count to refine estimates
**Warning signs:** Consistent under/over-runs on duration despite hitting word targets

### Pitfall 2: Inadequate Pronunciation Testing
**What goes wrong:** TTS mispronounces industry-specific terms (e.g., "Chubb" as "chub", "Aon" as "ay-on")
**Why it happens:** Azure OpenAI TTS trained on general corpus, lacks insurance/reinsurance domain knowledge
**How to avoid:**
- Build pronunciation dictionary incrementally based on actual mispronunciations
- Test with real article data, not synthetic examples
- Include phonetic respellings in preprocessing (e.g., "Chubb" → "Chub insurance")
- Log preprocessing transformations for debugging
**Warning signs:** User feedback on "weird pronunciations", unnatural pauses around company names

### Pitfall 3: SSML Assumption
**What goes wrong:** Developers attempt to use SSML markup for pronunciation control, which OpenAI TTS ignores
**Why it happens:** Prior experience with Google Cloud TTS, Amazon Polly, or Azure Speech Services (different from Azure OpenAI)
**How to avoid:**
- ALL pronunciation control via text preprocessing before TTS API call
- Test TTS output with raw text vs. SSML-marked text to confirm no effect
- Document in code comments that SSML is not supported
**Warning signs:** SSML tags appearing in audio as spoken text ("less than phoneme greater than")

### Pitfall 4: Voice Consistency vs. Role Differentiation Confusion
**What goes wrong:** Attempting to use different TTS voices for different roles, violating AUDIO-04 requirement
**Why it happens:** Misinterpreting "subtle tonal variation" as voice changes rather than script language changes
**Why it happens:** Confusion between user requirement for "one consistent voice" and natural desire for role differentiation
**How to avoid:**
- Use single voice (nova or shimmer) for ALL four roles
- Differentiate roles via script language/style in GPT-4o prompts, not TTS voice parameter
- Test all four role audios back-to-back to confirm voice consistency
**Warning signs:** Different `voice` parameter values in code for different roles

### Pitfall 5: Synchronous TTS Blocking Pipeline
**What goes wrong:** Pipeline waits sequentially for each role's TTS conversion (4× slower than necessary)
**Why it happens:** Simple sequential implementation without considering parallel processing opportunity
**How to avoid:**
- Generate all four scripts first (can be sequential)
- Convert all four scripts to audio in parallel (asyncio or ThreadPoolExecutor)
- Wait for all TTS completions before proceeding to next pipeline stage
**Warning signs:** Audio generation taking >2 minutes when Azure OpenAI TTS typically completes in 10-30 seconds

### Pitfall 6: Ignoring File System Race Conditions
**What goes wrong:** Concurrent audio generation attempts overwrite or corrupt MP3 files
**Why it happens:** Multiple pipeline runs or parallel role processing without file locking
**How to avoid:**
- Use date-based directory structure: `output/audio/YYYY-MM-DD/role.mp3`
- Implement idempotent generation check (skip if file exists and valid)
- Write to temp file first, then atomic rename to final name
- Log file operations with structlog for debugging
**Warning signs:** Intermittent zero-byte files, corrupted MP3s, "file in use" errors

## Code Examples

Verified patterns from official sources:

### Azure OpenAI Client Initialization (Keyless Authentication)
```python
# Source: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/text-to-speech-quickstart
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

endpoint = "https://your-resource.openai.azure.com"
deployment_name = "tts-1-hd"

# Recommended: Keyless auth with Managed Identity
credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(
    credential,
    "https://cognitiveservices.azure.com/.default"
)

client = AzureOpenAI(
    azure_endpoint=endpoint,
    azure_ad_token_provider=token_provider,
    api_version="2024-08-01-preview"
)
```

### TTS Audio Generation with Streaming
```python
# Source: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/text-to-speech-quickstart
from pathlib import Path

def generate_audio_streaming(client: AzureOpenAI, script: str, output_path: Path):
    """Stream TTS audio directly to file"""
    response = client.audio.speech.create(
        model="tts-1-hd",
        voice="nova",  # Female, professional, authoritative
        input=script,
        response_format="mp3"
    )

    # Stream to file (efficient for large audio)
    response.stream_to_file(str(output_path))
```

### Financial Figure Preprocessing
```python
# Source: https://pypi.org/project/num2words/ + industry best practices
from num2words import num2words
import re

def normalize_financial_figures(text: str) -> str:
    """Convert financial shorthand to natural speech"""

    # $1.2B → "one point two billion dollars"
    text = re.sub(
        r'\$(\d+\.?\d*)\s?[Bb]illion',
        lambda m: f"{num2words(float(m.group(1)))} billion dollars",
        text
    )

    # $150M → "one hundred fifty million dollars"
    text = re.sub(
        r'\$(\d+\.?\d*)\s?[Mm]illion',
        lambda m: f"{num2words(float(m.group(1)))} million dollars",
        text
    )

    # $25K → "twenty-five thousand dollars"
    text = re.sub(
        r'\$(\d+\.?\d*)\s?[Kk]',
        lambda m: f"{num2words(float(m.group(1)))} thousand dollars",
        text
    )

    # 15.3% → "fifteen point three percent"
    def replace_percent(match):
        num_str = match.group(1)
        if '.' in num_str:
            integer, decimal = num_str.split('.')
            return f"{num2words(int(integer))} point {num2words(int(decimal))} percent"
        return f"{num2words(int(float(num_str)))} percent"

    text = re.sub(r'(\d+\.?\d*)\s?%', replace_percent, text)

    return text

# Example:
# "$1.2B investment at 15.3% IRR"
# → "one point two billion dollars investment at fifteen point three percent I R R"
```

### GPT-4o Podcast Script Generation Prompt
```python
# Source: https://cleanvoice.ai/blog/chatgpt-for-podcasting/ + phase context
def build_script_generation_prompt(role: str, date: str, articles: list[dict]) -> dict:
    """System + user prompts for GPT-4o podcast script generation"""

    system_prompt = f"""You are a professional intelligence briefing narrator creating audio scripts for Marsh {role}.

**Audio Character:**
- Voice: Female, authoritative, clear, confident, professional broadcast quality
- Style: Bloomberg/Reuters morning briefing - conversational but credible
- Pacing: Brisk but clear, natural speaking rhythm (150 words per minute)

**Script Structure:**
1. Branded intro: "Good morning, this is your Marsh {role} intelligence brief for [date]..."
2. Priority-ordered content:
   - Critical priority stories first
   - High priority stories second
   - Medium priority stories last
3. Content synthesis: Group related articles by theme, weave into flowing narrative (not individual article summaries)
4. Source attribution: Include source names for credibility ("Reuters reports...", "According to the Financial Times...")
5. Clean sign-off: "That's your {role} brief for today. Stay informed."

**Writing Guidelines:**
- Target 300-540 words (2-5 minute audio duration)
- Write for listening, not reading: short sentences, contractions acceptable, conversational flow
- Use natural language for ALL numbers and figures (write out "one point two million dollars", not "$1.2M")
- Avoid jargon without context; explain industry terms briefly
- Role-specific language: Adjust terminology and focus based on {role} domain expertise

**Tone by Role:**
- Brokers: Action-oriented, market-focused, competitive intelligence
- Leadership: Strategic, big-picture, market trends and implications
- Compliance: Risk-focused, regulatory emphasis, clear guidance
- Underwriting: Technical, exposure-focused, data-driven insights
"""

    # Build user prompt with classified articles
    critical = [a for a in articles if a["priority"] == "Critical"]
    high = [a for a in articles if a["priority"] == "High"]
    medium = [a for a in articles if a["priority"] == "Medium"]

    user_prompt = f"Create podcast-style narration script for {date}.\n\n"

    if critical:
        user_prompt += "**CRITICAL PRIORITY:**\n"
        for article in critical:
            user_prompt += f"- {article['headline']} ({article['source']})\n  {article['summary']}\n\n"

    if high:
        user_prompt += "**HIGH PRIORITY:**\n"
        for article in high:
            user_prompt += f"- {article['headline']} ({article['source']})\n  {article['summary']}\n\n"

    if medium:
        user_prompt += "**MEDIUM PRIORITY:**\n"
        for article in medium:
            user_prompt += f"- {article['headline']} ({article['source']})\n  {article['summary']}\n\n"

    return {
        "system": system_prompt,
        "user": user_prompt
    }
```

### Idempotent Audio Generation with Validation
```python
# Source: Industry best practices for API cost optimization
from pathlib import Path
import structlog

logger = structlog.get_logger()

def generate_role_audio_idempotent(
    role: str,
    date: str,
    script: str,
    output_dir: Path,
    audio_generator: 'AudioGenerator'
) -> dict:
    """Generate audio only if not already exists and valid"""

    # Create date-specific directory
    date_dir = output_dir / date
    date_dir.mkdir(parents=True, exist_ok=True)

    audio_path = date_dir / f"{role}.mp3"

    # Check if already exists
    if audio_path.exists():
        file_size = audio_path.stat().st_size

        # Validate minimum size (100 KB for 2-minute audio at 128kbps)
        if file_size > 100_000:
            logger.info(
                "audio_exists_skipping",
                role=role,
                date=date,
                path=str(audio_path),
                size_mb=round(file_size / 1_048_576, 2)
            )
            return {
                "role": role,
                "date": date,
                "path": str(audio_path),
                "size_mb": round(file_size / 1_048_576, 2),
                "generated": False,
                "reason": "already_exists"
            }
        else:
            logger.warning(
                "audio_corrupted_regenerating",
                role=role,
                date=date,
                size_bytes=file_size
            )
            audio_path.unlink()

    # Generate new audio
    logger.info("generating_audio", role=role, date=date)
    metadata = audio_generator.generate_audio(script, audio_path)
    metadata.update({
        "role": role,
        "date": date,
        "generated": True
    })

    logger.info(
        "audio_generated",
        role=role,
        date=date,
        size_mb=metadata["size_mb"]
    )

    return metadata
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SSML markup for pronunciation | Text preprocessing before TTS | 2024 (OpenAI TTS launch) | Requires all pronunciation control via text normalization; SSML not supported |
| Separate TTS and LLM providers | Unified Azure OpenAI (GPT-4o + TTS) | 2023-2024 | Single API endpoint, consistent auth, simplified stack |
| Manual script writing | LLM-generated podcast scripts | 2023 (GPT-4 capability) | GPT-4o can generate broadcast-quality narration with proper prompting |
| Custom voice cloning | Standard TTS voices (nova, shimmer) | 2024 (OpenAI TTS quality) | Professional quality without custom training; faster deployment |
| inflect library for numbers | num2words library | Ongoing | num2words better for financial/currency conversion, multilingual support |
| tts-1 model | tts-1-hd model | 2024 | Higher audio quality for professional enterprise use cases |

**Deprecated/outdated:**
- **SSML for OpenAI TTS:** Not supported; all tutorials showing SSML with OpenAI are incorrect
- **API key authentication:** Azure recommends Managed Identity (DefaultAzureCredential) over API keys for security
- **Synchronous TTS calls:** Modern pattern uses streaming to file for memory efficiency
- **openai library <1.0:** Version 1.x+ has breaking changes; ensure 1.0+ for audio.speech API

## Open Questions

Things that couldn't be fully resolved:

1. **Azure OpenAI TTS regional availability**
   - What we know: Microsoft documentation states North Central US and Sweden Central regions support tts-1/tts-1-hd
   - What's unclear: Whether project's existing Azure OpenAI deployment is in a supported region, or requires new deployment
   - Recommendation: Verify existing Azure OpenAI resource region; create new deployment in North Central US if needed

2. **Exact voice selection between nova and shimmer**
   - What we know: Both are female voices suitable for professional narration
   - What's unclear: Subtle tonal differences between the two for "authoritative" vs. "conversational" balance
   - Recommendation: Generate sample audio with both voices during implementation, user selects preferred voice based on actual output

3. **GPT-4o token costs for daily script generation**
   - What we know: 4 roles × ~800 tokens output + prompt = ~5K tokens/day
   - What's unclear: Existing Azure OpenAI budget allocation for additional GPT-4o usage beyond classification
   - Recommendation: Monitor costs in Phase 17 implementation; script generation is <10% of current classification usage

4. **Company name pronunciation dictionary scope**
   - What we know: Insurance industry has unique company names (Chubb, Aon, Tokio Marine, etc.)
   - What's unclear: How many company names need custom pronunciation entries, vs. TTS handling correctly by default
   - Recommendation: Build incrementally based on actual mispronunciations; start with top 20 insurance carriers

5. **Audio duration variance acceptable range**
   - What we know: Requirement is 2-5 minutes (300-800 word range at 150 wpm)
   - What's unclear: Whether 1:55 or 5:10 is acceptable, or hard cutoffs enforced
   - Recommendation: Treat 2-5 minutes as guidance; focus on content quality over strict duration (flag for validation if <1:30 or >6:00)

## Sources

### Primary (HIGH confidence)
- [Azure OpenAI TTS Quickstart](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/text-to-speech-quickstart) - Official Microsoft documentation for tts-1-hd deployment, Python SDK, voice options
- [OpenAI TTS API Documentation](https://platform.openai.com/docs/guides/text-to-speech) - Official API reference for audio.speech.create(), voice characteristics, format options
- [OpenAI Audio API Reference](https://platform.openai.com/docs/api-reference/audio/createSpeech) - Technical API specification for parameters and response formats
- [num2words PyPI](https://pypi.org/project/num2words/) - Official library documentation for number-to-words conversion with currency support
- [Azure OpenAI GitHub Sample](https://github.com/LazaUK/AOAI-TextToSpeech-SDKv1) - Working Python SDK v1 example for Azure OpenAI TTS

### Secondary (MEDIUM confidence)
- [OpenAI TTS Voice Guide](https://skywork.ai/skypage/en/OpenAI-TTS-The-Ultimate-Guide-to-AI-Powered-Voice-Generation/1972920505343864832) - Voice characteristics and professional applications
- [AI Podcast Generation 2026](https://podcast.chandlernguyen.com/blog/what-is-ai-podcast-generation) - Current state of LLM-generated podcast scripts
- [ChatGPT Podcast Prompting](https://cleanvoice.ai/blog/chatgpt-for-podcasting/) - GPT-4o script generation best practices
- [TTS Duration Calculator](https://speechify.com/blog/text-speech-how-many-minutes/) - Word count to audio duration conversion
- [SSML Pronunciation Guide](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-pronunciation) - Azure Speech Services (different from Azure OpenAI TTS, but useful for understanding SSML limitations)

### Tertiary (LOW confidence, marked for validation)
- [n8n GPT-4o Podcast Workflow](https://n8n.io/workflows/6138-convert-documents-to-podcast-audio-with-gpt-4o-and-openai-tts/) - Community workflow example (unverified in production)
- [Audio File Size Calculator](https://www.colincrawley.com/audio-file-size-calculator/) - Generic MP3 bitrate calculations (not Azure OpenAI specific)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Azure OpenAI SDK already in project, num2words well-documented, official Microsoft guidance
- Architecture: HIGH - Three-stage pipeline pattern verified in official samples, idempotent generation is industry standard
- Pitfalls: HIGH - SSML limitation confirmed in official docs, voice consistency from requirements, duration variance from TTS research
- Code examples: HIGH - All examples sourced from official Microsoft/OpenAI documentation or established libraries
- Voice selection: MEDIUM - nova/shimmer recommendation based on documentation descriptions, actual testing needed
- Company pronunciations: MEDIUM - Industry-specific requirement, dictionary scope needs validation with real data

**Research date:** 2026-02-27
**Valid until:** 2026-04-27 (60 days - Azure OpenAI TTS is stable service, low change frequency)
