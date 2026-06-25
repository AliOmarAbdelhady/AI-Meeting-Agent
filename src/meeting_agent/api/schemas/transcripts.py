"""Pydantic request/response schemas for transcripts."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TranscriptSegmentResponse(BaseModel):
    """A single segment of a transcript."""
    id: str
    text: str
    start_time: float
    end_time: float
    speaker: Optional[str] = None
    confidence: float = 0.0
    segment_index: int

    model_config = {"from_attributes": True}


class TranscriptResponse(BaseModel):
    """Full transcript response."""
    id: str
    meeting_id: str
    full_text: str
    language: str = "en"
    duration_seconds: float
    word_count: Optional[int] = None
    segments: list[TranscriptSegmentResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptExportResponse(BaseModel):
    """Exported transcript in a specific format."""
    content: str
    format: str
    filename: str
