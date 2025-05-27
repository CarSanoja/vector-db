from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.endpoints import chunks, health, libraries, search
from src.api.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    vector_database_exception_handler,
)
from src.api.middleware.logging import LoggingMiddleware
from src.core.config import settings
from src.core.exceptions import VectorDatabaseError


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Vector Database API",
        description="REST API for indexing and querying documents in a Vector Database",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        redirect_slashes=False
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)

    app.add_exception_handler(VectorDatabaseError, vector_database_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(health.router, tags=["health"])
    app.include_router(
        libraries.router,
        prefix=settings.api_prefix,
        tags=["libraries"]
    )
    app.include_router(
        chunks.router,
        prefix=settings.api_prefix,
        tags=["chunks"]
    )
    app.include_router(
        search.router,
        prefix=settings.api_prefix,
        tags=["search"]
    )

    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup."""
        # Create necessary directories
        settings.create_directories()

        # Log startup
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info(
            "Vector Database API starting up",
            environment=settings.env,
            api_prefix=settings.api_prefix
        )

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on application shutdown."""
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Vector Database API shutting down")

    return app


app = create_app()
