from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Path

from src.api.models.chunk import (
    ChunkCreate,
    ChunkUpdate,
    ChunkResponse,
    ChunkBulkCreate,
    ChunkListResponse
)
from src.api.dependencies import ChunkServiceDep, LibraryServiceDep, PaginationDep
from src.core.exceptions import NotFoundError, ValidationError

router = APIRouter(tags=["chunks"])


@router.post(
    "/libraries/{library_id}/chunks",
    response_model=ChunkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a chunk",
    description="Create a new chunk in a library"
)
async def create_chunk(
    library_id: UUID,
    chunk: ChunkCreate,
    chunk_service: ChunkServiceDep
) -> ChunkResponse:
    """Create a new chunk."""
    try:
        created = await chunk_service.create_chunk(
            library_id=library_id,
            content=chunk.content,
            embedding=chunk.embedding,
            document_id=chunk.document_id,
            metadata=chunk.metadata
        )
        return ChunkResponse.from_orm(created)
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
    "/libraries/{library_id}/chunks/bulk",
    response_model=List[ChunkResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create chunks",
    description="Create multiple chunks in a single operation"
)
async def create_chunks_bulk(
    library_id: UUID,
    request: ChunkBulkCreate,
    chunk_service: ChunkServiceDep
) -> List[ChunkResponse]:
    """Create multiple chunks."""
    try:
        chunks_data = [chunk.dict() for chunk in request.chunks]
        created = await chunk_service.create_chunks_bulk(
            library_id=library_id,
            chunks_data=chunks_data
        )
        return [ChunkResponse.from_orm(chunk) for chunk in created]
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


@router.get(
    "/libraries/{library_id}/chunks",
    response_model=ChunkListResponse,
    summary="List chunks in library",
    description="List all chunks in a library with pagination"
)
async def list_chunks(
    library_id: UUID,
    chunk_service: ChunkServiceDep,
    pagination: PaginationDep
) -> ChunkListResponse:
    """List chunks in a library."""
    try:
        chunks = await chunk_service.list_chunks(
            library_id=library_id,
            limit=pagination.limit,
            offset=pagination.offset
        )
        
        # Get total count
        all_chunks = await chunk_service.list_chunks(library_id=library_id, limit=10000)
        total = len(all_chunks)
        
        return ChunkListResponse(
            chunks=[ChunkResponse.from_orm(chunk) for chunk in chunks],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.error_code, "message": str(e), "details": e.details}}
        )


@router.get(
    "/chunks/{chunk_id}",
    response_model=ChunkResponse,
    summary="Get chunk by ID",
    description="Retrieve a specific chunk by its ID"
)
async def get_chunk(
    chunk_id: UUID,
    chunk_service: ChunkServiceDep
) -> ChunkResponse:
    """Get a chunk by ID."""
    chunk = await chunk_service.get_chunk(chunk_id)
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CHUNK_NOT_FOUND",
                    "message": f"Chunk with id '{chunk_id}' not found",
                    "details": {"chunk_id": str(chunk_id)}
                }
            }
        )
    return ChunkResponse.from_orm(chunk)


@router.put(
    "/chunks/{chunk_id}",
    response_model=ChunkResponse,
    summary="Update chunk",
    description="Update chunk content or metadata"
)
async def update_chunk(
    chunk_id: UUID,
    update: ChunkUpdate,
    chunk_service: ChunkServiceDep
) -> ChunkResponse:
    """Update a chunk."""
    try:
        updated = await chunk_service.update_chunk(
            chunk_id=chunk_id,
            content=update.content,
            embedding=update.embedding,
            metadata=update.metadata
        )
        if not updated:
            raise NotFoundError("Chunk", str(chunk_id))
        return ChunkResponse.from_orm(updated)
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


@router.delete(
    "/chunks/{chunk_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete chunk",
    description="Delete a chunk from the library"
)
async def delete_chunk(
    chunk_id: UUID,
    chunk_service: ChunkServiceDep
) -> None:
    """Delete a chunk."""
    deleted = await chunk_service.delete_chunk(chunk_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CHUNK_NOT_FOUND",
                    "message": f"Chunk with id '{chunk_id}' not found",
                    "details": {"chunk_id": str(chunk_id)}
                }
            }
        )
