# Architecture Research: Audio Intelligence Briefings Integration

**Domain:** Audio intelligence briefings (podcast-style narration)
**Researched:** 2026-02-27
**Confidence:** HIGH

## Executive Summary

This research examines how to integrate per-role audio briefing generation into the existing MDInsights Python/FastAPI pipeline. The system currently follows a linear pattern: Factiva collection → GPT-4o classification → Jinja2 HTML generation → email delivery. Audio generation extends this by adding: script generation (GPT-4o) → TTS conversion (Azure OpenAI) → storage (filesystem) → delivery (email attachment + streaming endpoint).

**Key Integration Point:** Audio generation occurs as **Step 5c** in the existing pipeline, immediately after Step 5b (HTML report archiving) and before Step 8 (email delivery). This allows audio files to be attached to emails without changing the core pipeline structure.

**Storage Strategy:** Filesystem storage in `data/audio/` directory (not SQLite BLOBs). Audio files are 2-5 minutes (approximately 2-4 MB per role), making filesystem more appropriate than database storage for streaming performance and backup simplicity.

**Delivery Strategy:** Dual delivery — email attachment (under 10 MB enterprise limit) + streaming link to FastAPI endpoint with range request support for web player functionality.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          EXISTING PIPELINE                              │
│                                                                           │
│  Step 1: Factiva Collection                                             │
│           └─> Step 2: Query Articles                                    │
│                       └─> Step 3: GPT-4o Classification                 │
│                                   └─> Step 4: Re-query Classified       │
│                                           └─> Step 5: Report Generation │
│                                                   ├─> Browser HTML       │
│                                                   └─> Step 5b: Archive  │
└───────────────────────────────────────────────────────────────────────────┘
                                                          │
                                                          v
┌─────────────────────────────────────────────────────────────────────────┐
│                         NEW: AUDIO GENERATION                           │
│                                                                           │
│  Step 5c: Audio Generation (NEW — parallel per role)                   │
│           ├─> Script Writer: GPT-4o generates podcast script           │
│           │   Input: classified articles + role + executive summary    │
│           │   Output: natural narration with intro/outro branding      │
│           │                                                              │
│           ├─> TTS Client: Azure OpenAI text-to-speech                  │
│           │   Input: script text                                        │
│           │   Output: MP3 audio bytes                                   │
│           │                                                              │
│           └─> Audio Storage: Write to data/audio/{role}/{date}.mp3     │
│               Record metadata in audio_briefs table                     │
└───────────────────────────────────────────────────────────────────────────┘
                                                          │
                                                          v
┌─────────────────────────────────────────────────────────────────────────┐
│                       ENHANCED EMAIL DELIVERY                           │
│                                                                           │
│  Step 8: Email Delivery (MODIFIED)                                     │
│          ├─> Attach MP3 file (2-4 MB, under 10 MB enterprise limit)   │
│          └─> Include streaming link to /api/audio/{role}/{date}        │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Typical Implementation | Integration Point |
|-----------|----------------|------------------------|-------------------|
| **ScriptWriterService** | Generate podcast-style narration script from classified articles | GPT-4o with custom prompt template. Produces 500-800 word script with branded intro/outro. | New service in `app/services/audio/` |
| **TTSClient** | Convert script text to MP3 audio | Azure OpenAI TTS API (tts-1-hd model, alloy voice). Returns audio bytes. | New client in `app/services/audio/` |
| **AudioStorageManager** | Write MP3 files to filesystem and record metadata in database | Filesystem operations + SQLAlchemy ORM for audio_briefs table. | New service in `app/services/audio/` |
| **AudioStreamer** | Serve audio files with range request support | FastAPI FileResponse with `media_type="audio/mpeg"`. Handles HTTP Range headers. | New router in `app/routers/audio.py` |
| **AudioBrief (model)** | Database record for audio file metadata | SQLAlchemy model with role, date, filepath, duration, file_size, script_text. | New model in `app/models/audio_brief.py` |
| **PipelineOrchestrator (modified)** | Add Step 5c audio generation after HTML archiving | Call AudioGenerationService.generate_all_role_audios() after Step 5b. | Modified in `app/services/pipeline.py` |
| **EnterpriseEmailClient (modified)** | Attach audio files to email delivery | Add attachments parameter to send_email(). Include streaming link in email HTML. | Modified in `app/services/enterprise_emailer.py` |
| **Admin Dashboard (enhanced)** | Browse audio archive with web player | New route /admin/audio with audio player component. List by role and date. | New template in `app/templates/admin/audio.html` |

---

## Recommended Project Structure

