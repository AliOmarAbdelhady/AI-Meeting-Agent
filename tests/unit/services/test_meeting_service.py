"""Unit tests for MeetingService."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from meeting_agent.core.domain_models import Meeting
from meeting_agent.core.enums import MeetingPlatform, MeetingStatus
from meeting_agent.core.exceptions import MeetingNotFoundError, MeetingAlreadyStartedError
from meeting_agent.services.meeting_service import MeetingService


class MockMeetingCreate:
    """Mock request body for creating a meeting."""
    def __init__(self, **kwargs):
        self.title = kwargs.get("title", "Sprint Planning")
        self.platform = kwargs.get("platform", MeetingPlatform.GOOGLE_MEET)
        self.meeting_url = kwargs.get("meeting_url", "https://meet.google.com/abc")
        self.scheduled_at = kwargs.get("scheduled_at", datetime.utcnow() + timedelta(hours=1))
        self.participants = kwargs.get("participants", ["alice@example.com"])
        self.calendar_event_id = kwargs.get("calendar_event_id", None)


class MockMeetingUpdate:
    def __init__(self, title=None, scheduled_at=None, participants=None):
        self.title = title
        self.scheduled_at = scheduled_at
        self.participants = participants


@pytest.mark.asyncio
class TestMeetingServiceCreate:
    async def test_create_meeting_success(self, meeting_repo):
        service = MeetingService(meeting_repo)
        body = MockMeetingCreate()

        result = await service.create_meeting(body)

        assert result["title"] == "Sprint Planning"
        assert result["platform"] == "google_meet"
        assert result["status"] == "scheduled"
        assert result["participants"] == ["alice@example.com"]

    async def test_create_meeting_with_calendar_event(self, meeting_repo):
        service = MeetingService(meeting_repo)
        body = MockMeetingCreate(calendar_event_id="evt123")

        result = await service.create_meeting(body)

        assert result["calendar_event_id"] == "evt123"


@pytest.mark.asyncio
class TestMeetingServiceGet:
    async def test_get_meeting_exists(self, meeting_repo):
        service = MeetingService(meeting_repo)
        body = MockMeetingCreate()
        created = await service.create_meeting(body)

        result = await service.get_meeting(created["id"])

        assert result["id"] == created["id"]
        assert result["title"] == "Sprint Planning"

    async def test_get_meeting_not_found(self, meeting_repo):
        service = MeetingService(meeting_repo)

        with pytest.raises(MeetingNotFoundError):
            await service.get_meeting(str(uuid4()))


@pytest.mark.asyncio
class TestMeetingServiceList:
    async def test_list_meetings_empty(self, meeting_repo):
        service = MeetingService(meeting_repo)

        result = await service.list_meetings()

        assert result["items"] == []
        assert result["total"] == 0

    async def test_list_meetings_with_data(self, meeting_repo):
        service = MeetingService(meeting_repo)
        await service.create_meeting(MockMeetingCreate(title="Meeting 1"))
        await service.create_meeting(MockMeetingCreate(title="Meeting 2"))

        result = await service.list_meetings()

        assert result["total"] == 2
        assert len(result["items"]) == 2

    async def test_list_meetings_pagination(self, meeting_repo):
        service = MeetingService(meeting_repo)
        for i in range(5):
            await service.create_meeting(MockMeetingCreate(title=f"M{i}"))

        result = await service.list_meetings(page=1, page_size=2)

        assert result["total"] == 5
        assert len(result["items"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2


@pytest.mark.asyncio
class TestMeetingServiceUpdate:
    async def test_update_meeting_title(self, meeting_repo):
        service = MeetingService(meeting_repo)
        created = await service.create_meeting(MockMeetingCreate())

        result = await service.update_meeting(created["id"], MockMeetingUpdate(title="Updated Title"))

        assert result["title"] == "Updated Title"

    async def test_update_meeting_not_found(self, meeting_repo):
        service = MeetingService(meeting_repo)

        with pytest.raises(MeetingNotFoundError):
            await service.update_meeting(str(uuid4()), MockMeetingUpdate(title="X"))


@pytest.mark.asyncio
class TestMeetingServiceLifecycle:
    async def test_start_meeting(self, meeting_repo):
        service = MeetingService(meeting_repo)
        created = await service.create_meeting(MockMeetingCreate())

        result = await service.start_meeting(created["id"])

        assert result["status"] == "joining"
        assert result["started_at"] is not None

    async def test_start_meeting_already_started(self, meeting_repo):
        service = MeetingService(meeting_repo)
        created = await service.create_meeting(MockMeetingCreate())
        await service.start_meeting(created["id"])

        with pytest.raises(MeetingAlreadyStartedError):
            await service.start_meeting(created["id"])

    async def test_stop_meeting(self, meeting_repo):
        service = MeetingService(meeting_repo)
        created = await service.create_meeting(MockMeetingCreate())
        await service.start_meeting(created["id"])
        # Simulate transition to in_progress
        await meeting_repo.update_status(created["id"], "in_progress")

        result = await service.stop_meeting(created["id"])

        assert result["status"] == "transcribing"
        assert result["ended_at"] is not None

    async def test_delete_meeting(self, meeting_repo):
        service = MeetingService(meeting_repo)
        created = await service.create_meeting(MockMeetingCreate())

        await service.delete_meeting(created["id"])

        with pytest.raises(MeetingNotFoundError):
            await service.get_meeting(created["id"])

    async def test_mark_failed(self, meeting_repo):
        service = MeetingService(meeting_repo)
        created = await service.create_meeting(MockMeetingCreate())

        result = await service.mark_failed(created["id"], "Bot crashed")

        assert result["status"] == "failed"
        assert "Bot crashed" in result["error_message"]
