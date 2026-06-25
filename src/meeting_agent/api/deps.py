"""FastAPI dependency injection functions."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from meeting_agent.infrastructure.database.connection import get_async_session
from meeting_agent.infrastructure.database.repositories.meeting_repo import SqlMeetingRepository
from meeting_agent.infrastructure.database.repositories.transcript_repo import SqlTranscriptRepository
from meeting_agent.infrastructure.database.repositories.summary_repo import SqlSummaryRepository
from meeting_agent.infrastructure.database.repositories.task_repo import SqlTaskRepository
from meeting_agent.infrastructure.database.repositories.email_log_repo import SqlEmailLogRepository
from meeting_agent.services.meeting_service import MeetingService
from meeting_agent.services.summary_service import SummaryService
from meeting_agent.services.task_service import TaskService
from meeting_agent.services.email_service import EmailService
from meeting_agent.services.transcription_service import TranscriptionService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async for session in get_async_session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_meeting_service(db: DbSession) -> MeetingService:
    return MeetingService(SqlMeetingRepository(db))


def get_transcription_service(db: DbSession) -> TranscriptionService:
    return TranscriptionService(
        meeting_repo=SqlMeetingRepository(db),
        transcript_repo=SqlTranscriptRepository(db),
    )


def get_summary_service(db: DbSession) -> SummaryService:
    return SummaryService(
        transcript_repo=SqlTranscriptRepository(db),
        summary_repo=SqlSummaryRepository(db),
    )


def get_task_service(db: DbSession) -> TaskService:
    return TaskService(
        task_repo=SqlTaskRepository(db),
        summary_repo=SqlSummaryRepository(db),
    )


def get_email_service(db: DbSession) -> EmailService:
    return EmailService(
        email_log_repo=SqlEmailLogRepository(db),
        meeting_repo=SqlMeetingRepository(db),
        summary_repo=SqlSummaryRepository(db),
    )


MeetingServiceDep = Annotated[MeetingService, Depends(get_meeting_service)]
TranscriptionServiceDep = Annotated[TranscriptionService, Depends(get_transcription_service)]
SummaryServiceDep = Annotated[SummaryService, Depends(get_summary_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]
