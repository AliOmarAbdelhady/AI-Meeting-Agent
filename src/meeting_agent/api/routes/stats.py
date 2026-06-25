"""Dashboard stats and read-only system info endpoints.

Kept on a separate router so the paths never collide with ``/meetings/{meeting_id}``
on the meetings router.
"""

from fastapi import APIRouter

from meeting_agent.api.deps import MeetingServiceDep, TaskServiceDep
from meeting_agent.core.config import settings

router = APIRouter()


@router.get("/stats")
async def get_stats(meeting_service: MeetingServiceDep, task_service: TaskServiceDep):
    """Aggregate counts for the dashboard (meetings + tasks grouped by status)."""
    meeting_counts = await meeting_service.get_status_counts()
    task_counts = await task_service.get_status_counts()
    return {
        "meetings": meeting_counts,
        "meetings_total": sum(meeting_counts.values()),
        "tasks": task_counts,
        "tasks_total": sum(task_counts.values()),
    }


@router.get("/settings/info")
async def get_settings_info():
    """Return non-secret effective configuration + provider availability (read-only)."""
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "log_level": settings.log_level,
        "openai_model": settings.openai_model,
        "whisper_model_size": settings.whisper_model_size,
        "whisper_device": settings.whisper_device,
        "email_provider": settings.email_provider,
        "email_from_address": settings.email_from_address,
        "scheduler_enabled": settings.scheduler_enabled,
        "bot_headless": settings.bot_headless,
        # Availability flags — booleans only, never the secret values themselves.
        "openai_configured": bool(settings.get_openai_api_key()),
        "sendgrid_configured": bool(settings.get_sendgrid_api_key()),
        "smtp_configured": bool(settings.smtp_host and settings.get_smtp_password()),
    }
