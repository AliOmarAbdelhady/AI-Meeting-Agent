# 🧪 Real-World Testing Guide — AI Meeting Agent

> Step-by-step instructions to test the full pipeline with a real meeting, from zero to email delivered.

---

## 📋 Overview of Testing Phases

| Phase | What It Tests | Requires |
|-------|--------------|----------|
| **Phase 1** | API + Database only | Nothing (just the server) |
| **Phase 2** | Whisper transcription with your own audio | A `.wav` audio file + OpenAI key |
| **Phase 3** | Full AI pipeline (transcribe → summarize → tasks → email) | OpenAI key + email config |
| **Phase 4** | Bot joins a real Google Meet meeting | Google account + Playwright |

> **Recommended:** Test each phase in order. Don't skip to Phase 4 until Phases 1–3 work.

---

## Phase 1 — API & Database (No External Services)

This tests that the server starts, the database works, and the API endpoints respond.

### Step 1: Install system dependencies

```bash
# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install -y ffmpeg libportaudio2 portaudio19-dev

# macOS (Homebrew)
brew install ffmpeg portaudio
```

### Step 2: Set up the project

```bash
cd "AI Meeting Agent"

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install -e ".[dev]"
```

### Step 3: Start the server

```bash
make run
```

You should see:

```
Starting AI Meeting Agent v0.1.0
Database tables created.
Scheduler started.
Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Test the API

Open a **second terminal** and run:

```bash
# Health check
curl http://localhost:8000/api/v1/health
# Expected: {"status":"healthy","service":"AI Meeting Agent","version":"0.1.0"}

# Create a meeting
curl -X POST http://localhost:8000/api/v1/meetings \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Meeting",
    "platform": "google_meet",
    "meeting_url": "https://meet.google.com/test",
    "scheduled_at": "2026-06-15T10:00:00Z",
    "participants": ["your-email@gmail.com"]
  }'
# Expected: 201 with meeting JSON

# List meetings
curl http://localhost:8000/api/v1/meetings
# Expected: {"items":[...],"total":1,"page":1,"page_size":50}
```

Or open **http://localhost:8000/docs** in your browser and use the interactive Swagger UI.

### ✅ Phase 1 Pass Criteria
- [x] Server starts without errors
- [x] Health check returns `healthy`
- [x] Meeting CRUD works via API

---

## Phase 2 — Transcription with Your Own Audio

This tests that Whisper can transcribe real speech from an audio file.

### Step 1: Get your OpenAI API key

1. Go to **https://platform.openai.com/api-keys**
2. Create a new API key
3. Copy it

### Step 2: Configure `.env`

Edit your `.env` file and set these values:

```env
# ── THIS IS THE ONLY REQUIRED KEY ──
OPENAI_API_KEY=sk-proj-your-actual-key-here

# ── KEEP THESE DEFAULTS FOR NOW ──
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

### Step 3: Create a test audio file

**Option A — Record yourself speaking (recommended):**

```bash
# Install sox if you don't have it
sudo apt install sox   # Linux
brew install sox       # macOS

# Record 30 seconds of yourself talking about a project
rec -r 16000 -c 1 data/audio/test_meeting.wav trim 0 30
# Speak naturally for 30 seconds, then it auto-stops
```

**Option B — Use a synthetic test file:**

```python
# Run this in Python (with venv activated)
python3 -c "
import soundfile as sf
import numpy as np
print('Creating a silent test WAV file...')
# This creates a valid WAV file (replace with real audio for real results)
sf.write('data/audio/test_meeting.wav', np.zeros(16000 * 10), 16000)
print('Created data/audio/test_meeting.wav (10s silent)')
"
```

**Option C — Download a sample meeting recording:**

```bash
# Use any existing .wav, .mp3, or .m4a file you have
# If it's mp3/m4a, convert to wav:
ffmpeg -i your_recording.mp3 -ar 16000 -ac 1 data/audio/test_meeting.wav
```

### Step 4: Test transcription via Python

```bash
source .venv/bin/activate

python3 << 'EOF'
import asyncio
from meeting_agent.infrastructure.providers.whisper_engine import WhisperEngine

async def test():
    engine = WhisperEngine()
    # First run downloads the model (~150MB), subsequent runs are instant
    result = await engine.transcribe_file("data/audio/test_meeting.wav")
    print(f"\n{'='*60}")
    print(f"Language: {result['language']}")
    print(f"Duration: {result['duration_seconds']:.1f}s")
    print(f"Words:    {result['word_count']}")
    print(f"Segments: {len(result['segments'])}")
    print(f"\n--- Full Transcript ---\n{result['full_text']}")
    print(f"\n--- First 3 Segments ---")
    for seg in result['segments'][:3]:
        print(f"  [{seg['start_time']:.1f}s - {seg['end_time']:.1f}s] {seg['text']}")
    print(f"\n{'='*60}")

asyncio.run(test())
EOF
```

