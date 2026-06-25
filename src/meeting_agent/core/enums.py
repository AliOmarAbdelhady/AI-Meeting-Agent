from enum import Enum


class MeetingStatus(str, Enum):
    """Status of a meeting throughout its lifecycle."""
    SCHEDULED = "scheduled"
    JOINING = "joining"
    IN_PROGRESS = "in_progress"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MeetingPlatform(str, Enum):
    """Supported meeting platforms."""
    GOOGLE_MEET = "google_meet"
    ZOOM = "zoom"
    TEAMS = "teams"
    OTHER = "other"


class TaskPriority(str, Enum):
    """Priority levels for extracted tasks."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Status of an extracted task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EmailStatus(str, Enum):
    """Status of an email delivery."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class TranscriptExportFormat(str, Enum):
    """Supported transcript export formats."""
    TXT = "txt"
    SRT = "srt"
    VTT = "vtt"
