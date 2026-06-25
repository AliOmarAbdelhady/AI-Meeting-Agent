"""Abstract base classes for repositories and external service providers."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from uuid import UUID

from meeting_agent.core.domain_models import (
    EmailLog,
    Meeting,
    Summary,
    Task,
    Transcript,
    TranscriptSegment,
)


# ── Repository Interfaces ──────────────────────────────────────────────────

class MeetingRepository(ABC):
    @abstractmethod
    async def create(self, meeting: Meeting) -> Meeting: ...

    @abstractmethod
    async def get_by_id(self, meeting_id: UUID) -> Optional[Meeting]: ...

    @abstractmethod
    async def list_all(
        self,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Meeting]: ...

    @abstractmethod
    async def update(self, meeting: Meeting) -> Meeting: ...

    @abstractmethod
    async def delete(self, meeting_id: UUID) -> bool: ...

    @abstractmethod
    async def get_upcoming(self, within_minutes: int = 5) -> list[Meeting]: ...


class TranscriptRepository(ABC):
    @abstractmethod
    async def create(self, transcript: Transcript) -> Transcript: ...

    @abstractmethod
    async def get_by_meeting_id(self, meeting_id: UUID) -> Optional[Transcript]: ...

    @abstractmethod
    async def get_by_id(self, transcript_id: UUID) -> Optional[Transcript]: ...

    @abstractmethod
    async def add_segment(self, segment: TranscriptSegment) -> TranscriptSegment: ...


class SummaryRepository(ABC):
    @abstractmethod
    async def create(self, summary: Summary) -> Summary: ...

    @abstractmethod
    async def get_by_meeting_id(self, meeting_id: UUID) -> Optional[Summary]: ...

    @abstractmethod
    async def get_by_id(self, summary_id: UUID) -> Optional[Summary]: ...

    @abstractmethod
    async def update(self, summary: Summary) -> Summary: ...


class TaskRepository(ABC):
    @abstractmethod
    async def create(self, task: Task) -> Task: ...

    @abstractmethod
    async def create_batch(self, tasks: list[Task]) -> list[Task]: ...

    @abstractmethod
    async def get_by_id(self, task_id: UUID) -> Optional[Task]: ...

    @abstractmethod
    async def get_by_meeting_id(self, meeting_id: UUID) -> list[Task]: ...

    @abstractmethod
    async def list_all(
        self,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Task]: ...

    @abstractmethod
    async def update(self, task: Task) -> Task: ...

    @abstractmethod
    async def delete(self, task_id: UUID) -> bool: ...


class EmailLogRepository(ABC):
    @abstractmethod
    async def create(self, email_log: EmailLog) -> EmailLog: ...

    @abstractmethod
    async def get_by_meeting_id(self, meeting_id: UUID) -> list[EmailLog]: ...


# ── Service Provider Interfaces ────────────────────────────────────────────

class MeetingBot(ABC):
    """Abstract interface for a meeting bot."""

    @abstractmethod
    async def join(self, meeting_url: str, display_name: str = "Meeting Agent") -> None:
        """Join a meeting at the given URL."""
        ...

    @abstractmethod
    async def leave(self) -> None:
        """Leave the current meeting."""
        ...

    @abstractmethod
    async def get_live_captions(self) -> AsyncGenerator[str, None]:
        """Yield live caption text as it appears."""
        ...

    @abstractmethod
    async def is_in_meeting(self) -> bool:
        """Check if the bot is currently in a meeting."""
        ...

    @abstractmethod
    async def get_participants(self) -> list[str]:
        """Get the list of current participants."""
        ...


class AudioRecorder(ABC):
    """Abstract interface for audio recording."""

    @abstractmethod
    async def start_recording(self, output_filename: str) -> None: ...

    @abstractmethod
    async def stop_recording(self) -> str: ...

    @abstractmethod
    async def get_duration(self) -> float: ...


class TranscriptionEngine(ABC):
    """Abstract interface for speech-to-text engines."""

    @abstractmethod
    async def transcribe_file(self, audio_path: str) -> Transcript: ...

    @abstractmethod
    async def transcribe_chunk(self, audio_bytes: bytes) -> list[TranscriptSegment]: ...


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str: ...

    @abstractmethod
    async def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict: ...


class EmailProvider(ABC):
    """Abstract interface for email providers."""

    @abstractmethod
    async def send_email(
        self,
        to: list[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> str:
        """Send an email and return the provider message ID."""
        ...
