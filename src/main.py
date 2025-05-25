"""Main application entry point for Vector Database API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import health, libraries, chunks, search
from src.core.config import settings

# Create FastAPI application
app = FastAPI(
    title="Vector Database API",
    description="REST API for indexing and querying documents in a Vector Database",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(libraries.router, prefix="/api/v1", tags=["libraries"])
app.include_router(chunks.router, prefix="/api/v1", tags=["chunks"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    print("Vector Database API starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    print("Vector Database API shutting down...")
