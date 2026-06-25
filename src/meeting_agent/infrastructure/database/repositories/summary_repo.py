"""SQLAlchemy implementation of SummaryRepository."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class SqlSummaryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        meeting_id: str,
        summary_text: str,
        key_points: list[str],
        decisions: list[str],
        action_items: list[str],
        model_used: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
    ) -> dict:
        from meeting_agent.infrastructure.database.models import SummaryModel
        from uuid import uuid4
        model = SummaryModel(
            id=str(uuid4()),
            meeting_id=meeting_id,
            summary_text=summary_text,
            key_points=key_points,
            decisions=decisions,
            action_items=action_items,
            model_used=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_dict(model)

    async def get_by_meeting_id(self, meeting_id: str) -> Optional[dict]:
        from meeting_agent.infrastructure.database.models import SummaryModel
        result = await self.session.execute(
            select(SummaryModel).where(SummaryModel.meeting_id == meeting_id)
        )
        model = result.scalar_one_or_none()
        return self._to_dict(model) if model else None

    async def get_by_id(self, summary_id: str) -> Optional[dict]:
        from meeting_agent.infrastructure.database.models import SummaryModel
        result = await self.session.execute(
            select(SummaryModel).where(SummaryModel.id == summary_id)
        )
        model = result.scalar_one_or_none()
        return self._to_dict(model) if model else None

    async def update_fields(self, summary_id: str, **fields) -> Optional[dict]:
        from meeting_agent.infrastructure.database.models import SummaryModel
        if "updated_at" not in fields:
            fields["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(SummaryModel).where(SummaryModel.id == summary_id).values(**fields)
        )
        return await self.get_by_id(summary_id)

    @staticmethod
    def _to_dict(model) -> dict:
        return {
            "id": model.id,
            "meeting_id": model.meeting_id,
            "summary_text": model.summary_text,
            "key_points": model.key_points or [],
            "decisions": model.decisions or [],
            "action_items": model.action_items or [],
            "model_used": model.model_used,
            "prompt_tokens": model.prompt_tokens,
            "completion_tokens": model.completion_tokens,
            "created_at": model.created_at,
        }
