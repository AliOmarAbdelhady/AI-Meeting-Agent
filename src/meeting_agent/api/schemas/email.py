"""Pydantic request/response schemas for email."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SendEmailRequest(BaseModel):
    """Request body for sending a summary email."""
    recipients: list[str] = Field(..., min_length=1, description="List of recipient email addresses")
    custom_message: Optional[str] = Field(None, description="Optional custom message to include")


class EmailLogResponse(BaseModel):
    """Response schema for an email log entry."""
    id: str
    meeting_id: str
    recipients: list[str]
    subject: str
    status: str
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
