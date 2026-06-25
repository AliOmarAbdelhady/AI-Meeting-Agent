"""Shared test fixtures and configuration."""

import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from meeting_agent.infrastructure.database.models import Base
from meeting_agent.infrastructure.database.repositories.meeting_repo import SqlMeetingRepository
from meeting_agent.infrastructure.database.repositories.transcript_repo import SqlTranscriptRepository
from meeting_agent.infrastructure.database.repositories.summary_repo import SqlSummaryRepository
from meeting_agent.infrastructure.database.repositories.task_repo import SqlTaskRepository
from meeting_agent.infrastructure.database.repositories.email_log_repo import SqlEmailLogRepository

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """Provide a fresh test database engine with tables created."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provide a test database session."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
def meeting_repo(db_session):
    return SqlMeetingRepository(db_session)


@pytest_asyncio.fixture
def transcript_repo(db_session):
    return SqlTranscriptRepository(db_session)


@pytest_asyncio.fixture
def summary_repo(db_session):
    return SqlSummaryRepository(db_session)


@pytest_asyncio.fixture
def task_repo(db_session):
    return SqlTaskRepository(db_session)


@pytest_asyncio.fixture
def email_log_repo(db_session):
    return SqlEmailLogRepository(db_session)


# ── Factory helpers ───────────────────────────────────────────────────────────


def make_meeting_kwargs(**overrides):
    """Generate valid meeting data with defaults."""
    defaults = {
        "title": "Test Meeting",
        "platform": "google_meet",
        "meeting_url": "https://meet.google.com/abc-defg-hij",
        "status": "scheduled",
        "participants": ["alice@example.com", "bob@example.com"],
    }
    defaults.update(overrides)
    return defaults
