"""Business logic for transcription retrieval and export."""

import logging
from typing import Optional

from meeting_agent.core.enums import TranscriptExportFormat
from meeting_agent.core.exceptions import TranscriptionError
from meeting_agent.infrastructure.database.repositories.meeting_repo import SqlMeetingRepository
from meeting_agent.infrastructure.database.repositories.transcript_repo import SqlTranscriptRepository

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Manages transcript retrieval, formatting, and export."""

    def __init__(
        self,
        meeting_repo: SqlMeetingRepository,
        transcript_repo: SqlTranscriptRepository,
    ):
        self.meeting_repo = meeting_repo
        self.transcript_repo = transcript_repo

    async def get_transcript_by_id(self, transcript_id: str) -> Optional[dict]:
        """Get a transcript by its ID with segments."""
        return await self.transcript_repo.get_by_id(transcript_id)

    async def get_transcript_by_meeting(self, meeting_id: str) -> Optional[dict]:
        """Get the transcript for a specific meeting."""
        return await self.transcript_repo.get_by_meeting_id(meeting_id)

    async def export_transcript(self, transcript_id: str, format: str) -> dict:
        """Export a transcript in the specified format (txt, srt, vtt)."""
        transcript = await self.transcript_repo.get_by_id(transcript_id)
        if not transcript:
            return None

        format_enum = TranscriptExportFormat(format.lower())
        segments = transcript.get("segments", [])

        if format_enum == TranscriptExportFormat.TXT:
            content = self._export_txt(transcript, segments)
        elif format_enum == TranscriptExportFormat.SRT:
            content = self._export_srt(segments)
        elif format_enum == TranscriptExportFormat.VTT:
            content = self._export_vtt(segments)
        else:
            raise TranscriptionError(f"Unsupported export format: {format}")

        meeting_id = transcript["meeting_id"][:8]
        filename = f"transcript_{meeting_id}.{format_enum.value}"

        return {
            "content": content,
            "format": format_enum.value,
            "filename": filename,
        }

    @staticmethod
    def _export_txt(transcript: dict, segments: list[dict]) -> str:
        """Export as plain text with optional speaker labels."""
        if not segments:
            return transcript.get("full_text", "")

        lines = []
        for seg in segments:
            speaker = seg.get("speaker")
            text = seg.get("text", "").strip()
            if speaker:
                lines.append(f"[{speaker}]: {text}")
            else:
                lines.append(text)
        return "\n\n".join(lines)

    @staticmethod
    def _export_srt(segments: list[dict]) -> str:
        """Export as SubRip (.srt) subtitle format."""
        if not segments:
            return ""

        entries = []
        for i, seg in enumerate(segments, 1):
            start = TranscriptionService._seconds_to_srt_time(seg.get("start_time", 0))
            end = TranscriptionService._seconds_to_srt_time(seg.get("end_time", 0))
            text = seg.get("text", "").strip()
            entries.append(f"{i}\n{start} --> {end}\n{text}\n")
        return "\n".join(entries)

    @staticmethod
    def _export_vtt(segments: list[dict]) -> str:
        """Export as WebVTT (.vtt) subtitle format."""
        if not segments:
            return "WEBVTT\n"

        lines = ["WEBVTT\n"]
        for seg in segments:
            start = TranscriptionService._seconds_to_vtt_time(seg.get("start_time", 0))
            end = TranscriptionService._seconds_to_vtt_time(seg.get("end_time", 0))
            text = seg.get("text", "").strip()
            speaker = seg.get("speaker")
            if speaker:
                lines.append(f"\n{speaker}\n{start} --> {end}\n<v {speaker}>{text}\n")
            else:
                lines.append(f"\n{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """Convert seconds to SRT timestamp format: HH:MM:SS,mmm."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    @staticmethod
    def _seconds_to_vtt_time(seconds: float) -> str:
        """Convert seconds to WebVTT timestamp format: HH:MM:SS.mmm."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