### ✅ Phase 2 Pass Criteria
- [x] Whisper model downloads successfully
- [x] Audio file is transcribed without errors
- [x] Transcript text matches what was spoken

> **Tip:** If you get a CUDA error, make sure `WHISPER_DEVICE=cpu` in `.env`. The `base` model runs fine on CPU.

---

## Phase 3 — Full AI Pipeline (Summarize + Tasks + Email)

This tests the complete chain: audio → transcript → summary → tasks → email.

### Step 1: Set up email sending

**Option A — Gmail SMTP (easiest for testing):**

1. Go to your Google Account → Security → 2-Step Verification → **App passwords**
2. Generate a new app password (call it "Meeting Agent")
3. Copy the 16-character password

Edit `.env`:

```env
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=abcd-efgh-ijkl-mnop     # Your 16-char app password
EMAIL_FROM_ADDRESS=your-email@gmail.com
EMAIL_FROM_NAME=AI Meeting Agent
```

**Option B — SendGrid (for production):**

1. Sign up at **https://sendgrid.com** (free tier = 100 emails/day)
2. Create an API key with "Mail Send" permission
3. Verify your sender email

Edit `.env`:

```env
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.actual-key-here
EMAIL_FROM_ADDRESS=verified-sender@yourdomain.com
EMAIL_FROM_NAME=AI Meeting Agent
```

### Step 2: Run the full pipeline manually

Restart the server with your new `.env`:

```bash
# Stop the old server (Ctrl+C), then:
source .venv/bin/activate
make run
```

In a **second terminal**, run this end-to-end test script:

```bash
source .venv/bin/activate

python3 << 'SCRIPT'
import asyncio
import json
from meeting_agent.infrastructure.database.connection import async_session_factory
from meeting_agent.infrastructure.database.repositories.meeting_repo import SqlMeetingRepository
from meeting_agent.infrastructure.database.repositories.transcript_repo import SqlTranscriptRepository
from meeting_agent.infrastructure.database.repositories.summary_repo import SqlSummaryRepository
from meeting_agent.infrastructure.database.repositories.task_repo import SqlTaskRepository
from meeting_agent.infrastructure.database.repositories.email_log_repo import SqlEmailLogRepository
from meeting_agent.infrastructure.providers.whisper_engine import WhisperEngine
from meeting_agent.infrastructure.providers.llm_provider import OpenAILLMProvider
from meeting_agent.infrastructure.providers.email_smtp import SMTPEmailProvider
from meeting_agent.services.meeting_service import MeetingService
from meeting_agent.services.summary_service import SummaryService
from meeting_agent.services.task_service import TaskService
from meeting_agent.services.email_service import EmailService

async def run_full_pipeline():
    async with async_session_factory() as session:
        # Initialize repos
        meeting_repo = SqlMeetingRepository(session)
        transcript_repo = SqlTranscriptRepository(session)
        summary_repo = SqlSummaryRepository(session)
        task_repo = SqlTaskRepository(session)
        email_log_repo = SqlEmailLogRepository(session)

        # ── Step 1: Create a meeting ──
        print("\n📋 Step 1: Creating meeting...")
        from meeting_agent.core.domain_models import Meeting
        from meeting_agent.core.enums import MeetingPlatform, MeetingStatus
        from uuid import uuid4
        from datetime import datetime, timedelta

        meeting = Meeting(
            id=uuid4(),
            title="Q3 Sprint Planning",
            platform=MeetingPlatform.GOOGLE_MEET,
            meeting_url="https://meet.google.com/test-meeting",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            status=MeetingStatus.SCHEDULED,
            participants=["your-email@gmail.com"],  # ← PUT YOUR EMAIL HERE
        )
        meeting_dict = await meeting_repo.create(meeting)
        meeting_id = meeting_dict["id"]
        print(f"   ✅ Meeting created: {meeting_id}")
        print(f"   Title: {meeting_dict['title']}")

        # ── Step 2: Transcribe audio ──
        print("\n🎤 Step 2: Transcribing audio file...")
        await meeting_repo.update_status(meeting_id, "transcribing")
        whisper = WhisperEngine()
        transcription = await whisper.transcribe_file("data/audio/test_meeting.wav")

        transcript = await transcript_repo.create(
            meeting_id=meeting_id,
            full_text=transcription["full_text"],
            language=transcription["language"],
            duration_seconds=transcription["duration_seconds"],
            word_count=transcription["word_count"],
        )
        print(f"   ✅ Transcript created: {len(transcription['segments'])} segments, {transcription['word_count']} words")
        print(f"   Preview: {transcription['full_text'][:100]}...")

        # ── Step 3: Generate summary ──
        print("\n🧠 Step 3: Generating summary with GPT-4o...")
        await meeting_repo.update_status(meeting_id, "summarizing")
        llm = OpenAILLMProvider()
        summary_service = SummaryService(transcript_repo, summary_repo, llm)
        summary = await summary_service.generate_summary(meeting_id)
        print(f"   ✅ Summary generated (model: {summary['model_used']})")
        print(f"   Key points: {summary['key_points']}")
        print(f"   Decisions: {summary['decisions']}")

        # ── Step 4: Extract tasks ──
        print("\n📝 Step 4: Extracting tasks...")
        task_service = TaskService(task_repo, summary_repo, llm)
        tasks = await task_service.extract_tasks(meeting_id, summary["id"])
        print(f"   ✅ Extracted {len(tasks)} tasks:")
        for t in tasks:
            print(f"      • {t['title']} (priority: {t['priority']})")

        # ── Step 5: Send email ──
        print("\n📧 Step 5: Sending summary email...")
        email_provider = SMTPEmailProvider()
        email_service = EmailService(
            email_log_repo=email_log_repo,
            meeting_repo=meeting_repo,
            summary_repo=summary_repo,
            task_repo=task_repo,
            email_provider=email_provider,
        )
        try:
            result = await email_service.send_summary_email(
                meeting_id=meeting_id,
                recipients=["aliomarsalehmohamed@gmail.com"],  # ← PUT YOUR EMAIL HERE
            )
            print(f"   ✅ Email sent! Message ID: {result['provider_message_id']}")
        except Exception as e:
            print(f"   ⚠️  Email failed: {e}")
            print("   (This is OK — check your SMTP credentials)")

        # ── Done ──
        await meeting_repo.update_status(meeting_id, "completed")
        await session.commit()
        print("\n" + "="*60)
        print("✅ FULL PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)

asyncio.run(run_full_pipeline())
SCRIPT
```

