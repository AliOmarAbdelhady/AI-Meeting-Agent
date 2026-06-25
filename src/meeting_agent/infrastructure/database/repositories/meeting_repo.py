"""SQLAlchemy implementation of MeetingRepository."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from meeting_agent.core.domain_models import Meeting
from meeting_agent.core.enums import MeetingPlatform, MeetingStatus


class SqlMeetingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, meeting: Meeting) -> dict:
        from meeting_agent.infrastructure.database.models import MeetingModel
        model = MeetingModel(
            id=str(meeting.id),
            title=meeting.title,
            platform=meeting.platform.value,
            meeting_url=meeting.meeting_url,
            scheduled_at=meeting.scheduled_at,
            status=meeting.status.value,
            participants=meeting.participants,
            calendar_event_id=meeting.calendar_event_id,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_dict(model)

    async def get_by_id(self, meeting_id: str) -> Optional[dict]:
        from meeting_agent.infrastructure.database.models import MeetingModel
        result = await self.session.execute(
            select(MeetingModel).where(MeetingModel.id == meeting_id)
        )
        model = result.scalar_one_or_none()
        return self._to_dict(model) if model else None

    async def list_all(
        self,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        from meeting_agent.infrastructure.database.models import MeetingModel
        query = select(MeetingModel)
        count_query = select(func.count()).select_from(MeetingModel)

        if status:
            query = query.where(MeetingModel.status == status)
            count_query = count_query.where(MeetingModel.status == status)
        if platform:
            query = query.where(MeetingModel.platform == platform)
            count_query = count_query.where(MeetingModel.platform == platform)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(MeetingModel.scheduled_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_dict(m) for m in models], total

    async def update_status(self, meeting_id: str, status: str, **kwargs) -> Optional[dict]:
        from meeting_agent.infrastructure.database.models import MeetingModel
        values = {"status": status, "updated_at": datetime.utcnow()}
        values.update(kwargs)
        await self.session.execute(
            update(MeetingModel).where(MeetingModel.id == meeting_id).values(**values)
        )
        await self.session.flush()
        return await self.get_by_id(meeting_id)

    async def delete(self, meeting_id: str) -> bool:
        from meeting_agent.infrastructure.database.models import MeetingModel
        result = await self.session.execute(
            delete(MeetingModel).where(MeetingModel.id == meeting_id)
        )
        return result.rowcount > 0

    async def count_by_status(self) -> dict[str, int]:
        """Return a mapping of meeting status -> count."""
        from meeting_agent.infrastructure.database.models import MeetingModel
        result = await self.session.execute(
            select(MeetingModel.status, func.count()).group_by(MeetingModel.status)
        )
        return {status: count for status, count in result.all()}

    async def get_upcoming(self, within_minutes: int = 5) -> list[dict]:
        from meeting_agent.infrastructure.database.models import MeetingModel
        now = datetime.utcnow()
        cutoff = now + timedelta(minutes=within_minutes)
        result = await self.session.execute(
            select(MeetingModel)
            .where(MeetingModel.status == MeetingStatus.SCHEDULED.value)
            .where(MeetingModel.scheduled_at.between(now, cutoff))
            .order_by(MeetingModel.scheduled_at)
        )
        return [self._to_dict(m) for m in result.scalars().all()]

    @staticmethod
    def _to_dict(model) -> dict:
        return {
            "id": model.id,
            "title": model.title,
            "platform": model.platform,
            "meeting_url": model.meeting_url,
            "scheduled_at": model.scheduled_at,
            "started_at": model.started_at,
            "ended_at": model.ended_at,
            "status": model.status,
            "duration_seconds": model.duration_seconds,
            "participants": model.participants or [],
            "raw_audio_path": model.raw_audio_path,
            "calendar_event_id": model.calendar_event_id,
            "error_message": model.error_message,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }
