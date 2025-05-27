from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.dependencies import LibraryServiceDep, PaginationDep
from src.api.models.library import (
    LibraryCreate,
    LibraryListResponse,
    LibraryResponse,
    LibraryUpdate,
)
from src.core.exceptions import ConflictError, NotFoundError
from src.domain.entities.library import IndexType

router = APIRouter(prefix="/libraries", tags=["libraries"])


@router.post(
    "/",
    response_model=LibraryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new library",
    description="Create a new vector library with specified index type and dimension"
)
async def create_library(
    library: LibraryCreate,
    service: LibraryServiceDep
) -> LibraryResponse:
    """Create a new library."""
    try:
        created = await service.create_library(
            name=library.name,
            dimension=library.dimension,
            index_type=library.index_type,
            description=library.description,
            metadata=library.metadata
        )
        return LibraryResponse.from_orm(created)
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.error_code, "message": str(e), "details": e.details}}
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": str(e)}}
        ) from e


@router.get(
    "/",
    response_model=LibraryListResponse,
    summary="list libraries",
    description="list all libraries with optional filtering"
)
async def list_libraries(
    service: LibraryServiceDep,
    pagination: PaginationDep,
    index_type: Optional[IndexType] = Query(None, description="Filter by index type")
) -> LibraryListResponse:
    """list libraries."""
    libraries = await service.list_libraries(
        index_type=index_type,
        limit=pagination.limit,
        offset=pagination.offset
    )

    # Get total count
    all_libraries = await service.list_libraries(index_type=index_type)
    total = len(all_libraries)

    return LibraryListResponse(
        libraries=[LibraryResponse.from_orm(lib) for lib in libraries],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset
    )


@router.get(
    "/{library_id}",
    response_model=LibraryResponse,
    summary="Get library by ID",
    description="Retrieve a specific library by its ID"
)
async def get_library(
    library_id: UUID,
    service: LibraryServiceDep
) -> LibraryResponse:
    """Get a library by ID."""
    library = await service.get_library(library_id)
    if not library:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "LIBRARY_NOT_FOUND",
                    "message": f"Library with id '{library_id}' not found",
                    "details": {"library_id": str(library_id)}
                }
            }
        )
    return LibraryResponse.from_orm(library)


@router.put(
    "/{library_id}",
    response_model=LibraryResponse,
    summary="Update library",
    description="Update library metadata"
)
async def update_library(
    library_id: UUID,
    update: LibraryUpdate,
    service: LibraryServiceDep
) -> LibraryResponse:
    """Update a library."""
    try:
        updated = await service.update_library(
            library_id=library_id,
            name=update.name,
            description=update.description,
            metadata=update.metadata
        )
        if not updated:
            raise NotFoundError("Library", str(library_id))
        return LibraryResponse.from_orm(updated)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.error_code, "message": str(e), "details": e.details}}
        ) from e
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": e.error_code, "message": str(e), "details": e.details}}
        ) from e


@router.delete(
    "/{library_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete library",
    description="Delete a library and all its contents"
)
async def delete_library(
    library_id: UUID,
    service: LibraryServiceDep
) -> None:
    """Delete a library."""
    deleted = await service.delete_library(library_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "LIBRARY_NOT_FOUND",
                    "message": f"Library with id '{library_id}' not found",
                    "details": {"library_id": str(library_id)}
                }
            }
        )


@router.post(
    "/{library_id}/index",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Rebuild library index",
    description="Trigger index rebuild for a library"
)
async def rebuild_index(
    library_id: UUID,
    service: LibraryServiceDep
) -> dict:
    """Rebuild library index."""
    library = await service.get_library(library_id)
    if not library:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "LIBRARY_NOT_FOUND",
                    "message": f"Library with id '{library_id}' not found",
                    "details": {"library_id": str(library_id)}
                }
            }
        )

    # In a real implementation, this would trigger an async job
    return {
        "message": "Index rebuild initiated",
        "library_id": str(library_id),
        "status": "pending"
    }