```
app/
├── services/
│   ├── audio/                   # NEW: audio generation services
│   │   ├── __init__.py
│   │   ├── script_writer.py     # ScriptWriterService (GPT-4o script generation)
│   │   ├── tts_client.py        # TTSClient (Azure OpenAI TTS)
│   │   ├── storage_manager.py   # AudioStorageManager (filesystem + DB)
│   │   └── generator.py         # AudioGenerationService (orchestrator)
│   ├── pipeline.py              # MODIFIED: add Step 5c audio generation
│   ├── enterprise_emailer.py    # MODIFIED: add audio attachment support
│   └── ...
│
├── routers/
│   ├── audio.py                 # NEW: audio streaming endpoints
│   ├── admin.py                 # MODIFIED: add audio archive routes
│   └── ...
│
├── models/
│   ├── audio_brief.py           # NEW: AudioBrief ORM model
│   └── ...
│
├── templates/
│   ├── email/
│   │   └── role_email.html      # MODIFIED: add audio player + download link
│   ├── admin/
│   │   ├── audio.html           # NEW: audio archive browser
│   │   └── audio_player.html    # NEW: web player component
│   └── ...
│
└── schemas/
    └── audio.py                  # NEW: AudioBriefResponse, AudioMetadata schemas

data/
├── audio/                        # NEW: audio file storage (not in git)
│   ├── brokers/
│   │   ├── 2026-02-27.mp3
│   │   ├── 2026-02-26.mp3
│   │   └── ...
│   ├── leadership/
│   │   └── ...
│   ├── compliance/
│   │   └── ...
│   └── underwriting/
│       └── ...
├── reports/                      # EXISTING: HTML report archive
│   └── ...
└── mdinsights.db                 # EXISTING: SQLite database (add audio_briefs table)
```

---

## Data Flow

### Phase 1: Script Generation (Parallel per Role)

```
classified_articles + executive_summary
                    │
                    v
        ┌───────────────────────┐
        │  ScriptWriterService  │  ← GPT-4o with podcast prompt
        └───────────────────────┘
                    │
                    v
            podcast_script
            (500-800 words)
      ┌─────────────────────────┐
      │ "Good morning. This is │
      │  the Brokers Brief for │
      │  February 27th. Today's│
      │  top priority story..." │
      └─────────────────────────┘
```

**Input Context for Script Generation:**
- Role name (Brokers, Leadership, Compliance, Underwriting)
- Report date
- Executive summary (already generated in Step 5)
- Top 5-7 articles (title, summary, priority)
- Company name for branding

**Script Structure:**
1. Branded intro: "Good morning, this is the [Role] Brief for [Date]."
2. Executive summary narration (2-3 key themes)
3. Priority story walkthrough (3-5 top stories with context)
4. Closing with actionable takeaway
5. Branded sign-off: "That's your [Role] Brief. Full details in your email."

### Phase 2: TTS Conversion (Parallel per Role)

```
podcast_script
      │
      v
┌─────────────────┐
│   TTSClient     │  ← Azure OpenAI TTS (tts-1-hd, alloy voice)
└─────────────────┘
      │
      v
  audio_bytes
  (MP3, 2-4 MB)
```

**Azure OpenAI TTS Configuration:**
- Model: `tts-1-hd` (high-definition quality)
- Voice: `alloy` (professional, neutral tone)
- Speed: 1.0 (normal pace)
- Response format: `mp3` (compressed audio)
- Estimated size: 2-4 MB for 2-5 minute narration

### Phase 3: Storage (Filesystem + Database)

```
audio_bytes + metadata
         │
         v
┌────────────────────────┐
│ AudioStorageManager    │
└────────────────────────┘
         │
         ├─> Write MP3 to data/audio/{role}/{date}.mp3
         │   (Filesystem storage)
         │
         └─> Record metadata in audio_briefs table
             (SQLite database)
```

**Filesystem Structure:**
- Base path: `data/audio/`
- Role subdirectories: `brokers/`, `leadership/`, `compliance/`, `underwriting/`
- Filename format: `YYYY-MM-DD.mp3` (e.g., `2026-02-27.mp3`)
- Permissions: 644 (read for web server, write for pipeline)

**Database Record (audio_briefs table):**
```sql
CREATE TABLE audio_briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    role TEXT NOT NULL,
    report_date DATE NOT NULL,
    filepath TEXT NOT NULL,
    file_size INTEGER,
    duration_seconds INTEGER,
    script_text TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id),
    UNIQUE(role, report_date)
);
```

### Phase 4: Email Delivery (Attachment + Link)

```
MP3 file (2-4 MB) + streaming_url
            │
            v
┌────────────────────────────┐
│  EnterpriseEmailClient     │
└────────────────────────────┘
            │
            ├─> Attach MP3 to email (enterprise supports up to 10 MB)
            │   Content-Type: audio/mpeg
            │   Filename: {company_name}_{role}_brief_{date}.mp3
            │
            └─> Include streaming link in HTML body:
                <a href="https://mdinsights.marsh.com/api/audio/{role}/{date}">
                  Stream Online
                </a>
```

