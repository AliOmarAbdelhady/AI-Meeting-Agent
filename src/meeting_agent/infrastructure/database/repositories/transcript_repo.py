"""SQLAlchemy implementation of TranscriptRepository."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlTranscriptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, meeting_id: str, full_text: str, language: str, duration_seconds: float, word_count: Optional[int] = None) -> dict:
        from meeting_agent.infrastructure.database.models import TranscriptModel
        from uuid import uuid4
        model = TranscriptModel(
            id=str(uuid4()),
            meeting_id=meeting_id,
            full_text=full_text,
            language=language,
            duration_seconds=duration_seconds,
            word_count=word_count,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_dict(model)

    async def get_by_meeting_id(self, meeting_id: str) -> Optional[dict]:
        from meeting_agent.infrastructure.database.models import TranscriptModel
        result = await self.session.execute(
            select(TranscriptModel).where(TranscriptModel.meeting_id == meeting_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        data = self._to_dict(model)
        # Also fetch segments
        data["segments"] = await self._get_segments(model.id)
        return data

    async def get_by_id(self, transcript_id: str) -> Optional[dict]:
        from meeting_agent.infrastructure.database.models import TranscriptModel
        result = await self.session.execute(
            select(TranscriptModel).where(TranscriptModel.id == transcript_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        data = self._to_dict(model)
        data["segments"] = await self._get_segments(model.id)
        return data

    async def _get_segments(self, transcript_id: str) -> list[dict]:
        from meeting_agent.infrastructure.database.models import TranscriptSegmentModel
        result = await self.session.execute(
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.transcript_id == transcript_id)
            .order_by(TranscriptSegmentModel.segment_index)
        )
        return [{
            "id": s.id,
            "text": s.text,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "speaker": s.speaker,
            "confidence": s.confidence,
            "segment_index": s.segment_index,
        } for s in result.scalars().all()]

    @staticmethod
    def _to_dict(model) -> dict:
        return {
            "id": model.id,
            "meeting_id": model.meeting_id,
            "full_text": model.full_text,
            "language": model.language,
            "duration_seconds": model.duration_seconds,
            "word_count": model.word_count,
            "created_at": model.created_at,
        }
