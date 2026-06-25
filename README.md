# 🤖 AI Meeting Agent

> An AI-powered agent that automatically joins meetings, records audio, transcribes speech, generates summaries, extracts action items, and emails participants — end to end.

```
Meeting → Record → Transcript → Summary → Tasks → Email
```

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Web GUI](#-web-gui)
- [Testing](#-testing)
- [Docker Deployment](#-docker-deployment)
- [Automation Flow](#-automation-flow)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Auto-Join Meetings** | Playwright-based bot joins Google Meet, Zoom, and Teams |
| **Audio Recording** | Captures high-quality audio via `sounddevice` |
| **Speech-to-Text** | Transcribes using `faster-whisper` (OpenAI Whisper) |
| **AI Summarization** | Generates summaries, key points, and decisions via GPT-4o |
| **Task Extraction** | Extracts action items with assignees, priorities, and due dates |
| **Email Notifications** | Sends beautifully formatted summary emails (SendGrid / SMTP) |
| **REST API** | Full CRUD API with FastAPI + interactive Swagger docs |
| **Web GUI** | Built-in dashboard, meeting manager, transcript/summary viewer, task Kanban board & settings — no build step |
| **Background Scheduler** | APScheduler monitors upcoming meetings and triggers auto-processing |
| **Database Migrations** | Alembic-managed schema evolution (SQLite dev / PostgreSQL prod) |
| **Docker Ready** | Production-grade Dockerfile + docker-compose with PostgreSQL |

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        FastAPI (REST API)                     │
│  /api/v1/meetings  /transcripts  /summaries  /tasks  /health │
├──────────────────────────────────────────────────────────────┤
│                      Service Layer                            │
│  MeetingService │ TranscriptionService │ SummaryService       │
│  TaskService    │ EmailService                                   │
├──────────────────────────────────────────────────────────────┤
│                 Infrastructure Providers                       │
│  PlaywrightMeetingBot │ AudioRecorder │ WhisperEngine          │
│  OpenAILLMProvider    │ SendGridEmail │ SMTPEmail             │
├──────────────────────────────────────────────────────────────┤
│               Database (SQLAlchemy + Alembic)                  │
│  SQLite (dev) │ PostgreSQL (prod)                              │
├──────────────────────────────────────────────────────────────┤
│                   Background Workers                           │
│  APScheduler → MeetingPipeline (join → record → transcribe    │
│                → summarize → extract tasks → email)           │
└──────────────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.12 |
| **Web Framework** | FastAPI |
| **Database ORM** | SQLAlchemy 2.0 (async) |
| **Migrations** | Alembic |
| **Speech-to-Text** | faster-whisper (Whisper) |
| **LLM** | OpenAI GPT-4o |
| **Browser Automation** | Playwright |
| **Audio Recording** | sounddevice + soundfile |
| **Email** | SendGrid / SMTP (aiosmtplib) |
| **Scheduler** | APScheduler |
| **Testing** | pytest + pytest-asyncio + httpx |
| **Containerization** | Docker + docker-compose |
| **Linting** | Ruff + mypy |

---

## 📁 Project Structure

```
AI Meeting Agent/
├── src/meeting_agent/
│   ├── api/                          # FastAPI routes, schemas, deps
│   │   ├── deps.py                   # Dependency injection
│   │   ├── router.py                 # API router
│   │   ├── routes/                   # Endpoint handlers
│   │   │   ├── health.py
│   │   │   ├── meetings.py
│   │   │   ├── transcripts.py
│   │   │   ├── summaries.py
│   │   │   └── tasks.py
│   │   └── schemas/                  # Pydantic request/response models
│   │       ├── meetings.py
│   │       ├── transcripts.py
│   │       ├── summaries.py
│   │       ├── tasks.py
│   │       └── email.py
│   ├── core/                         # Domain layer (no external deps)
│   │   ├── config.py                 # Settings (pydantic-settings)
│   │   ├── domain_models.py          # Pure dataclass entities
│   │   ├── enums.py                  # Status/platform enums
│   │   ├── exceptions.py             # Custom exception hierarchy
│   │   └── interfaces.py             # Abstract base classes
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── connection.py         # Async SQLAlchemy engine
│   │   │   ├── models.py             # ORM table definitions
│   │   │   └── repositories/         # Data access layer
│   │   │       ├── meeting_repo.py
│   │   │       ├── transcript_repo.py
│   │   │       ├── summary_repo.py
│   │   │       ├── task_repo.py
│   │   │       └── email_log_repo.py
│   │   └── providers/                # External service integrations
│   │       ├── audio_recorder.py     # sounddevice audio capture
│   │       ├── whisper_engine.py     # faster-whisper transcription
│   │       ├── llm_provider.py       # OpenAI GPT-4o client
│   │       ├── email_sendgrid.py     # SendGrid email
│   │       ├── email_smtp.py         # SMTP email
│   │       └── meeting_bot.py        # Playwright meeting bot
│   ├── services/                     # Business logic
│   │   ├── meeting_service.py
│   │   ├── transcription_service.py
│   │   ├── summary_service.py
│   │   ├── task_service.py
│   │   └── email_service.py
│   ├── workers/                      # Background processing
│   │   ├── scheduler.py              # APScheduler job manager
│   │   └── pipeline.py               # Full meeting processing pipeline
│   ├── main.py                       # FastAPI app factory
│   └── asgi.py                       # Uvicorn ASGI entry point
├── tests/
│   ├── conftest.py                   # Shared fixtures
│   ├── unit/services/                # Unit tests for services
│   └── integration/                  # API integration tests
├── alembic/                          # Database migrations
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .dockerignore
├── scripts/
│   └── run_dev.sh                    # Dev setup script
├── pyproject.toml                    # Package config + deps
├── Makefile                          # Developer commands
├── .env.example                      # Environment template
└── .gitignore
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **pip** (or uv)
- **FFmpeg** (for audio processing)
- **PortAudio** (for audio recording — `libportaudio2` on Linux)
- **OpenAI API key** (for LLM features)

### 1. Clone and Setup

```bash
# Navigate to the project
cd "AI Meeting Agent"

# Option A: Use the setup script
chmod +x scripts/run_dev.sh
./scripts/run_dev.sh

# Option B: Manual setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual API keys
nano .env
```

**Required settings in `.env`:**

```env
# Required for AI features
OPENAI_API_KEY=sk-your-actual-openai-key

# Required for email (choose one)
SENDGRID_API_KEY=SG.your-key       # Option 1: SendGrid
SMTP_HOST=smtp.gmail.com           # Option 2: SMTP
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. Run the Server

```bash
source .venv/bin/activate
make run
```

The API is now live at **http://localhost:8000**

- 🖥️ **Web GUI**: http://localhost:8000/app/ (the root `/` redirects here)
- 📖 **Swagger UI**: http://localhost:8000/docs
- 📕 **ReDoc**: http://localhost:8000/redoc

### 4. Test It Works

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Create a meeting
curl -X POST http://localhost:8000/api/v1/meetings \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sprint Planning",
    "platform": "google_meet",
    "meeting_url": "https://meet.google.com/abc-defg-hij",
    "scheduled_at": "2026-06-01T10:00:00Z",
    "participants": ["alice@example.com", "bob@example.com"]
  }'

# List all meetings
curl http://localhost:8000/api/v1/meetings
```

---

## 🖥️ Web GUI

The project ships with a built-in, dependency-free web interface — a vanilla HTML/CSS/JS single-page app served by FastAPI itself (no Node/npm build step). It talks to the REST API described above.

**Open it at** `http://localhost:8000/app/` (or just `http://localhost:8000/`, which redirects there).

| View | What it does |
|------|--------------|
| **Dashboard** | Live stat tiles (total/upcoming/completed meetings, pending tasks), a status breakdown bar chart, and recent meetings |
| **Meetings** | Searchable, filterable, paginated meeting list; schedule new meetings via a modal form |
| **Meeting detail** | Lifecycle controls (Start/Stop bot), and five tabs: Overview, Transcript (with search + TXT/SRT/VTT export), Summary (inline-editable), Tasks, and Emails (compose + history). Live status polling while a meeting is processing |
| **Tasks** | A 4-column Kanban board — drag cards between columns to update status, or edit assignee/priority/due date inline |
| **Settings** | Read-only effective config + which credentials are configured (OpenAI/SendGrid/SMTP); toggle dark/light theme (persisted) |

The app lives under [`src/meeting_agent/static/`](src/meeting_agent/static/) (HTML shell, `css/`, and ES-module `js/` organized into `components/` and `views/`). The same origin serves both `/app` and `/api/v1`, so no CORS configuration is needed. To host the frontend on a different origin, set `DEBUG=true` (or add that origin to the CORS allowlist).

---

All configuration is managed via environment variables or the `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required.** Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | LLM model to use |
| `OPENAI_TEMPERATURE` | `0.3` | LLM sampling temperature |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model (`tiny`, `base`, `small`, `medium`, `large`) |
| `WHISPER_DEVICE` | `cpu` | Compute device (`cpu` or `cuda`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/meeting_agent.db` | Async database URL |
| `SENDGRID_API_KEY` | — | SendGrid API key (for email) |
| `EMAIL_PROVIDER` | `sendgrid` | Email provider (`sendgrid` or `smtp`) |
| `SMTP_HOST` | — | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USERNAME` | — | SMTP username |
| `SMTP_PASSWORD` | — | SMTP password |
| `BOT_HEADLESS` | `true` | Run browser in headless mode |
| `SCHEDULER_ENABLED` | `true` | Enable automatic meeting scheduler |
| `SCHEDULER_CHECK_INTERVAL_SECONDS` | `60` | How often to check for upcoming meetings |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEBUG` | `false` | Enable debug mode |

---

## 📡 API Reference

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |

### Stats & Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/stats` | Dashboard counts (meetings & tasks grouped by status) |
| `GET` | `/api/v1/settings/info` | Read-only effective config + credential availability flags (never secrets) |

### Meetings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/meetings` | Schedule a new meeting |
| `GET` | `/api/v1/meetings` | List meetings (paginated, filterable) |
| `GET` | `/api/v1/meetings/{id}` | Get meeting details |
| `PATCH` | `/api/v1/meetings/{id}` | Update meeting metadata |
| `DELETE` | `/api/v1/meetings/{id}` | Delete a meeting |
| `POST` | `/api/v1/meetings/{id}/start` | Trigger bot to join |
| `POST` | `/api/v1/meetings/{id}/stop` | Stop and begin processing |
| `GET` | `/api/v1/meetings/{id}/status` | Get meeting status |
| `POST` | `/api/v1/meetings/{id}/send-email` | Send summary email |
| `GET` | `/api/v1/meetings/{id}/emails` | Get email history |
| `GET` | `/api/v1/meetings/{id}/transcript` | Get the meeting's transcript (404 until transcribed) |
| `GET` | `/api/v1/meetings/{id}/summary` | Get the meeting's AI summary (404 until summarized) |
| `GET` | `/api/v1/meetings/{id}/tasks` | List action items for the meeting |

### Transcripts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/transcripts/{id}` | Get transcript with segments |
| `GET` | `/api/v1/transcripts/{id}/export?format=srt` | Export as TXT, SRT, or VTT |

### Summaries

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/summaries/{id}` | Get summary |
| `PATCH` | `/api/v1/summaries/{id}` | Edit summary (manual corrections) |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/tasks` | List tasks (paginated, filterable) |
| `GET` | `/api/v1/tasks/{id}` | Get task details |
| `PATCH` | `/api/v1/tasks/{id}` | Update task |
| `DELETE` | `/api/v1/tasks/{id}` | Delete task |

### Example: Full Meeting Workflow via API

```bash
# 1. Create a meeting
MEETING=$(curl -s -X POST http://localhost:8000/api/v1/meetings \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Q3 Planning",
    "platform": "google_meet",
    "meeting_url": "https://meet.google.com/xyz",
    "scheduled_at": "2026-06-15T14:00:00Z",
    "participants": ["team@company.com"]
  }')

MEETING_ID=$(echo $MEETING | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Start the meeting (bot joins)
curl -X POST http://localhost:8000/api/v1/meetings/$MEETING_ID/start

# 3. Stop the meeting (triggers transcription → summary → tasks)
curl -X POST http://localhost:8000/api/v1/meetings/$MEETING_ID/stop

# 4. Check status
curl http://localhost:8000/api/v1/meetings/$MEETING_ID/status

# 5. Send summary email to participants
curl -X POST http://localhost:8000/api/v1/meetings/$MEETING_ID/send-email \
  -H "Content-Type: application/json" \
  -d '{"recipients": ["team@company.com"]}'
```

---

## 🧪 Testing

### Run All Tests (50 tests)

```bash
source .venv/bin/activate
make test
```

### Run Specific Test Suites

```bash
# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Tests with coverage report
make test-cov
```

### Test Structure

```
tests/
├── conftest.py                           # Shared fixtures + in-memory DB
├── unit/services/
│   ├── test_meeting_service.py           # 12 tests — CRUD, lifecycle, errors
│   ├── test_transcription_service.py     #  8 tests — TXT/SRT/VTT export
│   ├── test_summary_and_task_service.py  # 10 tests — LLM generation, extraction
│   └── test_email_service.py             #  5 tests — send, fail, history
└── integration/
    └── test_api.py                       # 13 tests — full API endpoint tests
```

### What's Tested

- ✅ Meeting CRUD and state transitions (scheduled → joining → recording → transcribing → summarizing → completed)
- ✅ Error handling (not found, already started, invalid state)
- ✅ Transcription export in TXT, SRT, VTT formats
- ✅ Summary generation with mocked LLM
- ✅ Task extraction with mocked LLM
- ✅ Email composition, send success, send failure
- ✅ API validation (422 on invalid input)
- ✅ Pagination and filtering

---

## 🐳 Docker Deployment

### Build and Run

```bash
# Build the image
make docker-build

# Start all services (API + PostgreSQL)
make docker-up

# Stop
make docker-down
```

### docker-compose

The `docker/docker-compose.yml` includes:

- **`api`** — The FastAPI application (port 8000)
- **`db`** — PostgreSQL 16 database (port 5432)

For production, set these in your `.env`:

```env
DATABASE_URL=postgresql+asyncpg://meeting_agent:changeme@db:5432/meeting_agent
DATABASE_URL_SYNC=postgresql://meeting_agent:changeme@db:5432/meeting_agent
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.your-production-key
```

---

## 🔄 Automation Flow

The full processing pipeline runs automatically when the scheduler detects an upcoming meeting:

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Scheduler   │────▶│  Bot Joins   │────▶│  Records Audio  │
│  (every 60s) │     │  Meeting     │     │  (sounddevice)  │
└─────────────┘     └──────────────┘     └────────┬───────┘
                                                   │
┌─────────────┐     ┌──────────────┐     ┌────────▼───────┐
│  Email       │◀────│  Extract     │◀────│  Whisper STT   │
│  Participants│     │  Tasks       │     │  Transcription  │
└─────────────┘     └──────────────┘     └────────┬───────┘
                           ▲                       │
                    ┌──────┴───────┐        ┌──────▼────────┐
                    │  LLM Summary │◀───────│  Transcript    │
                    │  (GPT-4o)    │        │  Segments      │
                    └──────────────┘        └───────────────┘
```

### Meeting Status Lifecycle

```
scheduled → joining → in_progress → recording → transcribing → summarizing → completed
                │                                                    │
                └──────────────► failed ◄───────────────────────────┘
```

---

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'meeting_agent'` | Run `pip install -e .` from the project root |
| `sounddevice` import error | Install PortAudio: `sudo apt install libportaudio2 portaudio19-dev` |
| `playwright` browser not found | Run `playwright install chromium` |
| Whisper model download slow | First run downloads the model; subsequent runs use cache |
| `no such table: meetings` | Tables auto-create on startup; run `make run` once |
| Tests fail with ROS plugin errors | Already handled via `pyproject.toml` config |
| Email not sending | Check `SENDGRID_API_KEY` or SMTP credentials in `.env` |
| Docker build fails | Ensure Docker has enough memory (4GB+ recommended) |

### Makefile Commands

```bash
make help          # Show all available commands
make install       # Install production dependencies
make dev           # Install dev dependencies + Playwright
make run           # Start development server
make test          # Run all tests
make test-unit     # Unit tests only
make test-integration  # Integration tests only
make test-cov      # Tests with coverage report
make lint          # Run linters (ruff + mypy)
make format        # Auto-format code
make migrate       # Run database migrations
make docker-up     # Start Docker containers
make docker-down   # Stop Docker containers
make clean         # Clean generated files
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
