"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Check that the API is running."""
    return {
        "status": "healthy",
        "service": "AI Meeting Agent",
        "version": "0.1.0",
    }
