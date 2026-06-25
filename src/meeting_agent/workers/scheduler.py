"""APScheduler-based scheduler for automatic meeting processing."""

import asyncio
import logging
from typing import Optional

from meeting_agent.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: Optional[object] = None


async def start_scheduler():
    """Initialize and start the APScheduler."""
    global _scheduler

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        _scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)

        # Job: Check for upcoming meetings
        _scheduler.add_job(
            check_upcoming_meetings,
            trigger=IntervalTrigger(seconds=settings.scheduler_check_interval_seconds),
            id="check_upcoming_meetings",
            name="Check for upcoming meetings",
            replace_existing=True,
        )

        _scheduler.start()
        logger.info(
            "Scheduler started (check interval: %ds)",
            settings.scheduler_check_interval_seconds,
        )
    except ImportError:
        logger.warning("apscheduler not installed — scheduler disabled")
    except Exception as e:
        logger.error("Failed to start scheduler: %s", e)
        raise


async def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler shut down")


async def check_upcoming_meetings():
    """Check for meetings about to start and trigger the processing pipeline."""
    logger.debug("Checking for upcoming meetings...")

    try:
        from meeting_agent.infrastructure.database.connection import async_session_factory
        from meeting_agent.infrastructure.database.repositories.meeting_repo import SqlMeetingRepository
        from meeting_agent.workers.pipeline import MeetingPipeline

        async with async_session_factory() as session:
            repo = SqlMeetingRepository(session)
            upcoming = await repo.get_upcoming(within_minutes=settings.scheduler_check_interval_seconds // 60 + 1)

            for meeting_data in upcoming:
                logger.info("Scheduler found upcoming meeting: %s (%s)", meeting_data["id"], meeting_data["title"])
                # Fire and forget — run pipeline in background
                asyncio.create_task(_run_pipeline(meeting_data["id"]))
                await session.commit()

    except Exception as e:
        logger.error("Error in check_upcoming_meetings: %s", e)


async def _run_pipeline(meeting_id: str):
    """Run the full meeting processing pipeline for a meeting."""
    try:
        from meeting_agent.workers.pipeline import MeetingPipeline
        pipeline = MeetingPipeline()
        await pipeline.process(meeting_id)
    except Exception as e:
        logger.error("Pipeline failed for meeting %s: %s", meeting_id, e)
