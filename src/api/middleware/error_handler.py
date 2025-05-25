from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.exceptions import (
    VectorDatabaseError,
    ValidationError,
    NotFoundError,
    ConflictError
)
from src.core.logging import get_logger

logger = get_logger(__name__)


async def vector_database_exception_handler(
    request: Request,
    exc: VectorDatabaseError
) -> JSONResponse:
    """Handle custom vector database exceptions."""
    logger.error(
        f"VectorDatabaseError: {exc.message}",
        error_code=exc.error_code,
        details=exc.details,
        path=request.url.path
    )
    
    # Map exceptions to HTTP status codes
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.error(
        "Validation error",
        errors=exc.errors(),
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors()
            }
        }
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.error(
        f"HTTP exception: {exc.detail}",
        status_code=exc.status_code,
        path=request.url.path
    )
    
    # If detail is already a dict with error structure, use it
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = exc.detail
    else:
        content = {
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "details": {"status_code": exc.status_code}
            }
        }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle any unhandled exceptions."""
    logger.exception(
        "Unhandled exception",
        exc_type=type(exc).__name__,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {}
            }
        }
    )