"""Full meeting processing pipeline: join → record → transcribe → summarize → tasks → email."""

import logging
from datetime import datetime
from uuid import uuid4

from meeting_agent.core.config import settings
from meeting_agent.core.enums import MeetingStatus

logger = logging.getLogger(__name__)


class MeetingPipeline:
    """Orchestrates the full meeting processing workflow.

    Flow: JOIN → RECORD → TRANSCRIBE → SUMMARIZE → EXTRACT TASKS → EMAIL
    """

    def __init__(self):
        self._meeting_repo = None
        self._transcript_repo = None
        self._summary_repo = None
        self._task_repo = None
        self._email_log_repo = None

    def _init_repos(self, session):
        """Initialize repositories with a database session."""
        from meeting_agent.infrastructure.database.repositories.meeting_repo import SqlMeetingRepository
        from meeting_agent.infrastructure.database.repositories.transcript_repo import SqlTranscriptRepository
        from meeting_agent.infrastructure.database.repositories.summary_repo import SqlSummaryRepository
        from meeting_agent.infrastructure.database.repositories.task_repo import SqlTaskRepository
        from meeting_agent.infrastructure.database.repositories.email_log_repo import SqlEmailLogRepository

        self._meeting_repo = SqlMeetingRepository(session)
        self._transcript_repo = SqlTranscriptRepository(session)
        self._summary_repo = SqlSummaryRepository(session)
        self._task_repo = SqlTaskRepository(session)
        self._email_log_repo = SqlEmailLogRepository(session)

    async def process(self, meeting_id: str) -> None:
        """Run the full processing pipeline for a meeting."""
        from meeting_agent.infrastructure.database.connection import async_session_factory

        async with async_session_factory() as session:
            self._init_repos(session)

            try:
                # Step 1: Join meeting
                await self._step_join(meeting_id)
                await session.commit()

                # Step 2: Record audio
                audio_path = await self._step_record(meeting_id)
                await session.commit()

                # Step 3: Transcribe
                transcript = await self._step_transcribe(meeting_id, audio_path)
                await session.commit()

                # Step 4: Summarize
                summary = await self._step_summarize(meeting_id)
                await session.commit()

                # Step 5: Extract tasks
                tasks = await self._step_extract_tasks(meeting_id, summary)
                await session.commit()

                # Step 6: Email participants
                await self._step_email(meeting_id)
                await session.commit()

                # Mark completed
                await self._meeting_repo.update_status(meeting_id, MeetingStatus.COMPLETED.value)
                await session.commit()
                logger.info("Pipeline completed for meeting %s", meeting_id)

            except Exception as e:
                await session.rollback()
                # Try to mark as failed
                try:
                    await self._meeting_repo.update_status(
                        meeting_id, MeetingStatus.FAILED.value, error_message=str(e)
                    )
                    await session.commit()
                except Exception:
                    pass
                logger.error("Pipeline failed for meeting %s: %s", meeting_id, e)
                raise

    async def _step_join(self, meeting_id: str) -> None:
        """Step 1: Bot joins the meeting."""
        meeting = await self._meeting_repo.get_by_id(meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        await self._meeting_repo.update_status(meeting_id, MeetingStatus.JOINING.value, started_at=datetime.utcnow())

        try:
            from meeting_agent.infrastructure.providers.meeting_bot import PlaywrightMeetingBot
            bot = PlaywrightMeetingBot()
            await bot.join(meeting["meeting_url"])
            await self._meeting_repo.update_status(meeting_id, MeetingStatus.IN_PROGRESS.value)
            logger.info("Pipeline [JOIN]: Bot joined meeting %s", meeting_id)
        except Exception as e:
            logger.error("Pipeline [JOIN]: Failed - %s", e)
            raise

    async def _step_record(self, meeting_id: str) -> str:
        """Step 2: Record audio during the meeting."""
        await self._meeting_repo.update_status(meeting_id, MeetingStatus.RECORDING.value)

        try:
            from meeting_agent.infrastructure.providers.audio_recorder import AudioRecorder
            recorder = AudioRecorder()
            filename = f"meeting_{meeting_id[:8]}_{uuid4().hex[:6]}.wav"
            await recorder.start_recording(filename)

            # Record for the meeting duration or until max duration
            # In production, this would be event-driven
            import asyncio
            record_seconds = min(settings.audio_max_duration_seconds, 3600)  # Default 1 hour max for auto
            await asyncio.sleep(record_seconds)

            audio_path = await recorder.stop_recording()
            await self._meeting_repo.update_status(
                meeting_id,
                MeetingStatus.TRANSCRIBING.value,
                raw_audio_path=audio_path,
            )
            logger.info("Pipeline [RECORD]: Audio saved → %s", audio_path)
            return audio_path
        except Exception as e:
            logger.error("Pipeline [RECORD]: Failed - %s", e)
            raise

    async def _step_transcribe(self, meeting_id: str, audio_path: str) -> dict:
        """Step 3: Transcribe the audio file."""
        try:
            from meeting_agent.infrastructure.providers.whisper_engine import WhisperEngine
            engine = WhisperEngine()
            result = await engine.transcribe_file(audio_path)

            # Store transcript
            transcript = await self._transcript_repo.create(
                meeting_id=meeting_id,
                full_text=result["full_text"],
                language=result["language"],
                duration_seconds=result["duration_seconds"],
                word_count=result["word_count"],
            )

            # Store segments
            for seg in result["segments"]:
                await self._transcript_repo._store_segment(
                    transcript_id=transcript["id"],
                    meeting_id=meeting_id,
                    **seg,
                )

            logger.info(
                "Pipeline [TRANSCRIBE]: %d words, %d segments",
                result["word_count"],
                len(result["segments"]),
            )
            return transcript
        except Exception as e:
            logger.error("Pipeline [TRANSCRIBE]: Failed - %s", e)
            raise

    async def _step_summarize(self, meeting_id: str) -> dict:
        """Step 4: Generate meeting summary using LLM."""
        await self._meeting_repo.update_status(meeting_id, MeetingStatus.SUMMARIZING.value)

        try:
            from meeting_agent.infrastructure.providers.llm_provider import OpenAILLMProvider
            from meeting_agent.services.summary_service import SummaryService

            llm = OpenAILLMProvider()
            service = SummaryService(
                transcript_repo=self._transcript_repo,
                summary_repo=self._summary_repo,
                llm_provider=llm,
            )
            summary = await service.generate_summary(meeting_id)
            logger.info("Pipeline [SUMMARIZE]: Summary generated")
            return summary
        except Exception as e:
            logger.error("Pipeline [SUMMARIZE]: Failed - %s", e)
            raise

    async def _step_extract_tasks(self, meeting_id: str, summary: dict) -> list[dict]:
        """Step 5: Extract action items as tasks."""
        try:
            from meeting_agent.infrastructure.providers.llm_provider import OpenAILLMProvider
            from meeting_agent.services.task_service import TaskService

            llm = OpenAILLMProvider()
            service = TaskService(
                task_repo=self._task_repo,
                summary_repo=self._summary_repo,
                llm_provider=llm,
            )
            tasks = await service.extract_tasks(meeting_id, summary["id"])
            logger.info("Pipeline [TASKS]: Extracted %d tasks", len(tasks))
            return tasks
        except Exception as e:
            logger.error("Pipeline [TASKS]: Failed - %s", e)
            raise

    async def _step_email(self, meeting_id: str) -> None:
        """Step 6: Email summary to participants."""
        try:
            meeting = await self._meeting_repo.get_by_id(meeting_id)
            participants = meeting.get("participants", [])

            if not participants:
                logger.info("Pipeline [EMAIL]: No participants — skipping email")
                return

            # Select email provider
            if settings.email_provider == "smtp":
                from meeting_agent.infrastructure.providers.email_smtp import SMTPEmailProvider
                provider = SMTPEmailProvider()
            else:
                from meeting_agent.infrastructure.providers.email_sendgrid import SendGridEmailProvider
                provider = SendGridEmailProvider()

            from meeting_agent.services.email_service import EmailService
            service = EmailService(
                email_log_repo=self._email_log_repo,
                meeting_repo=self._meeting_repo,
                summary_repo=self._summary_repo,
                task_repo=self._task_repo,
                email_provider=provider,
            )
            await service.send_summary_email(meeting_id, participants)
            logger.info("Pipeline [EMAIL]: Summary sent to %d participants", len(participants))
        except Exception as e:
            logger.error("Pipeline [EMAIL]: Failed - %s", e)
            raise
