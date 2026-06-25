"""Integration tests for API endpoints."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from meeting_agent.infrastructure.database.models import Base
from meeting_agent.infrastructure.database.connection import get_async_session
from meeting_agent.api.deps import get_db
from meeting_agent.main import create_app


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_session():
    """Override database session for tests — uses in-memory test DB."""
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture
async def client():
    """Provide an async HTTP test client with a fresh in-memory database."""
    # Create tables on test engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    # Override the database dependency so the app uses our test DB
    app.dependency_overrides[get_db] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_check(self, client):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "AI Meeting Agent"


@pytest.mark.asyncio
class TestMeetingEndpoints:
    async def test_create_meeting(self, client):
        payload = {
            "title": "Sprint Planning",
            "platform": "google_meet",
            "meeting_url": "https://meet.google.com/abc-defg-hij",
            "scheduled_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "participants": ["alice@example.com", "bob@example.com"],
        }

        response = await client.post("/api/v1/meetings", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Sprint Planning"
        assert data["status"] == "scheduled"
        assert "id" in data

    async def test_create_meeting_invalid(self, client):
        payload = {"title": ""}  # Missing required fields

        response = await client.post("/api/v1/meetings", json=payload)
        assert response.status_code == 422

    async def test_list_meetings_empty(self, client):
        response = await client.get("/api/v1/meetings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_meetings_with_data(self, client):
        # Create two meetings
        for i in range(2):
            payload = {
                "title": f"Meeting {i}",
                "platform": "zoom",
                "meeting_url": f"https://zoom.us/j/{i}",
                "scheduled_at": (datetime.utcnow() + timedelta(hours=i + 1)).isoformat(),
            }
            await client.post("/api/v1/meetings", json=payload)

        response = await client.get("/api/v1/meetings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_get_meeting_by_id(self, client):
        payload = {
            "title": "Test Meeting",
            "platform": "teams",
            "meeting_url": "https://teams.microsoft.com/meet/123",
            "scheduled_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }
        create_resp = await client.post("/api/v1/meetings", json=payload)
        meeting_id = create_resp.json()["id"]

        response = await client.get(f"/api/v1/meetings/{meeting_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Test Meeting"

    async def test_get_meeting_not_found(self, client):
        response = await client.get(f"/api/v1/meetings/{uuid4()}")
        assert response.status_code == 400  # MeetingAgentError handler returns 400
        assert "MEETING_NOT_FOUND" in response.json()["error"]["code"]

    async def test_update_meeting(self, client):
        payload = {
            "title": "Original",
            "platform": "google_meet",
            "meeting_url": "https://meet.google.com/test",
            "scheduled_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }
        create_resp = await client.post("/api/v1/meetings", json=payload)
        meeting_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/meetings/{meeting_id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    async def test_start_meeting(self, client):
        payload = {
            "title": "Startable",
            "platform": "google_meet",
            "meeting_url": "https://meet.google.com/start",
            "scheduled_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }
        create_resp = await client.post("/api/v1/meetings", json=payload)
        meeting_id = create_resp.json()["id"]

        response = await client.post(f"/api/v1/meetings/{meeting_id}/start")
        assert response.status_code == 200
        assert response.json()["status"] == "joining"

    async def test_delete_meeting(self, client):
        payload = {
            "title": "Deletable",
            "platform": "google_meet",
            "meeting_url": "https://meet.google.com/del",
            "scheduled_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }
        create_resp = await client.post("/api/v1/meetings", json=payload)
        meeting_id = create_resp.json()["id"]

        response = await client.delete(f"/api/v1/meetings/{meeting_id}")
        assert response.status_code == 204

    async def test_meeting_status(self, client):
        payload = {
            "title": "Status Check",
            "platform": "google_meet",
            "meeting_url": "https://meet.google.com/status",
            "scheduled_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }
        create_resp = await client.post("/api/v1/meetings", json=payload)
        meeting_id = create_resp.json()["id"]

        response = await client.get(f"/api/v1/meetings/{meeting_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == "scheduled"


@pytest.mark.asyncio
class TestTaskEndpoints:
    async def test_list_tasks_empty(self, client):
        response = await client.get("/api/v1/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_get_task_not_found(self, client):
        response = await client.get(f"/api/v1/tasks/{uuid4()}")
        assert response.status_code == 400  # MeetingAgentError handler returns 400
        assert "TASK_NOT_FOUND" in response.json()["error"]["code"]


async def _create_meeting(client, **overrides):
    """Helper: create a meeting and return its id."""
    payload = {
        "title": "Test Meeting",
        "platform": "google_meet",
        "meeting_url": "https://meet.google.com/abc-defg-hij",
        "scheduled_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "participants": ["alice@example.com"],
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/meetings", json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
class TestMeetingNestedEndpoints:
    """Meeting-scoped routes that back the GUI detail view."""

    async def test_transcript_not_ready_returns_404(self, client):
        meeting_id = await _create_meeting(client)
        response = await client.get(f"/api/v1/meetings/{meeting_id}/transcript")
        assert response.status_code == 404

    async def test_summary_not_ready_returns_404(self, client):
        meeting_id = await _create_meeting(client)
        response = await client.get(f"/api/v1/meetings/{meeting_id}/summary")
        assert response.status_code == 404

    async def test_tasks_empty_returns_list(self, client):
        meeting_id = await _create_meeting(client)
        response = await client.get(f"/api/v1/meetings/{meeting_id}/tasks")
        assert response.status_code == 200
        assert response.json() == []

    async def test_nested_endpoints_unknown_meeting_404(self, client):
        unknown = uuid4()
        for suffix in ("/transcript", "/summary", "/tasks"):
            response = await client.get(f"/api/v1/meetings/{unknown}{suffix}")
            assert response.status_code == 404, suffix


@pytest.mark.asyncio
class TestStatsAndSettings:
    async def test_stats_structure_and_counts(self, client):
        before = (await client.get("/api/v1/stats")).json()
        assert before["meetings_total"] == 0
        assert "scheduled" in before["meetings"]
        assert before["meetings"]["scheduled"] == 0

        await _create_meeting(client, title="Stats Meeting")

        after = (await client.get("/api/v1/stats")).json()
        assert after["meetings_total"] == 1
        assert after["meetings"]["scheduled"] == 1
        assert "pending" in after["tasks"]
        assert "tasks_total" in after

    async def test_settings_info_is_safe_and_non_secret(self, client):
        response = await client.get("/api/v1/settings/info")
        assert response.status_code == 200
        data = response.json()
        # Non-secret effective config keys are present.
        for key in ("app_name", "openai_model", "email_provider", "openai_configured"):
            assert key in data
        # Availability flags are booleans.
        assert isinstance(data["openai_configured"], bool)
        # No secret material ever leaks into the response.
        body = response.text.lower()
        for secret in ("sk-", "password", "api_key", "secret"):
            assert secret not in body, f"leaked secret marker: {secret}"


@pytest.mark.asyncio
class TestWebGui:
    async def test_root_redirects_to_app(self, client):
        response = await client.get("/", follow_redirects=False)
        assert response.status_code in (307, 301)
        assert response.headers["location"].rstrip("/") == "/app"

    async def test_app_serves_index(self, client):
        response = await client.get("/app/")
        assert response.status_code == 200
        assert "AI Meeting Agent" in response.text
        assert "app.js" in response.text

