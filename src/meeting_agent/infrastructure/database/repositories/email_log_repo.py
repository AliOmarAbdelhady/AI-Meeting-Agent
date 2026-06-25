"""SQLAlchemy implementation of EmailLogRepository."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlEmailLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        meeting_id: str,
        recipients: list[str],
        subject: str,
    ) -> dict:
        from meeting_agent.infrastructure.database.models import EmailLogModel
        model = EmailLogModel(
            id=str(uuid4()),
            meeting_id=meeting_id,
            recipients=recipients,
            subject=subject,
            status="pending",
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_dict(model)

    async def mark_sent(self, email_id: str, provider_message_id: Optional[str] = None) -> dict:
        from meeting_agent.infrastructure.database.models import EmailLogModel
        from sqlalchemy import update
        await self.session.execute(
            update(EmailLogModel)
            .where(EmailLogModel.id == email_id)
            .values(status="sent", provider_message_id=provider_message_id, sent_at=datetime.utcnow())
        )
        return await self.get_by_id(email_id)

    async def mark_failed(self, email_id: str, error_message: str) -> dict:
        from meeting_agent.infrastructure.database.models import EmailLogModel
        from sqlalchemy import update
        await self.session.execute(
            update(EmailLogModel)
            .where(EmailLogModel.id == email_id)
            .values(status="failed", error_message=error_message)
        )
        return await self.get_by_id(email_id)

    async def get_by_meeting_id(self, meeting_id: str) -> list[dict]:
        from meeting_agent.infrastructure.database.models import EmailLogModel
        result = await self.session.execute(
            select(EmailLogModel).where(EmailLogModel.meeting_id == meeting_id).order_by(EmailLogModel.created_at.desc())
        )
        return [self._to_dict(m) for m in result.scalars().all()]

    async def get_by_id(self, email_id: str) -> Optional[dict]:
        from meeting_agent.infrastructure.database.models import EmailLogModel
        result = await self.session.execute(
            select(EmailLogModel).where(EmailLogModel.id == email_id)
        )
        model = result.scalar_one_or_none()
        return self._to_dict(model) if model else None

    @staticmethod
    def _to_dict(model) -> dict:
        return {
            "id": model.id,
            "meeting_id": model.meeting_id,
            "recipients": model.recipients or [],
            "subject": model.subject,
            "status": model.status,
            "provider_message_id": model.provider_message_id,
            "error_message": model.error_message,
            "sent_at": model.sent_at,
            "created_at": model.created_at,
        }