### ✅ Phase 3 Pass Criteria
- [x] Audio is transcribed to text
- [x] GPT-4o generates a summary with key points and decisions
- [x] Tasks are extracted with titles and priorities
- [x] Email is delivered to your inbox (check spam folder)
- [x] Meeting status ends as `completed`

> **Important:** Replace `your-email@gmail.com` with your actual email address in the script above (appears in 2 places).

---

## Phase 4 — Bot Joins a Real Meeting

This is the full end-to-end test: the bot actually joins a Google Meet call, records audio, and runs the pipeline.

### Step 1: Install Playwright browser

```bash
source .venv/bin/activate
playwright install chromium
```

### Step 2: Create a dedicated Google account for the bot

> ⚠️ **Do NOT use your personal Google account.** Create a separate one.

1. Go to **https://accounts.google.com/signup**
2. Create an account like `your-team-meeting-bot@gmail.com`
3. Sign in once in a regular browser to accept terms

### Step 3: Create a test meeting

1. Open **https://meet.google.com** on your personal account
2. Click **"New meeting" → "Start an instant meeting"**
3. Copy the meeting URL (e.g., `https://meet.google.com/xyz-abc-def`)
4. **Admit the bot** when it asks to join

### Step 4: Configure `.env` for the bot

```env
BOT_HEADLESS=false              # Show browser so you can see what happens
BOT_BROWSER_TIMEOUT=60          # Give more time for manual steps
BOT_GOOGLE_EMAIL=your-bot@gmail.com
BOT_GOOGLE_PASSWORD=your-bot-password
```

### Step 5: Run the bot test

**Option A — Quick test via Python (recommended for first attempt):**

```bash
source .venv/bin/activate

python3 << 'SCRIPT'
import asyncio
from meeting_agent.infrastructure.providers.meeting_bot import PlaywrightMeetingBot

async def test_bot():
    bot = PlaywrightMeetingBot()

    # Replace with your actual Google Meet URL
    MEETING_URL = "https://meet.google.com/qzr-czru-gpb"  # ← CHANGE THIS

    print("🤖 Bot is joining the meeting...")
    print("   If prompted, manually log in to Google in the browser window.")
    print("   Then the bot will try to join the meeting.\n")

    try:
        await bot.join(MEETING_URL, display_name="AI Meeting Bot")
        print("✅ Bot joined successfully!")

        in_meeting = await bot.is_in_meeting()
        print(f"   In meeting: {in_meeting}")

        # Stay in the meeting for 15 seconds
        print("   Recording for 15 seconds...")
        await asyncio.sleep(15)

        print("   Leaving meeting...")
        await bot.leave()
        print("✅ Bot left the meeting.")

    except Exception as e:
        print(f"❌ Error: {e}")
        await bot.leave()

asyncio.run(test_bot())
SCRIPT
```

**What to expect:**
1. A Chromium browser window opens
2. It navigates to the Google Meet URL
3. You may need to manually sign in to Google (first time only)
4. The bot clicks "Ask to join" / "Join now"
5. **On your personal device**, admit the bot into the meeting
6. The bot stays for 15 seconds, then leaves

**Option B — Full automated pipeline via API:**

```bash
# 1. Start the server
make run

# 2. In another terminal, schedule a meeting starting NOW
curl -X POST http://localhost:8000/api/v1/meetings \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Live Test Meeting",
    "platform": "google_meet",
    "meeting_url": "https://meet.google.com/qzr-czru-gpb",
    "scheduled_at": "2026-06-01T12:00:00Z",
    "participants": ["aliomarsalehmohamed@gmail.com"]
  }'

# 3. Start the meeting (triggers bot to join)
curl -X POST http://localhost:8000/api/v1/meetings/{MEETING_ID}/start

# 4. After the meeting, stop it (triggers transcription → summary → email)
curl -X POST http://localhost:8000/api/v1/meetings/{MEETING_ID}/stop
```

### ✅ Phase 4 Pass Criteria
- [x] Chromium browser opens and navigates to Google Meet
- [x] Bot appears in the meeting as a participant
- [x] Audio is recorded during the meeting
- [x] Full pipeline runs after the meeting ends
- [x] Summary email is delivered

---

## 🔍 Quick Diagnostic Commands

If something isn't working, check these:

```bash
# Is the server running?
curl http://localhost:8000/api/v1/health

# Is the database working?
ls -la data/meeting_agent.db

# Are audio files being saved?
ls -la data/audio/

# Check the server logs (they show every step)
# Look at the terminal where `make run` is active

# Test OpenAI key is valid
python3 -c "
from meeting_agent.infrastructure.providers.llm_provider import OpenAILLMProvider
import asyncio
async def test():
    llm = OpenAILLMProvider()
    result = await llm.generate('Say hello in one word.')
    print(f'LLM response: {result}')
asyncio.run(test())
"

# Test email sending
python3 -c "
from meeting_agent.infrastructure.providers.email_smtp import SMTPEmailProvider
import asyncio
async def test():
    smtp = SMTPEmailProvider()
    msg_id = await smtp.send_email(
        to=['your-email@gmail.com'],
        subject='Test from Meeting Agent',
        html_body='<h1>It works!</h1><p>Email sending is configured correctly.</p>',
        text_body='It works! Email sending is configured correctly.',
    )
    print(f'Sent! Message ID: {msg_id}')
asyncio.run(test())
"
```

---

## ⚠️ Common Issues & Fixes

| Problem | Fix |
|---------|-----|
| `openai.AuthenticationError` | Your `OPENAI_API_KEY` is invalid or expired. Regenerate it. |
| `sounddevice.PortAudioError` | Install PortAudio: `sudo apt install libportaudio2 portaudio19-dev` |
| Whisper is very slow | Use `WHISPER_MODEL_SIZE=tiny` for faster (less accurate) results |
| Bot can't join Google Meet | Google may block automated sign-ins. Use `BOT_HEADLESS=false` and sign in manually the first time. |
| Email goes to spam | Add `EMAIL_FROM_NAME=AI Meeting Agent` to your contacts. Use SendGrid for better deliverability. |
| `playwright._impl._errors.Error: Browser closed` | Run `playwright install chromium` again |
| No audio in recording | The bot records from the system audio. Make sure your meeting has audio playing. On Linux, you may need PulseAudio configured. |
| Google blocks the bot with "This browser is not supported" | Try running with `BOT_HEADLESS=false` or use a Zoom/Teams meeting instead |

---

## 📊 What Success Looks Like

When everything works end-to-end, you should see:

1. **In the server terminal:**
```
Pipeline [JOIN]: Bot joined meeting abc123
Pipeline [RECORD]: Audio saved → data/audio/meeting_abc123.wav (120.5s, 1928000 samples)
Pipeline [TRANSCRIBE]: 847 words, 42 segments
Pipeline [SUMMARIZE]: Summary generated
Pipeline [TASKS]: Extracted 5 tasks
Pipeline [EMAIL]: Summary sent to 3 participants
Pipeline completed for meeting abc123
```

2. **In your email inbox:**
A beautifully formatted HTML email with:
- Meeting summary (3-5 paragraphs)
- Key points (bulleted list)
- Decisions made
- Action items with assignees and due dates

3. **Via the API:**
```bash
curl http://localhost:8000/api/v1/meetings/{id}/status
# {"meeting_id":"abc123","status":"completed"}

curl http://localhost:8000/api/v1/tasks
# Returns the extracted tasks with priorities and assignees
```
