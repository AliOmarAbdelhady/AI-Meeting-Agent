"""Business logic for summary generation and management."""

import json
import logging
from typing import Optional

from meeting_agent.core.exceptions import LLMError, SummaryNotFoundError
from meeting_agent.infrastructure.database.repositories.summary_repo import SqlSummaryRepository
from meeting_agent.infrastructure.database.repositories.transcript_repo import SqlTranscriptRepository

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are a professional meeting assistant. Analyze the meeting transcript
and produce a JSON object with exactly these keys:
- "summary_text": A concise 3-5 paragraph summary of the meeting.
- "key_points": A list of the most important points discussed (max 10).
- "decisions": A list of decisions made during the meeting.
- "action_items": A list of action items with assignee if mentioned.

Return ONLY valid JSON. No markdown, no extra text."""


class SummaryService:
    """Generates summaries using LLM and manages summary CRUD."""

    def __init__(
        self,
        transcript_repo: SqlTranscriptRepository,
        summary_repo: SqlSummaryRepository,
        llm_provider=None,
    ):
        self.transcript_repo = transcript_repo
        self.summary_repo = summary_repo
        self.llm_provider = llm_provider

    async def generate_summary(self, meeting_id: str) -> dict:
        """Generate a summary from a meeting's transcript using LLM."""
        # 1. Get transcript
        transcript = await self.transcript_repo.get_by_meeting_id(meeting_id)
        if not transcript:
            raise SummaryNotFoundError(meeting_id)

        full_text = transcript.get("full_text", "")
        if not full_text.strip():
            raise LLMError("Transcript is empty — nothing to summarize")

        # 2. Call LLM
        if not self.llm_provider:
            raise LLMError("LLM provider not configured")

        prompt = f"Meeting Transcript:\n\n{full_text}"
        try:
            raw_response = await self.llm_provider.generate_json(
                prompt=prompt,
                system_prompt=SUMMARY_SYSTEM_PROMPT,
            )
        except Exception as e:
            raise LLMError(f"LLM call failed: {e}") from e

        # 3. Parse and validate response
        if isinstance(raw_response, str):
            try:
                raw_response = json.loads(raw_response)
            except json.JSONDecodeError:
                raise LLMError("LLM returned invalid JSON")

        summary_text = raw_response.get("summary_text", "")
        key_points = raw_response.get("key_points", [])
        decisions = raw_response.get("decisions", [])
        action_items = raw_response.get("action_items", [])

        # 4. Store summary
        summary = await self.summary_repo.create(
            meeting_id=meeting_id,
            summary_text=summary_text,
            key_points=key_points,
            decisions=decisions,
            action_items=action_items,
            model_used=self.llm_provider.model_name if hasattr(self.llm_provider, "model_name") else "unknown",
        )
        logger.info("Generated summary for meeting %s", meeting_id)
        return summary

    async def get_summary_by_id(self, summary_id: str) -> Optional[dict]:
        """Get a summary by its ID."""
        summary = await self.summary_repo.get_by_id(summary_id)
        if not summary:
            raise SummaryNotFoundError(summary_id)
        return summary

    async def get_summary_by_meeting(self, meeting_id: str) -> Optional[dict]:
        """Get the summary for a specific meeting."""
        return await self.summary_repo.get_by_meeting_id(meeting_id)

    async def update_summary(self, summary_id: str, body) -> dict:
        """Update a summary (manual corrections)."""
        existing = await self.summary_repo.get_by_id(summary_id)
        if not existing:
            raise SummaryNotFoundError(summary_id)

        fields = {}
        if body.summary_text is not None:
            fields["summary_text"] = body.summary_text
        if body.key_points is not None:
            fields["key_points"] = body.key_points
        if body.decisions is not None:
            fields["decisions"] = body.decisions
        if body.action_items is not None:
            fields["action_items"] = body.action_items

        if fields:
            return await self.summary_repo.update_fields(summary_id, **fields)
        return existing