**Email Attachment Strategy:**
- **Pros:** Offline playback, no internet required, familiar UX
- **Cons:** Email size increases, attachment scanning delays
- **Decision:** Include both attachment AND streaming link for flexibility

**Streaming Link Benefits:**
- Reduces email size pressure if attachment fails
- Web player with seek/scrubbing functionality
- Archive access without searching email

### Phase 5: Web Streaming (Range Request Support)

```
GET /api/audio/{role}/{date}
         │
         v
┌────────────────────────┐
│   AudioStreamer        │  ← FastAPI FileResponse
└────────────────────────┘
         │
         ├─> Check audio_briefs table for filepath
         │
         ├─> Verify file exists on disk
         │
         ├─> Handle HTTP Range header (for seek functionality)
         │   Range: bytes=0-1023 → partial content (206)
         │   No Range header → full file (200)
         │
         └─> Return FileResponse with media_type="audio/mpeg"
```

**Range Request Flow:**
1. Client requests audio: `GET /api/audio/brokers/2026-02-27`
2. AudioStreamer queries database for filepath
3. Check filesystem: `data/audio/brokers/2026-02-27.mp3` exists
4. Read Range header (if present)
5. Return FileResponse with appropriate status:
   - 200 OK: Full file (no Range header)
   - 206 Partial Content: Byte range (with Range header)
   - 404 Not Found: File missing or invalid role/date

---

## Integration Points with Existing Pipeline

| Existing Component | Integration | Changes Needed |
|-------------------|-------------|----------------|
| **PipelineOrchestrator.run_full_pipeline_with_email()** | Add Step 5c: Audio generation after Step 5b (HTML archiving) | Insert audio generation call between Steps 5b and 8. Error handling: audio failure NEVER blocks email delivery. |
| **RoleReportService** | Provide article data to script writer | Add method `get_articles_for_audio(role, articles, executive_summary)` to prepare audio context. |
| **EnterpriseEmailClient.send_email()** | Add audio file attachment support | Add `attachments` parameter (List of file paths). Build MIME multipart message with audio/mpeg Content-Type. |
| **GraphEmailService.send_email()** | Add audio file attachment support (Graph API fallback) | Convert file to base64, attach via Graph API attachment schema. |
| **Admin Dashboard (admin.py router)** | Add audio archive browser route | New route `/admin/audio` listing audio briefs by role/date. Include web player component. |
| **Email HTML Template** | Add audio player and streaming link | Embed HTML5 audio player: `<audio controls src="/api/audio/{role}/{date}">`. Fallback: download link. |
| **Health Check Endpoint** | Add audio storage directory check | Verify `data/audio/` is writable. Check latest audio file age (<36 hours). |
| **Run Model** | Add audio generation status tracking | Add column: `audio_generated BOOLEAN DEFAULT 0`. Update after successful Step 5c completion. |

---

## New Components Detailed Design

### 1. ScriptWriterService (app/services/audio/script_writer.py)

**Purpose:** Generate podcast-style narration scripts from classified articles using GPT-4o.

**Class Signature:**
```python
class ScriptWriterService:
    def __init__(self, azure_openai_client, deployment: str):
        """Initialize with Azure OpenAI client (same pattern as RoleClassificationService)."""

    def generate_script(
        self,
        role: str,
        articles: List[dict],
        executive_summary: dict,
        report_date: datetime,
        company_name: str
    ) -> str:
        """
        Generate podcast script for a specific role.

        Returns:
            Script text (500-800 words) ready for TTS conversion.

        Raises:
            OpenAIError: On API failure (caller handles gracefully).
        """
```

**GPT-4o Prompt Template:**
```
You are a professional podcast narrator creating a 2-3 minute audio intelligence brief
for {role} professionals in the insurance industry.

Context:
- Company: {company_name}
- Role: {role}
- Date: {date}
- Executive Summary: {summary_paragraphs}

Top Articles (priority-sorted):
{article_list}

Generate a natural, conversational narration script (500-800 words):
1. Branded intro: "Good morning, this is the {role} Brief for {date}."
2. Executive overview (2-3 key themes from summary)
3. Top 3-5 priority stories with brief context
4. Closing with actionable takeaway
5. Sign-off: "That's your {role} Brief. Full details in your email."

Style:
- Conversational but professional
- Natural pacing for audio (avoid lists, use flowing prose)
- No formatting markup (plain text for TTS)
- 2-3 minute target length
```

**Error Handling:**
- API failure → Return fallback script: "Audio brief generation unavailable. Please refer to your email for full details."
- Empty articles → Skip audio generation (log warning, no error)

