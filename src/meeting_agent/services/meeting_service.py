"""Business logic for meeting lifecycle management."""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from meeting_agent.core.domain_models import Meeting
from meeting_agent.core.enums import MeetingPlatform, MeetingStatus
from meeting_agent.core.exceptions import (
    MeetingAlreadyStartedError,
    MeetingNotFoundError,
    MeetingNotReadyError,
)
from meeting_agent.infrastructure.database.repositories.meeting_repo import SqlMeetingRepository

logger = logging.getLogger(__name__)


class MeetingService:
    """Orchestrates CRUD operations and state transitions for meetings."""

    def __init__(self, repo: SqlMeetingRepository):
        self.repo = repo

    async def create_meeting(self, body) -> dict:
        """Create a new scheduled meeting."""
        meeting = Meeting(
            id=uuid4(),
            title=body.title,
            platform=body.platform,
            meeting_url=body.meeting_url,
            scheduled_at=body.scheduled_at,
            participants=body.participants,
            calendar_event_id=body.calendar_event_id,
            status=MeetingStatus.SCHEDULED,
        )
        result = await self.repo.create(meeting)
        logger.info("Created meeting %s: %s", meeting.id, meeting.title)
        return result

    async def get_meeting(self, meeting_id: str) -> Optional[dict]:
        """Retrieve a meeting by ID."""
        meeting = await self.repo.get_by_id(meeting_id)
        if not meeting:
            raise MeetingNotFoundError(meeting_id)
        return meeting

    async def list_meetings(
        self,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """List meetings with optional filters and pagination."""
        offset = (page - 1) * page_size
        items, total = await self.repo.list_all(
            status=status,
            platform=platform,
            offset=offset,
            limit=page_size,
        )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_meeting(self, meeting_id: str, body) -> dict:
        """Update meeting metadata."""
        existing = await self.repo.get_by_id(meeting_id)
        if not existing:
            raise MeetingNotFoundError(meeting_id)

        updates = {}
        if body.title is not None:
            updates["title"] = body.title
        if body.scheduled_at is not None:
            updates["scheduled_at"] = body.scheduled_at
        if body.participants is not None:
            updates["participants"] = body.participants

        if updates:
            result = await self.repo.update_status(meeting_id, existing["status"], **updates)
            logger.info("Updated meeting %s", meeting_id)
            return result
        return existing

    async def delete_meeting(self, meeting_id: str) -> None:
        """Delete a meeting (only if scheduled)."""
        existing = await self.repo.get_by_id(meeting_id)
        if not existing:
            raise MeetingNotFoundError(meeting_id)
        if existing["status"] not in (MeetingStatus.SCHEDULED.value, MeetingStatus.CANCELLED.value):
            raise MeetingNotReadyError(meeting_id, existing["status"])
        await self.repo.delete(meeting_id)
        logger.info("Deleted meeting %s", meeting_id)

    async def start_meeting(self, meeting_id: str) -> dict:
        """Transition meeting to joining state and trigger bot."""
        existing = await self.repo.get_by_id(meeting_id)
        if not existing:
            raise MeetingNotFoundError(meeting_id)
        if existing["status"] not in (MeetingStatus.SCHEDULED.value,):
            raise MeetingAlreadyStartedError(meeting_id)

        result = await self.repo.update_status(
            meeting_id,
            MeetingStatus.JOINING.value,
            started_at=datetime.utcnow(),
        )
        logger.info("Meeting %s transitioned to JOINING", meeting_id)
        return result

    async def stop_meeting(self, meeting_id: str) -> dict:
        """Stop meeting recording and begin post-processing."""
        existing = await self.repo.get_by_id(meeting_id)
        if not existing:
            raise MeetingNotFoundError(meeting_id)
        if existing["status"] not in (
            MeetingStatus.IN_PROGRESS.value,
            MeetingStatus.RECORDING.value,
        ):
            raise MeetingNotReadyError(meeting_id, existing["status"])

        result = await self.repo.update_status(
            meeting_id,
            MeetingStatus.TRANSCRIBING.value,
            ended_at=datetime.utcnow(),
        )
        logger.info("Meeting %s stopped, entering TRANSCRIBING", meeting_id)
        return result

    async def get_upcoming_meetings(self, within_minutes: int = 5) -> list[dict]:
        """Get meetings scheduled to start within the given window."""
        return await self.repo.get_upcoming(within_minutes)

    async def get_status_counts(self) -> dict[str, int]:
        """Return a mapping of meeting status -> count (for the dashboard)."""
        counts = await self.repo.count_by_status()
        # Ensure every known status is represented, even if zero.
        return {status.value: counts.get(status.value, 0) for status in MeetingStatus}

    async def mark_failed(self, meeting_id: str, error_message: str) -> dict:
        """Mark a meeting as failed with an error message."""
        result = await self.repo.update_status(
            meeting_id,
            MeetingStatus.FAILED.value,
            error_message=error_message,
        )
        logger.error("Meeting %s failed: %s", meeting_id, error_message)
        return result
