"""Meeting API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from meeting_agent.api.deps import (
    EmailServiceDep,
    MeetingServiceDep,
    SummaryServiceDep,
    TaskServiceDep,
    TranscriptionServiceDep,
)
from meeting_agent.api.schemas.meetings import MeetingCreate, MeetingListResponse, MeetingResponse, MeetingUpdate
from meeting_agent.api.schemas.email import EmailLogResponse, SendEmailRequest
from meeting_agent.api.schemas.summaries import SummaryResponse
from meeting_agent.api.schemas.tasks import TaskResponse
from meeting_agent.api.schemas.transcripts import TranscriptResponse
from meeting_agent.core.exceptions import MeetingNotFoundError

router = APIRouter()


async def _ensure_meeting(service: MeetingServiceDep, meeting_id: str) -> None:
    """Return 404 if the meeting does not exist.

    ``MeetingService.get_meeting`` raises ``MeetingNotFoundError`` (mapped to HTTP 400
    by the global handler); this helper converts that into a clean 404 for nested routes.
    """
    try:
        await service.get_meeting(meeting_id)
    except MeetingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found") from exc


@router.post("", response_model=MeetingResponse, status_code=201)
async def create_meeting(body: MeetingCreate, service: MeetingServiceDep):
    """Schedule a new meeting."""
    meeting = await service.create_meeting(body)
    return meeting


@router.get("", response_model=MeetingListResponse)
async def list_meetings(
    service: MeetingServiceDep,
    status: Optional[str] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List all meetings with optional filters."""
    return await service.list_meetings(status=status, platform=platform, page=page, page_size=page_size)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: str, service: MeetingServiceDep):
    """Get meeting details by ID."""
    meeting = await service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
    return meeting


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(meeting_id: str, body: MeetingUpdate, service: MeetingServiceDep):
    """Update meeting metadata."""
    return await service.update_meeting(meeting_id, body)


@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(meeting_id: str, service: MeetingServiceDep):
    """Cancel/delete a meeting."""
    await service.delete_meeting(meeting_id)


@router.post("/{meeting_id}/start", response_model=MeetingResponse)
async def start_meeting(meeting_id: str, service: MeetingServiceDep):
    """Trigger the bot to join a meeting."""
    return await service.start_meeting(meeting_id)


@router.post("/{meeting_id}/stop", response_model=MeetingResponse)
async def stop_meeting(meeting_id: str, service: MeetingServiceDep):
    """Stop meeting recording and trigger post-processing."""
    return await service.stop_meeting(meeting_id)


@router.get("/{meeting_id}/status")
async def get_meeting_status(meeting_id: str, service: MeetingServiceDep):
    """Get the current status of a meeting."""
    meeting = await service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
    return {"meeting_id": meeting_id, "status": meeting["status"]}


@router.post("/{meeting_id}/send-email", response_model=EmailLogResponse)
async def send_meeting_email(meeting_id: str, body: SendEmailRequest, email_service: EmailServiceDep):
    """Send summary email to participants."""
    return await email_service.send_summary_email(
        meeting_id=meeting_id,
        recipients=body.recipients,
        custom_message=body.custom_message,
    )


@router.get("/{meeting_id}/emails", response_model=list[EmailLogResponse])
async def get_meeting_emails(meeting_id: str, email_service: EmailServiceDep):
    """Get email history for a meeting."""
    return await email_service.get_email_history(meeting_id)


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def get_meeting_transcript(
    meeting_id: str,
    service: MeetingServiceDep,
    transcription_service: TranscriptionServiceDep,
):
    """Get the transcript for a meeting (with segments)."""
    await _ensure_meeting(service, meeting_id)
    transcript = await transcription_service.get_transcript_by_meeting(meeting_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not ready yet")
    return transcript


@router.get("/{meeting_id}/summary", response_model=SummaryResponse)
async def get_meeting_summary(
    meeting_id: str,
    service: MeetingServiceDep,
    summary_service: SummaryServiceDep,
):
    """Get the AI summary for a meeting."""
    await _ensure_meeting(service, meeting_id)
    summary = await summary_service.get_summary_by_meeting(meeting_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not ready yet")
    return summary


@router.get("/{meeting_id}/tasks", response_model=list[TaskResponse])
async def get_meeting_tasks(
    meeting_id: str,
    service: MeetingServiceDep,
    task_service: TaskServiceDep,
):
    """Get all action items extracted for a meeting."""
    await _ensure_meeting(service, meeting_id)
    return await task_service.get_tasks_by_meeting(meeting_id)
