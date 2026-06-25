"""Summary API endpoints."""

from fastapi import APIRouter, HTTPException

from meeting_agent.api.deps import SummaryServiceDep
from meeting_agent.api.schemas.summaries import SummaryResponse, SummaryUpdateRequest

router = APIRouter()


@router.get("/{summary_id}", response_model=SummaryResponse)
async def get_summary(summary_id: str, service: SummaryServiceDep):
    """Get summary by ID."""
    summary = await service.get_summary_by_id(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Summary {summary_id} not found")
    return summary


@router.patch("/{summary_id}", response_model=SummaryResponse)
async def update_summary(summary_id: str, body: SummaryUpdateRequest, service: SummaryServiceDep):
    """Edit a summary (manual corrections)."""
    return await service.update_summary(summary_id, body)
