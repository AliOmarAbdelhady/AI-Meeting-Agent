"""Unit tests for TranscriptionService."""

from uuid import uuid4

import pytest

from meeting_agent.services.transcription_service import TranscriptionService


def _make_transcript_repo_with_data(segments=None, full_text="Hello world this is a test"):
    """Create a mock transcript repo that returns predefined data."""
    class MockTranscriptRepo:
        def __init__(self, data):
            self._data = data

        async def get_by_id(self, transcript_id):
            return self._data

        async def get_by_meeting_id(self, meeting_id):
            return self._data

    segments = segments or [
        {"text": "Hello world", "start_time": 0.0, "end_time": 2.0, "speaker": None, "segment_index": 0},
        {"text": "this is a test", "start_time": 2.0, "end_time": 4.5, "speaker": "Speaker 1", "segment_index": 1},
    ]
    data = {
        "id": str(uuid4()),
        "meeting_id": str(uuid4()),
        "full_text": full_text,
        "language": "en",
        "duration_seconds": 4.5,
        "word_count": len(full_text.split()),
        "segments": segments,
    }
    return MockTranscriptRepo(data)


def _make_meeting_repo():
    class MockMeetingRepo:
        pass
    return MockMeetingRepo()


@pytest.mark.asyncio
class TestTranscriptionExport:
    async def test_export_txt(self):
        repo = _make_transcript_repo_with_data()
        service = TranscriptionService(meeting_repo=_make_meeting_repo(), transcript_repo=repo)

        result = await service.export_transcript(repo._data["id"], "txt")

        assert result["format"] == "txt"
        assert "Hello world" in result["content"]
        assert result["filename"].endswith(".txt")

    async def test_export_txt_with_speakers(self):
        repo = _make_transcript_repo_with_data()
        service = TranscriptionService(meeting_repo=_make_meeting_repo(), transcript_repo=repo)

        result = await service.export_transcript(repo._data["id"], "txt")

        assert "[Speaker 1]: this is a test" in result["content"]

    async def test_export_srt(self):
        repo = _make_transcript_repo_with_data()
        service = TranscriptionService(meeting_repo=_make_meeting_repo(), transcript_repo=repo)

        result = await service.export_transcript(repo._data["id"], "srt")

        assert result["format"] == "srt"
        assert "00:00:00,000 --> 00:00:02,000" in result["content"]
        assert "1\n" in result["content"]
        assert "Hello world" in result["content"]

    async def test_export_vtt(self):
        repo = _make_transcript_repo_with_data()
        service = TranscriptionService(meeting_repo=_make_meeting_repo(), transcript_repo=repo)

        result = await service.export_transcript(repo._data["id"], "vtt")

        assert result["format"] == "vtt"
        assert result["content"].startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.000" in result["content"]

    async def test_export_not_found(self):
        class EmptyRepo:
            async def get_by_id(self, _):
                return None
        service = TranscriptionService(meeting_repo=_make_meeting_repo(), transcript_repo=EmptyRepo())

        result = await service.export_transcript(str(uuid4()), "txt")

        assert result is None

    async def test_get_transcript_by_id(self):
        repo = _make_transcript_repo_with_data()
        service = TranscriptionService(meeting_repo=_make_meeting_repo(), transcript_repo=repo)

        result = await service.get_transcript_by_id(repo._data["id"])

        assert result is not None
        assert result["full_text"] == "Hello world this is a test"

    async def test_srt_timestamp_format(self):
        """Verify SRT timestamp format is correct."""
        result = TranscriptionService._seconds_to_srt_time(3661.5)
        assert result == "01:01:01,500"

    async def test_vtt_timestamp_format(self):
        """Verify VTT timestamp format is correct."""
        result = TranscriptionService._seconds_to_vtt_time(3661.5)
        assert result == "01:01:01.500"
