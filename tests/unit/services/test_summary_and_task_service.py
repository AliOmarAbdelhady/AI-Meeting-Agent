"""Unit tests for SummaryService and TaskService."""

import json
from uuid import uuid4

import pytest

from meeting_agent.core.exceptions import SummaryNotFoundError, TaskNotFoundError, LLMError
from meeting_agent.services.summary_service import SummaryService
from meeting_agent.services.task_service import TaskService


# ── Mock Repos ────────────────────────────────────────────────────────────────


class MockSummaryRepo:
    def __init__(self):
        self._store = {}

    async def create(self, **kwargs):
        record = {"id": str(uuid4()), **kwargs}
        self._store[record["id"]] = record
        return record

    async def get_by_id(self, summary_id):
        return self._store.get(summary_id)

    async def get_by_meeting_id(self, meeting_id):
        for s in self._store.values():
            if s["meeting_id"] == meeting_id:
                return s
        return None

    async def update_fields(self, summary_id, **fields):
        record = self._store.get(summary_id)
        if record:
            record.update(fields)
        return record


class MockTranscriptRepo:
    def __init__(self, text="This is a test transcript about project planning."):
        self._text = text

    async def get_by_meeting_id(self, meeting_id):
        return {
            "id": str(uuid4()),
            "meeting_id": meeting_id,
            "full_text": self._text,
            "language": "en",
            "duration_seconds": 60.0,
            "word_count": len(self._text.split()),
        }


class MockTaskRepo:
    def __init__(self):
        self._store = {}

    async def create(self, **kwargs):
        record = {"id": str(uuid4()), "status": "pending", "priority": "medium", **kwargs}
        self._store[record["id"]] = record
        return record

    async def get_by_id(self, task_id):
        return self._store.get(task_id)

    async def get_by_meeting_id(self, meeting_id):
        return [t for t in self._store.values() if t.get("meeting_id") == meeting_id]

    async def list_all(self, **kwargs):
        items = list(self._store.values())
        return items, len(items)

    async def update_fields(self, task_id, **fields):
        record = self._store.get(task_id)
        if record:
            record.update(fields)
        return record

    async def delete(self, task_id):
        return self._store.pop(task_id, None) is not None


class MockLLM:
    """Mock LLM that returns predefined JSON responses."""

    def __init__(self, response=None):
        self.model_name = "mock-llm"
        self._response = response or {
            "summary_text": "Team discussed project timeline and deliverables.",
            "key_points": ["Timeline extended by 2 weeks", "New feature prioritized"],
            "decisions": ["Approve new timeline", "Assign backend work to Alice"],
            "action_items": ["Update project plan", "Schedule follow-up"],
        }

    async def generate(self, prompt, system_prompt=None):
        return "Generated text response"

    async def generate_json(self, prompt, system_prompt=None):
        return self._response


# ── SummaryService Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSummaryService:
    async def test_generate_summary(self):
        summary_repo = MockSummaryRepo()
        transcript_repo = MockTranscriptRepo()
        llm = MockLLM()
        service = SummaryService(transcript_repo, summary_repo, llm)

        meeting_id = str(uuid4())
        result = await service.generate_summary(meeting_id)

        assert result["summary_text"] == "Team discussed project timeline and deliverables."
        assert len(result["key_points"]) == 2
        assert len(result["decisions"]) == 2
        assert result["model_used"] == "mock-llm"

    async def test_generate_summary_no_provider(self):
        summary_repo = MockSummaryRepo()
        transcript_repo = MockTranscriptRepo()
        service = SummaryService(transcript_repo, summary_repo, llm_provider=None)

        with pytest.raises(LLMError, match="LLM provider not configured"):
            await service.generate_summary(str(uuid4()))

    async def test_get_summary_by_id(self):
        summary_repo = MockSummaryRepo()
        transcript_repo = MockTranscriptRepo()
        llm = MockLLM()
        service = SummaryService(transcript_repo, summary_repo, llm)

        meeting_id = str(uuid4())
        created = await service.generate_summary(meeting_id)
        result = await service.get_summary_by_id(created["id"])

        assert result["id"] == created["id"]

    async def test_get_summary_not_found(self):
        summary_repo = MockSummaryRepo()
        service = SummaryService(MockTranscriptRepo(), summary_repo)

        with pytest.raises(SummaryNotFoundError):
            await service.get_summary_by_id(str(uuid4()))

    async def test_update_summary(self):
        summary_repo = MockSummaryRepo()
        llm = MockLLM()
        service = SummaryService(MockTranscriptRepo(), summary_repo, llm)

        meeting_id = str(uuid4())
        created = await service.generate_summary(meeting_id)

        class MockBody:
            summary_text = "Updated summary"
            key_points = None
            decisions = None
            action_items = None

        result = await service.update_summary(created["id"], MockBody())
        assert result["summary_text"] == "Updated summary"


# ── TaskService Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTaskService:
    async def test_extract_tasks(self):
        task_repo = MockTaskRepo()
        summary_repo = MockSummaryRepo()
        llm = MockLLM(response=[
            {"title": "Update docs", "description": "Update API documentation", "priority": "high"},
            {"title": "Fix bug #42", "assignee_name": "Bob", "priority": "medium"},
        ])
        service = TaskService(task_repo, summary_repo, llm)

        # Create a summary first
        summary = await summary_repo.create(
            meeting_id=str(uuid4()),
            summary_text="Discuss bugs and docs",
            key_points=[],
            decisions=[],
            action_items=[],
            model_used="test",
        )

        tasks = await service.extract_tasks(meeting_id=str(uuid4()), summary_id=summary["id"])

        assert len(tasks) == 2
        assert tasks[0]["title"] == "Update docs"
        assert tasks[1]["title"] == "Fix bug #42"

    async def test_list_tasks(self):
        task_repo = MockTaskRepo()
        service = TaskService(task_repo, MockSummaryRepo())

        meeting_id = str(uuid4())
        await task_repo.create(meeting_id=meeting_id, title="Task 1")
        await task_repo.create(meeting_id=meeting_id, title="Task 2")

        result = await service.list_tasks()

        assert result["total"] == 2

    async def test_update_task(self):
        task_repo = MockTaskRepo()
        service = TaskService(task_repo, MockSummaryRepo())

        created = await task_repo.create(meeting_id=str(uuid4()), title="Original")

        class MockBody:
            title = "Updated"
            description = None
            assignee_email = None
            assignee_name = None
            due_date = None
            priority = None
            status = None

        result = await service.update_task(created["id"], MockBody())
        assert result["title"] == "Updated"

    async def test_delete_task(self):
        task_repo = MockTaskRepo()
        service = TaskService(task_repo, MockSummaryRepo())

        created = await task_repo.create(meeting_id=str(uuid4()), title="To delete")
        await service.delete_task(created["id"])

    async def test_task_not_found(self):
        task_repo = MockTaskRepo()
        service = TaskService(task_repo, MockSummaryRepo())

        with pytest.raises(TaskNotFoundError):
            await service.get_task(str(uuid4()))
