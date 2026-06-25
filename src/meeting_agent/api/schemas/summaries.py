"""Pydantic request/response schemas for summaries."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    """Response schema for a meeting summary."""
    id: str
    meeting_id: str
    summary_text: str
    key_points: list[str] = []
    decisions: list[str] = []
    action_items: list[str] = []
    model_used: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SummaryUpdateRequest(BaseModel):
    """Request body for editing a summary."""
    summary_text: Optional[str] = None
    key_points: Optional[list[str]] = None
    decisions: Optional[list[str]] = None
    action_items: Optional[list[str]] = None
