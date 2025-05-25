from typing import Dict, List
from uuid import UUID
import time

from fastapi import APIRouter, HTTPException, status

from src.api.models.search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    MultiSearchRequest,
    MultiSearchResponse
)
from src.api.dependencies import SearchServiceDep
from src.core.exceptions import NotFoundError, ValidationError

router = APIRouter(tags=["search"])


@router.post(
    "/libraries/{library_id}/search",
    response_model=SearchResponse,
    summary="Search in library",
    description="Perform vector similarity search in a library"
)
async def search_library(
    library_id: UUID,
    request: SearchRequest,
    search_service: SearchServiceDep
) -> SearchResponse:
    """Search for similar chunks in a library."""
    try:
        start_time = time.time()
        
        results = await search_service.search(
            library_id=library_id,
            embedding=request.embedding,
            k=request.k,
            metadata_filters=request.metadata_filters
        )
        
        query_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=[SearchResult.from_orm(r) for r in results],
            query_time_ms=query_time_ms,
            total_found=len(results)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.error_code, "message": str(e), "details": e.details}}
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": e.error_code, "message": str(e), "details": e.details}}
        )


@router.post(
    "/search",
    response_model=MultiSearchResponse,
    summary="Multi-library search",
    description="Search across multiple libraries simultaneously"
)
async def multi_library_search(
    request: MultiSearchRequest,
    search_service: SearchServiceDep
) -> MultiSearchResponse:
    """Search across multiple libraries."""
    try:
        start_time = time.time()
        
        results = await search_service.multi_library_search(
            library_ids=request.library_ids,
            embedding=request.embedding,
            k=request.k,
            metadata_filters=request.metadata_filters
        )
        
        query_time_ms = (time.time() - start_time) * 1000
        
        # Convert results to response format
        formatted_results: Dict[UUID, List[SearchResult]] = {}
        total_found = 0
        
        for library_id, search_results in results.items():
            formatted_results[library_id] = [
                SearchResult.from_orm(r) for r in search_results
            ]
            total_found += len(search_results)
        
        return MultiSearchResponse(
            results=formatted_results,
            query_time_ms=query_time_ms,
            total_found=total_found
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.error_code, "message": str(e), "details": e.details}}
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": e.error_code, "message": str(e), "details": e.details}}
        )
