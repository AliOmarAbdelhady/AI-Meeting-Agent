"""Task API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from meeting_agent.api.deps import TaskServiceDep
from meeting_agent.api.schemas.tasks import TaskListResponse, TaskResponse, TaskUpdateRequest

router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    service: TaskServiceDep,
    status: Optional[str] = Query(None, description="Filter by status"),
    assignee: Optional[str] = Query(None, description="Filter by assignee email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List all tasks with optional filters."""
    return await service.list_tasks(status=status, assignee=assignee, page=page, page_size=page_size)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, service: TaskServiceDep):
    """Get task details by ID."""
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, body: TaskUpdateRequest, service: TaskServiceDep):
    """Update a task (status, assignee, due date, etc.)."""
    return await service.update_task(task_id, body)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, service: TaskServiceDep):
    """Delete a task."""
    await service.delete_task(task_id)
