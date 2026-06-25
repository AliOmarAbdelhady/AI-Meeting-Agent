"""SQLAlchemy implementation of TaskRepository."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession


class SqlTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        meeting_id: str,
        title: str,
        description: Optional[str] = None,
        assignee_email: Optional[str] = None,
        assignee_name: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: str = "medium",
        source_summary_id: Optional[str] = None,
    ) -> dict:
        from meeting_agent.infrastructure.database.models import TaskModel
        model = TaskModel(
            id=str(uuid4()),
            meeting_id=meeting_id,
            title=title,
            description=description,
            assignee_email=assignee_email,
            assignee_name=assignee_name,
            due_date=due_date,
            priority=priority,
            source_summary_id=source_summary_id,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_dict(model)

    async def create_batch(self, tasks: list[dict]) -> list[dict]:
        from meeting_agent.infrastructure.database.models import TaskModel
        models = []
        for t in tasks:
            model = TaskModel(id=str(uuid4()), **t)
            self.session.add(model)
            models.append(model)
        await self.session.flush()
        return [self._to_dict(m) for m in models]

    async def get_by_id(self, task_id: str) -> Optional[dict]:
        from meeting_agent.infrastructure.database.models import TaskModel
        result = await self.session.execute(
            select(TaskModel).where(TaskModel.id == task_id)
        )
        model = result.scalar_one_or_none()
        return self._to_dict(model) if model else None

    async def get_by_meeting_id(self, meeting_id: str) -> list[dict]:
        from meeting_agent.infrastructure.database.models import TaskModel
        result = await self.session.execute(
            select(TaskModel).where(TaskModel.meeting_id == meeting_id).order_by(TaskModel.created_at)
        )
        return [self._to_dict(m) for m in result.scalars().all()]

    async def count_by_status(self) -> dict[str, int]:
        """Return a mapping of task status -> count."""
        from meeting_agent.infrastructure.database.models import TaskModel
        result = await self.session.execute(
            select(TaskModel.status, func.count()).group_by(TaskModel.status)
        )
        return {status: count for status, count in result.all()}

    async def list_all(
        self,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        from meeting_agent.infrastructure.database.models import TaskModel
        query = select(TaskModel)
        count_query = select(func.count()).select_from(TaskModel)

        if status:
            query = query.where(TaskModel.status == status)
            count_query = count_query.where(TaskModel.status == status)
        if assignee:
            query = query.where(TaskModel.assignee_email == assignee)
            count_query = count_query.where(TaskModel.assignee_email == assignee)

        total = (await self.session.execute(count_query)).scalar() or 0
        result = await self.session.execute(
            query.order_by(TaskModel.created_at.desc()).offset(offset).limit(limit)
        )
        return [self._to_dict(m) for m in result.scalars().all()], total

    async def update_fields(self, task_id: str, **fields) -> Optional[dict]:
        from meeting_agent.infrastructure.database.models import TaskModel
        fields["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(TaskModel).where(TaskModel.id == task_id).values(**fields)
        )
        return await self.get_by_id(task_id)

    async def delete(self, task_id: str) -> bool:
        from meeting_agent.infrastructure.database.models import TaskModel
        result = await self.session.execute(
            delete(TaskModel).where(TaskModel.id == task_id)
        )
        return result.rowcount > 0

    @staticmethod
    def _to_dict(model) -> dict:
        return {
            "id": model.id,
            "meeting_id": model.meeting_id,
            "title": model.title,
            "description": model.description,
            "assignee_email": model.assignee_email,
            "assignee_name": model.assignee_name,
            "due_date": model.due_date,
            "priority": model.priority,
            "status": model.status,
            "source_summary_id": model.source_summary_id,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }
