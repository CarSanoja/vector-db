from datetime import datetime

from fastapi import APIRouter, status

from src.api.models.common import HealthResponse
from src.core.config import settings

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Health check",
    description="Check if the API is healthy and responsive"
)
async def health_check() -> HealthResponse:
    """Check API health status."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0",
        services={
            "api": "healthy",
            "vector_db": "healthy",
            "environment": settings.env
        }
    )


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Readiness check",
    description="Check if the API is ready to serve requests"
)
async def readiness_check() -> dict:
    """Check API readiness."""
    # Could add additional checks here (DB connection, etc.)
    return {"ready": True}
