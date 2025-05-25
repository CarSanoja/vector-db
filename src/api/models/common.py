from typing import Dict, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from fastapi import Query


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: Dict[str, Any] = Field(
        ...,
        example={
            "code": "RESOURCE_NOT_FOUND",
            "message": "Library not found",
            "details": {"resource_type": "library", "resource_id": "123"}
        }
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime
    version: str
    services: Dict[str, str]


class PaginationParams(BaseModel):
    """Pagination parameters."""
    limit: int = Query(default=100, ge=1, le=1000)
    offset: int = Query(default=0, ge=0)
