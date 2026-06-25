"""Pydantic request/response schemas for meetings."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from meeting_agent.core.enums import MeetingPlatform, MeetingStatus


class MeetingCreate(BaseModel):
    """Request body for creating a new meeting."""
    title: str = Field(..., min_length=1, max_length=500, description="Meeting title")
    platform: MeetingPlatform = Field(..., description="Meeting platform")
    meeting_url: str = Field(..., min_length=1, max_length=2048, description="Meeting join URL")
    scheduled_at: datetime = Field(..., description="Scheduled start time (ISO 8601)")
    participants: list[str] = Field(default_factory=list, description="List of participant emails")
    calendar_event_id: Optional[str] = Field(None, description="Google Calendar event ID")


class MeetingUpdate(BaseModel):
    """Request body for updating a meeting."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    scheduled_at: Optional[datetime] = None
    participants: Optional[list[str]] = None


class MeetingResponse(BaseModel):
    """Response schema for a meeting."""
    id: str
    title: str
    platform: str
    meeting_url: str
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str
    duration_seconds: Optional[int] = None
    participants: list[str] = []
    raw_audio_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MeetingListResponse(BaseModel):
    """Paginated list of meetings."""
    items: list[MeetingResponse]
    total: int
    page: int
    page_size: int
