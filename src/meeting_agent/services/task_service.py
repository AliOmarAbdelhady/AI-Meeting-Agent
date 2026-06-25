"""Business logic for task extraction and management."""

import json
import logging
from datetime import datetime
from typing import Optional

from meeting_agent.core.enums import TaskPriority, TaskStatus
from meeting_agent.core.exceptions import LLMError, TaskNotFoundError
from meeting_agent.infrastructure.database.repositories.summary_repo import SqlSummaryRepository
from meeting_agent.infrastructure.database.repositories.task_repo import SqlTaskRepository

logger = logging.getLogger(__name__)

TASK_EXTRACTION_PROMPT = """You are a project management assistant. Given a meeting summary,
extract action items as tasks. Return a JSON array where each task has:
- "title": Short task title (required)
- "description": Detailed description (optional)
- "assignee_email": Email if mentioned (optional)
- "assignee_name": Name if mentioned (optional)
- "priority": "high", "medium", or "low" (default: "medium")
- "due_date": ISO 8601 date if mentioned (optional)

Return ONLY a valid JSON array. No markdown, no explanation."""


class TaskService:
    """Extracts tasks from summaries and manages task CRUD."""

    def __init__(
        self,
        task_repo: SqlTaskRepository,
        summary_repo: SqlSummaryRepository,
        llm_provider=None,
    ):
        self.task_repo = task_repo
        self.summary_repo = summary_repo
        self.llm_provider = llm_provider

    async def extract_tasks(self, meeting_id: str, summary_id: str) -> list[dict]:
        """Extract tasks from a summary using LLM."""
        summary = await self.summary_repo.get_by_id(summary_id)
        if not summary:
            raise TaskNotFoundError(summary_id)

        if not self.llm_provider:
            raise LLMError("LLM provider not configured")

        prompt = (
            f"Meeting Summary:\n{summary['summary_text']}\n\n"
            f"Key Points: {json.dumps(summary.get('key_points', []))}\n"
            f"Decisions: {json.dumps(summary.get('decisions', []))}\n"
            f"Action Items: {json.dumps(summary.get('action_items', []))}"
        )

        try:
            raw = await self.llm_provider.generate_json(
                prompt=prompt,
                system_prompt=TASK_EXTRACTION_PROMPT,
            )
        except Exception as e:
            raise LLMError(f"Task extraction failed: {e}") from e

        if isinstance(raw, str):
            raw = json.loads(raw)

        tasks_data = raw if isinstance(raw, list) else [raw]
        created = []
        for t in tasks_data:
            task = await self.task_repo.create(
                meeting_id=meeting_id,
                title=t.get("title", "Untitled task"),
                description=t.get("description"),
                assignee_email=t.get("assignee_email"),
                assignee_name=t.get("assignee_name"),
                due_date=t.get("due_date"),
                priority=t.get("priority", "medium"),
                source_summary_id=summary_id,
            )
            created.append(task)

        logger.info("Extracted %d tasks for meeting %s", len(created), meeting_id)
        return created

    async def get_task(self, task_id: str) -> Optional[dict]:
        """Get a task by ID."""
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        return task

    async def list_tasks(
        self,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """List tasks with optional filters and pagination."""
        offset = (page - 1) * page_size
        items, total = await self.task_repo.list_all(
            status=status,
            assignee=assignee,
            offset=offset,
            limit=page_size,
        )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_tasks_by_meeting(self, meeting_id: str) -> list[dict]:
        """Get all tasks belonging to a specific meeting."""
        return await self.task_repo.get_by_meeting_id(meeting_id)

    async def get_status_counts(self) -> dict[str, int]:
        """Return a mapping of task status -> count (for the dashboard)."""
        counts = await self.task_repo.count_by_status()
        # Ensure every known status is represented, even if zero.
        return {status.value: counts.get(status.value, 0) for status in TaskStatus}

    async def update_task(self, task_id: str, body) -> dict:
        """Update a task's fields."""
        existing = await self.task_repo.get_by_id(task_id)
        if not existing:
            raise TaskNotFoundError(task_id)

        fields = {}
        if body.title is not None:
            fields["title"] = body.title
        if body.description is not None:
            fields["description"] = body.description
        if body.assignee_email is not None:
            fields["assignee_email"] = body.assignee_email
        if body.assignee_name is not None:
            fields["assignee_name"] = body.assignee_name
        if body.due_date is not None:
            fields["due_date"] = body.due_date
        if body.priority is not None:
            fields["priority"] = body.priority.value if hasattr(body.priority, "value") else body.priority
        if body.status is not None:
            fields["status"] = body.status.value if hasattr(body.status, "value") else body.status

        if fields:
            return await self.task_repo.update_fields(task_id, **fields)
        return existing

    async def delete_task(self, task_id: str) -> None:
        """Delete a task."""
        existing = await self.task_repo.get_by_id(task_id)
        if not existing:
            raise TaskNotFoundError(task_id)
        await self.task_repo.delete(task_id)
        logger.info("Deleted task %s", task_id)
