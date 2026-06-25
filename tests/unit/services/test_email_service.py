"""Unit tests for EmailService."""

from uuid import uuid4

import pytest

from meeting_agent.core.exceptions import EmailSendError
from meeting_agent.services.email_service import EmailService


class MockEmailLogRepo:
    def __init__(self):
        self._store = {}

    async def create(self, **kwargs):
        record = {"id": str(uuid4()), "status": "pending", **kwargs}
        self._store[record["id"]] = record
        return record

    async def mark_sent(self, email_id, provider_message_id=None):
        record = self._store.get(email_id)
        if record:
            record["status"] = "sent"
            record["provider_message_id"] = provider_message_id
        return record

    async def mark_failed(self, email_id, error_message):
        record = self._store.get(email_id)
        if record:
            record["status"] = "failed"
            record["error_message"] = error_message
        return record

    async def get_by_meeting_id(self, meeting_id):
        return [e for e in self._store.values() if e.get("meeting_id") == meeting_id]


class MockMeetingRepo:
    async def get_by_id(self, meeting_id):
        return {
            "id": meeting_id,
            "title": "Sprint Planning",
            "participants": ["alice@example.com"],
        }


class MockSummaryRepo:
    async def get_by_meeting_id(self, meeting_id):
        return {
            "id": str(uuid4()),
            "meeting_id": meeting_id,
            "summary_text": "The team discussed the sprint goals.",
            "key_points": ["Goal 1", "Goal 2"],
            "decisions": ["Decision A"],
            "action_items": ["Action 1", "Action 2"],
        }


class MockTaskRepo:
    async def get_by_meeting_id(self, meeting_id):
        return [
            {"title": "Task 1", "description": "Do thing", "assignee_name": "Alice", "assignee_email": "alice@test.com", "due_date": None},
        ]


class MockEmailProvider:
    async def send_email(self, to, subject, html_body, text_body=None):
        return "msg-123"


class FailingEmailProvider:
    async def send_email(self, to, subject, html_body, text_body=None):
        raise Exception("SMTP connection refused")


@pytest.mark.asyncio
class TestEmailService:
    async def test_send_summary_email_success(self):
        service = EmailService(
            email_log_repo=MockEmailLogRepo(),
            meeting_repo=MockMeetingRepo(),
            summary_repo=MockSummaryRepo(),
            task_repo=MockTaskRepo(),
            email_provider=MockEmailProvider(),
        )

        meeting_id = str(uuid4())
        result = await service.send_summary_email(
            meeting_id=meeting_id,
            recipients=["alice@example.com"],
        )

        assert result["status"] == "sent"
        assert result["provider_message_id"] == "msg-123"

    async def test_send_summary_email_with_custom_message(self):
        service = EmailService(
            email_log_repo=MockEmailLogRepo(),
            meeting_repo=MockMeetingRepo(),
            summary_repo=MockSummaryRepo(),
            task_repo=MockTaskRepo(),
            email_provider=MockEmailProvider(),
        )

        meeting_id = str(uuid4())
        result = await service.send_summary_email(
            meeting_id=meeting_id,
            recipients=["bob@example.com"],
            custom_message="Please review before Friday",
        )

        assert result["status"] == "sent"

    async def test_send_email_failure(self):
        log_repo = MockEmailLogRepo()
        service = EmailService(
            email_log_repo=log_repo,
            meeting_repo=MockMeetingRepo(),
            summary_repo=MockSummaryRepo(),
            task_repo=MockTaskRepo(),
            email_provider=FailingEmailProvider(),
        )

        meeting_id = str(uuid4())
        with pytest.raises(EmailSendError):
            await service.send_summary_email(
                meeting_id=meeting_id,
                recipients=["alice@example.com"],
            )

    async def test_send_email_no_provider(self):
        service = EmailService(
            email_log_repo=MockEmailLogRepo(),
            meeting_repo=MockMeetingRepo(),
            summary_repo=MockSummaryRepo(),
            email_provider=None,
        )

        with pytest.raises(EmailSendError, match="No email provider"):
            await service.send_summary_email(
                meeting_id=str(uuid4()),
                recipients=["alice@example.com"],
            )

    async def test_get_email_history(self):
        log_repo = MockEmailLogRepo()
        service = EmailService(
            email_log_repo=log_repo,
            meeting_repo=MockMeetingRepo(),
            summary_repo=MockSummaryRepo(),
            email_provider=MockEmailProvider(),
        )

        meeting_id = str(uuid4())
        await service.send_summary_email(meeting_id, ["alice@example.com"])

        history = await service.get_email_history(meeting_id)
        assert len(history) == 1