---

### 2. TTSClient (app/services/audio/tts_client.py)

**Purpose:** Convert text scripts to MP3 audio using Azure OpenAI TTS API.

**Class Signature:**
```python
class TTSClient:
    def __init__(self):
        """Initialize Azure OpenAI TTS client from settings."""

    def generate_audio(self, script: str) -> bytes:
        """
        Convert script text to MP3 audio bytes.

        Args:
            script: Text script (500-800 words)

        Returns:
            MP3 audio bytes (2-4 MB)

        Raises:
            OpenAIError: On TTS API failure
        """
```

**Azure OpenAI TTS API Call:**
```python
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version="2024-08-01-preview"  # TTS support version
)

response = client.audio.speech.create(
    model="tts-1-hd",
    voice="alloy",
    input=script,
    response_format="mp3",
    speed=1.0
)

audio_bytes = response.content  # Raw MP3 bytes
```

**Retry Strategy (Tenacity):**
- Retry on: `APIError`, `APIConnectionError`, `RateLimitError`
- Stop after: 2 attempts
- Wait: Random exponential backoff (2-10 seconds)

**Error Handling:**
- TTS failure → Log error, skip audio for this role, continue pipeline
- Audio generation NEVER blocks email delivery

---

### 3. AudioStorageManager (app/services/audio/storage_manager.py)

**Purpose:** Write MP3 files to filesystem and record metadata in database.

**Class Signature:**
```python
class AudioStorageManager:
    def __init__(self, base_path: str = "data/audio"):
        """Initialize with base audio storage directory."""

    def store_audio(
        self,
        role: str,
        report_date: datetime,
        audio_bytes: bytes,
        script_text: str,
        run_id: int
    ) -> AudioBrief:
        """
        Store audio file and record metadata.

        Returns:
            AudioBrief ORM object with filepath, file_size, etc.

        Raises:
            IOError: On filesystem write failure
        """
```

**Storage Implementation:**
```python
def store_audio(...) -> AudioBrief:
    # Build filepath
    role_dir = os.path.join(self.base_path, role.lower())
    os.makedirs(role_dir, exist_ok=True)

    date_str = report_date.strftime("%Y-%m-%d")
    filepath = os.path.join(role_dir, f"{date_str}.mp3")

    # Write audio bytes to file
    with open(filepath, "wb") as f:
        f.write(audio_bytes)

    # Calculate duration (estimate: 150 words/minute)
    word_count = len(script_text.split())
    duration_seconds = int((word_count / 150) * 60)

    # Record in database
    audio_brief = AudioBrief(
        run_id=run_id,
        role=role,
        report_date=report_date,
        filepath=filepath,
        file_size=len(audio_bytes),
        duration_seconds=duration_seconds,
        script_text=script_text
    )
    db.add(audio_brief)
    db.commit()

    return audio_brief
```

**Filesystem Permissions:**
- Directory: 755 (read/execute for all, write for owner)
- Files: 644 (read for all, write for owner)
- Owner: Application service account

---

### 4. AudioBrief Model (app/models/audio_brief.py)

**Purpose:** SQLAlchemy ORM model for audio file metadata.

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from app.database import Base

class AudioBrief(Base):
    """
    Audio briefing metadata and file location.

    Each AudioBrief represents one role's audio narration for a specific date.
    The actual MP3 file is stored on filesystem (filepath column).
    """
    __tablename__ = "audio_briefs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=True)

    role = Column(String(50), nullable=False)  # Brokers, Leadership, etc.
    report_date = Column(Date, nullable=False)

    # File storage
    filepath = Column(String(500), nullable=False)  # Absolute path to MP3
    file_size = Column(Integer, nullable=False)     # Bytes
    duration_seconds = Column(Integer, nullable=True)  # Estimated duration

    # Script preservation (for regeneration/debugging)
    script_text = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("Run", back_populates="audio_briefs")

    def __repr__(self) -> str:
        return f"<AudioBrief(role={self.role}, date={self.report_date})>"
```

**Unique Constraint:**
- One audio brief per role per date: `UNIQUE(role, report_date)`
- Regeneration overwrites existing record (or delete-then-insert pattern)

---

### 5. AudioStreamer Router (app/routers/audio.py)

**Purpose:** FastAPI router for audio streaming endpoints.

```python
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.audio_brief import AudioBrief
import os

router = APIRouter(prefix="/api/audio", tags=["Audio"])

