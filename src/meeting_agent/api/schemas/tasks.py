"""Pydantic request/response schemas for tasks."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from meeting_agent.core.enums import TaskPriority, TaskStatus


class TaskResponse(BaseModel):
    """Response schema for a task."""
    id: str
    meeting_id: str
    title: str
    description: Optional[str] = None
    assignee_email: Optional[str] = None
    assignee_name: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str
    status: str
    source_summary_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskUpdateRequest(BaseModel):
    """Request body for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    assignee_email: Optional[str] = None
    assignee_name: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
