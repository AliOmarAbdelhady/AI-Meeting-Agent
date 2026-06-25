"""Pure domain entities — no ORM or external framework dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from meeting_agent.core.enums import (
    EmailStatus,
    MeetingPlatform,
    MeetingStatus,
    TaskPriority,
    TaskStatus,
)


@dataclass
class Meeting:
    """Represents a scheduled or completed meeting."""
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    platform: MeetingPlatform = MeetingPlatform.OTHER
    meeting_url: str = ""
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: MeetingStatus = MeetingStatus.SCHEDULED
    duration_seconds: Optional[int] = None
    participants: list[str] = field(default_factory=list)
    raw_audio_path: Optional[str] = None
    calendar_event_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TranscriptSegment:
    """A single timestamped segment of a transcript."""
    id: UUID = field(default_factory=uuid4)
    transcript_id: UUID = field(default_factory=uuid4)
    meeting_id: UUID = field(default_factory=uuid4)
    text: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    speaker: Optional[str] = None
    confidence: float = 0.0
    segment_index: int = 0


@dataclass
class Transcript:
    """Full transcript for a meeting with all segments."""
    id: UUID = field(default_factory=uuid4)
    meeting_id: UUID = field(default_factory=uuid4)
    segments: list[TranscriptSegment] = field(default_factory=list)
    full_text: str = ""
    language: str = "en"
    duration_seconds: float = 0.0
    word_count: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Summary:
    """LLM-generated meeting summary."""
    id: UUID = field(default_factory=uuid4)
    meeting_id: UUID = field(default_factory=uuid4)
    summary_text: str = ""
    key_points: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    model_used: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Task:
    """An action item extracted from a meeting."""
    id: UUID = field(default_factory=uuid4)
    meeting_id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: Optional[str] = None
    assignee_email: Optional[str] = None
    assignee_name: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    source_summary_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EmailLog:
    """Log entry for an email sent regarding a meeting."""
    id: UUID = field(default_factory=uuid4)
    meeting_id: UUID = field(default_factory=uuid4)
    recipients: list[str] = field(default_factory=list)
    subject: str = ""
    status: EmailStatus = EmailStatus.PENDING
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