@router.get("/{role}/{date}")
async def stream_audio(
    role: str,
    date: str,  # Format: YYYY-MM-DD
    request: Request
):
    """
    Stream audio brief with HTTP range request support.

    Supports:
    - Full file download (no Range header)
    - Partial content streaming (Range header present)
    - Web player seek/scrubbing functionality

    Returns:
        FileResponse with media_type="audio/mpeg"

    Status Codes:
        200 OK: Full file
        206 Partial Content: Byte range (if Range header present)
        404 Not Found: Invalid role/date or file missing
    """
    db = SessionLocal()
    try:
        # Query database for audio brief
        audio_brief = db.query(AudioBrief).filter(
            AudioBrief.role == role.capitalize(),
            AudioBrief.report_date == date
        ).first()

        if not audio_brief:
            raise HTTPException(status_code=404, detail="Audio brief not found")

        # Verify file exists on disk
        if not os.path.exists(audio_brief.filepath):
            raise HTTPException(status_code=404, detail="Audio file missing from storage")

        # Return FileResponse (handles Range requests automatically via Starlette)
        return FileResponse(
            path=audio_brief.filepath,
            media_type="audio/mpeg",
            filename=f"{role}_{date}.mp3"
        )
    finally:
        db.close()
```

**Range Request Handling:**
- **Automatic:** Starlette's FileResponse handles HTTP Range headers automatically
- **Client sends:** `Range: bytes=0-1023` → Server responds with 206 Partial Content
- **No Range header:** Full file delivered with 200 OK
- **Benefits:** Web player seek functionality, resumable downloads

---

### 6. AudioGenerationService (app/services/audio/generator.py)

**Purpose:** Orchestrate complete audio generation workflow (script → TTS → storage).

```python
class AudioGenerationService:
    def __init__(
        self,
        script_writer: ScriptWriterService,
        tts_client: TTSClient,
        storage_manager: AudioStorageManager
    ):
        """Initialize with service dependencies."""

    async def generate_role_audio(
        self,
        role: str,
        articles: List[dict],
        executive_summary: dict,
        report_date: datetime,
        run_id: int
    ) -> Optional[AudioBrief]:
        """
        Generate audio brief for one role.

        Returns:
            AudioBrief on success, None on failure (never raises)
        """
        try:
            # Step 1: Generate script
            script = self.script_writer.generate_script(...)

            # Step 2: Convert to audio
            audio_bytes = self.tts_client.generate_audio(script)

            # Step 3: Store file + metadata
            audio_brief = self.storage_manager.store_audio(...)

            return audio_brief

        except Exception as e:
            # Log error, return None (audio failure never blocks pipeline)
            logger.error("audio_generation_failed", role=role, error=str(e))
            return None

    async def generate_all_role_audios(
        self,
        classified_articles: List[NewsArticle],
        report_date: datetime,
        run_id: int,
        executive_summaries: Dict[str, dict]
    ) -> Dict[str, Optional[AudioBrief]]:
        """
        Generate audio briefs for all 4 roles in parallel.

        Returns:
            Dict mapping role -> AudioBrief (or None on failure)
        """
        # Use asyncio.gather for parallel generation
        tasks = [
            self.generate_role_audio(role, ...)
            for role in ["Brokers", "Leadership", "Compliance", "Underwriting"]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results to roles
        return dict(zip(roles, results))
```

---

## Suggested Build Order

**Rationale:** Build from data layer up, test each component independently before integration.

### Phase 1: Data Layer (Week 1)

**Goal:** Establish storage foundation before audio generation.

1. **AudioBrief Model** (`app/models/audio_brief.py`)
   - **Why first:** Database schema must exist before any storage operations
   - **Testing:** Create migration, verify table creation
   - **Dependencies:** None (uses existing SQLAlchemy patterns)

2. **AudioStorageManager** (`app/services/audio/storage_manager.py`)
   - **Why next:** Storage can be tested with mock audio bytes
   - **Testing:** Write dummy MP3, verify filesystem + DB record creation
   - **Dependencies:** AudioBrief model

3. **Database Migration**
   - **Action:** Add audio_briefs table via Alembic or raw SQL
   - **Testing:** Run migration on dev database, verify schema

### Phase 2: Audio Generation (Week 2)

**Goal:** Generate audio files independent of pipeline integration.

4. **TTSClient** (`app/services/audio/tts_client.py`)
   - **Why before script writer:** Can test with hardcoded scripts
   - **Testing:** Call Azure OpenAI TTS with sample text, verify MP3 output
   - **Dependencies:** Azure OpenAI credentials (already configured)

5. **ScriptWriterService** (`app/services/audio/script_writer.py`)
   - **Why next:** Depends on existing article classification data
   - **Testing:** Generate script from sample articles, verify output format
   - **Dependencies:** Azure OpenAI client (same as classifier)

6. **AudioGenerationService** (`app/services/audio/generator.py`)
   - **Why last in phase:** Orchestrates all previous components
   - **Testing:** End-to-end test (articles → script → audio → storage)
   - **Dependencies:** ScriptWriter, TTSClient, StorageManager

### Phase 3: Delivery (Week 3)

**Goal:** Make audio accessible via streaming and email.

7. **AudioStreamer Router** (`app/routers/audio.py`)
   - **Why first in delivery:** Independent of pipeline, testable immediately
   - **Testing:** Upload sample MP3, verify streaming endpoint works
   - **Dependencies:** AudioBrief model (for queries)

8. **Email Template Updates** (`app/templates/email/role_email.html`)
   - **Why next:** Visual testing before attachment implementation
   - **Testing:** Render email with audio player HTML, verify layout
   - **Dependencies:** Streaming endpoint (for links)

9. **Email Attachment Support** (`app/services/enterprise_emailer.py`)
   - **Why before pipeline:** Can test attachment separately
   - **Testing:** Send test email with MP3 attachment
   - **Dependencies:** AudioBrief model (to query filepaths)

### Phase 4: Pipeline Integration (Week 4)

**Goal:** Integrate audio generation into production pipeline.

10. **Pipeline Integration** (`app/services/pipeline.py`)
    - **Why last:** Requires all previous components working
    - **Testing:** Run full pipeline, verify audio + HTML + email delivery
    - **Implementation:** Add Step 5c between Steps 5b and 8
    - **Error handling:** Audio failure logs warning, continues to email

11. **Admin Dashboard** (`app/routers/admin.py`, `app/templates/admin/audio.html`)
    - **Why after pipeline:** Requires real audio files to browse
    - **Testing:** Browse audio archive, play sample files
    - **Dependencies:** AudioStreamer, AudioBrief model

### Phase 5: Production Readiness (Week 5)

**Goal:** Monitoring, error handling, performance optimization.

12. **Health Check Updates** (`app/main.py`)
    - **Action:** Add audio storage directory check
    - **Testing:** Verify health endpoint reports audio status

13. **Error Monitoring**
    - **Action:** Add ApiEvent logging for audio generation (AUDIO_GENERATED, AUDIO_FAILED)
    - **Testing:** Trigger failures, verify event recording

14. **Performance Testing**
    - **Action:** Generate audio for all 4 roles, measure time
    - **Target:** <30 seconds for parallel generation (4 roles @ 2-5 min each)

---

## Decision Rationale

### Why Filesystem Storage Instead of SQLite BLOBs?

**Decision:** Store audio files in `data/audio/` directory structure, NOT in SQLite BLOBs.

**Evidence:**
1. **Performance:** [SQLite is 35% faster for BLOBs <250KB](https://sqlite.org/fasterthanfs.html), but audio files are 2-4 MB (exceeds efficient BLOB range)
2. **Streaming:** FileResponse streams from disk efficiently; BLOB streaming requires custom chunking
3. **Backup:** Filesystem allows incremental audio backups without full database dump
4. **Range Requests:** FileResponse handles HTTP Range headers automatically; BLOB serving requires manual implementation
5. **Operational Simplicity:** Audio files can be inspected, deleted, or moved independently

**Tradeoff:** Lose transactional integrity (audio file could exist without DB record), mitigated by storing filepath in database for reference integrity.

### Why Dual Delivery (Attachment + Streaming)?

**Decision:** Attach MP3 to email AND include streaming link.

**Evidence:**
1. **Email Limits:** [Enterprise Outlook typically allows 10-35 MB attachments](https://learn.microsoft.com/en-us/office365/servicedescriptions/exchange-online-service-description/exchange-online-limits); 2-4 MB audio is safe
2. **Offline Access:** Users can play audio without internet (flights, commutes)
3. **Fallback:** Streaming link provides access if attachment is stripped by email gateway
4. **Web Player:** Streaming enables seek/scrubbing functionality (not available in email attachment players)

**Tradeoff:** Email size increases, but 2-4 MB is within acceptable limits for daily briefings.

### Why Parallel Audio Generation?

**Decision:** Generate audio for all 4 roles in parallel using `asyncio.gather()`.

**Evidence:**
1. **Performance:** Sequential generation = 4 × 10 seconds = 40 seconds; parallel = ~10 seconds (limited by slowest role)
2. **Azure OpenAI TTS:** API is async-capable, benefits from concurrent calls
3. **Pipeline Impact:** Minimizes delay between report generation and email delivery

**Tradeoff:** Higher memory usage during generation, acceptable for 4 concurrent MP3 generations.

### Why Azure OpenAI TTS Instead of Alternatives?

**Decision:** Use Azure OpenAI TTS (tts-1-hd model) for audio generation.

**Evidence:**
1. **Existing Integration:** Project already uses Azure OpenAI for classification, same credentials
2. **Quality:** [TTS-1-HD offers high-quality audio with consistent quality](https://platform.openai.com/docs/guides/text-to-speech)
3. **Voice Options:** Professional voices (alloy, echo, fable) suitable for business intelligence
4. **Simplicity:** Single API call returns MP3 bytes, no additional processing needed

**Alternatives Considered:**
- **Azure Speech Services:** More complex authentication, separate service
- **AWS Polly:** Requires separate AWS account, additional infrastructure
- **Google TTS:** Requires separate GCP account

---

## Email Attachment Implementation

### MIME Multipart Structure

```python
# In EnterpriseEmailClient.send_email()

def _build_payload_with_attachment(
    self,
    to_addresses: List[str],
    subject: str,
    html_body: str,
    cc_addresses: Optional[List[str]],
    audio_filepath: Optional[str]  # NEW parameter
) -> Dict[str, Any]:
    """
    Build email payload with optional audio attachment.

    Args:
        audio_filepath: Absolute path to MP3 file (or None for no attachment)
    """
    payload = {
        self.FIELD_SUBJECT: subject,
        self.FIELD_HTML_BODY: html_body,
        self.FIELD_TO_RECIPIENTS: to_addresses,
        self.FIELD_SENDER: self.sender_email,
    }

    if cc_addresses:
        payload[self.FIELD_CC_RECIPIENTS] = cc_addresses

    # Add audio attachment if provided
    if audio_filepath and os.path.exists(audio_filepath):
        with open(audio_filepath, "rb") as f:
            audio_bytes = f.read()

        # Base64 encode for email transmission
        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        filename = os.path.basename(audio_filepath)

        payload[self.FIELD_ATTACHMENTS] = [{
            "filename": filename,
            "contentType": "audio/mpeg",
            "contentBytes": audio_b64
        }]

    return payload
```

**Attachment Size Validation:**
```python
# Before attaching, validate size
max_attachment_size = 10 * 1024 * 1024  # 10 MB (conservative enterprise limit)

if os.path.getsize(audio_filepath) > max_attachment_size:
    logger.warning(
        "audio_attachment_too_large",
        filepath=audio_filepath,
        size_mb=os.path.getsize(audio_filepath) / (1024 * 1024)
    )
    # Skip attachment, include only streaming link
    return payload_without_attachment
```

---

## Admin Dashboard Audio Player

### Audio Archive Browser Template

```html
<!-- app/templates/admin/audio.html -->

{% extends "admin/base.html" %}

{% block content %}
<div class="container mt-4">
    <h2>Audio Brief Archive</h2>

    <!-- Role Filter Tabs -->
    <ul class="nav nav-tabs mb-4">
        <li class="nav-item">
            <a class="nav-link active" href="#brokers" data-bs-toggle="tab">Brokers</a>
        </li>
        <li class="nav-item">
            <a class="nav-link" href="#leadership" data-bs-toggle="tab">Leadership</a>
        </li>
        <li class="nav-item">
            <a class="nav-link" href="#compliance" data-bs-toggle="tab">Compliance</a>
        </li>
        <li class="nav-item">
            <a class="nav-link" href="#underwriting" data-bs-toggle="tab">Underwriting</a>
        </li>
    </ul>

    <!-- Audio List by Role -->
    <div class="tab-content">
        {% for role in ["Brokers", "Leadership", "Compliance", "Underwriting"] %}
        <div class="tab-pane fade {% if role == 'Brokers' %}show active{% endif %}" id="{{ role.lower() }}">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Duration</th>
                        <th>Size</th>
                        <th>Player</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for audio in audio_briefs[role] %}
                    <tr>
                        <td>{{ audio.report_date.strftime('%Y-%m-%d') }}</td>
                        <td>{{ audio.duration_seconds // 60 }}:{{ (audio.duration_seconds % 60):02d }}</td>
                        <td>{{ (audio.file_size / (1024 * 1024))|round(1) }} MB</td>
                        <td>
                            <audio controls preload="none" style="width: 300px;">
                                <source src="/api/audio/{{ role }}/{{ audio.report_date.strftime('%Y-%m-%d') }}" type="audio/mpeg">
                                Your browser does not support audio playback.
                            </audio>
                        </td>
                        <td>
                            <a href="/api/audio/{{ role }}/{{ audio.report_date.strftime('%Y-%m-%d') }}" download class="btn btn-sm btn-primary">
                                Download
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

---

## Configuration Updates

### Settings (app/config.py)

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Audio generation settings (NEW)
    audio_enabled: bool = True  # Feature flag for audio generation
    audio_voice: str = "alloy"  # Azure OpenAI TTS voice
    audio_speed: float = 1.0    # Narration speed (0.5-2.0)
    audio_base_path: str = "data/audio"  # Filesystem storage base

    def is_audio_configured(self) -> bool:
        """Check if audio generation is configured."""
        return bool(
            self.audio_enabled
            and self.is_azure_openai_configured()  # Same Azure OpenAI for TTS
        )
```

---

## Error Handling Strategy

### Audio Generation Failure Modes

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Script generation fails (GPT-4o error) | No audio for this role | Log error, continue with remaining roles. Email delivery proceeds without attachment. |
| TTS conversion fails (Azure OpenAI TTS error) | No audio for this role | Log error, retry once with exponential backoff. If still fails, skip audio. |
| Storage write fails (disk full, permissions) | Audio lost for this run | Log error, alert admin. Check disk space in health check. |
| All roles fail | No audio in email | Log critical error, send admin alert. Email delivery continues with HTML only. |
| Streaming endpoint unavailable | Users can't stream | Email attachment still works. Admin dashboard shows error message. |

### Graceful Degradation

```python
# In PipelineOrchestrator.run_full_pipeline_with_email()

try:
    # Step 5c: Audio generation
    logger.info("step_5c_audio_generation_started")

    audio_service = AudioGenerationService(...)
    audio_results = await audio_service.generate_all_role_audios(
        classified_articles=classified_articles,
        report_date=report_date,
        run_id=run.id,
        executive_summaries=executive_summaries_dict
    )

    # Count successes
    audio_success_count = len([r for r in audio_results.values() if r is not None])

    logger.info(
        "step_5c_audio_generation_completed",
        successes=audio_success_count,
        failures=4 - audio_success_count
    )

    result["audio_generated"] = audio_success_count

except Exception as e:
    # Audio generation failure NEVER blocks email delivery
    logger.error(
        "step_5c_audio_generation_failed",
        error=str(e),
        exc_info=True
    )
    result["audio_generated"] = 0
    audio_results = {}

# Email delivery continues regardless of audio status
# ...
```

---

## Performance Considerations

### Parallel Audio Generation

**Expected Performance:**
- Script generation (GPT-4o): ~3-5 seconds per role
- TTS conversion (Azure OpenAI): ~5-8 seconds per role
- Storage write: <1 second per role
- **Total (parallel):** ~10 seconds for all 4 roles

**Optimization:**
```python
# Use asyncio.gather() for parallel execution
async def generate_all_role_audios(...):
    tasks = [
        generate_role_audio("Brokers", ...),
        generate_role_audio("Leadership", ...),
        generate_role_audio("Compliance", ...),
        generate_role_audio("Underwriting", ...)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return dict(zip(["Brokers", "Leadership", "Compliance", "Underwriting"], results))
```

### Streaming Optimization

**FileResponse Buffering:**
- Starlette's FileResponse uses chunked streaming (8KB chunks by default)
- No need to load entire MP3 into memory
- Range requests allow efficient seeking without full download

**Caching Strategy:**
- Set `Cache-Control: public, max-age=86400` (24 hours) for audio files
- Audio files are immutable (keyed by role + date)
- Reduces server load for repeated listens

---

## Sources

### Azure OpenAI TTS
- [Text to speech with Azure OpenAI - Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/openai/text-to-speech-quickstart)
- [Azure OpenAI speech to speech chat - Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/openai-speech)
- [What are OpenAI text to speech voices? - Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/openai-voices)
- [Text to speech | OpenAI API](https://platform.openai.com/docs/guides/text-to-speech)

### FastAPI Audio Streaming
- [Receiving and returning audio & video files using FileResponse - FastAPI GitHub](https://github.com/fastapi/fastapi/discussions/6284)
- [Custom Response - HTML, Stream, File, others - FastAPI](https://fastapi.tiangolo.com/advanced/custom-response/)
- [Streaming Responses in FastAPI – Random Thoughts](https://hassaanbinaslam.github.io/posts/2025-01-19-streaming-responses-fastapi.html)

### Email Attachment Limits
- [Increase Outlook Attachment Size Limit: Easy Fixes for 2026](https://smartreach.io/blog/outlook-attachment-size-limit/)
- [Exchange Online limits - Microsoft Learn](https://learn.microsoft.com/en-us/office365/servicedescriptions/exchange-online-service-description/exchange-online-limits)
- [Outlook email attachment size limit and how to increase it](https://www.ablebits.com/office-addins-blog/outlook-attachment-size-limit-increase/)

### SQLite BLOB vs Filesystem Storage
- [SQLite is 35% Faster than Filesystem with Small BLOBs](https://levysoft.medium.com/sqlite-is-35-faster-than-filesystem-with-small-blobs-2974c095d324)
- [35% Faster Than The Filesystem - SQLite](https://sqlite.org/fasterthanfs.html)
- [Internal Versus External BLOBs - SQLite](https://sqlite.org/intern-v-extern-blob.html)

---

*Architecture research for: Audio intelligence briefings integration*
*Researched: 2026-02-27*
*Confidence: HIGH*
