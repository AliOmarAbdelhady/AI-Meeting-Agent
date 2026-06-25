"""Transcript API endpoints."""

from fastapi import APIRouter, HTTPException, Query

from meeting_agent.api.deps import TranscriptionServiceDep
from meeting_agent.api.schemas.transcripts import TranscriptExportResponse, TranscriptResponse

router = APIRouter()


@router.get("/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(transcript_id: str, service: TranscriptionServiceDep):
    """Get transcript by ID."""
    transcript = await service.get_transcript_by_id(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail=f"Transcript {transcript_id} not found")
    return transcript


@router.get("/{transcript_id}/export", response_model=TranscriptExportResponse)
async def export_transcript(
    transcript_id: str,
    service: TranscriptionServiceDep,
    format: str = Query("txt", description="Export format: txt, srt, vtt"),
):
    """Export transcript in various formats (txt, srt, vtt)."""
    return await service.export_transcript(transcript_id, format)
