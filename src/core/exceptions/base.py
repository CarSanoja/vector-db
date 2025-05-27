from typing import Any, Optional


class VectorDatabaseError(Exception):
    """Base exception for all vector database errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ValidationError(VectorDatabaseError):
    """Raised when validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if field:
            self.details["field"] = field


class NotFoundError(VectorDatabaseError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: Optional[str] = None,
        **kwargs
    ):
        message = message or f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message, **kwargs)
        self.details.update({
            "resource_type": resource_type,
            "resource_id": resource_id,
        })


class ConflictError(VectorDatabaseError):
    """Raised when there's a conflict in the operation."""

    def __init__(self, message: str, conflict_type: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if conflict_type:
            self.details["conflict_type"] = conflict_type


class IndexError(VectorDatabaseError):
    """Raised when there's an error with vector index operations."""

    def __init__(
        self,
        message: str,
        index_type: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if index_type:
            self.details["index_type"] = index_type
        if operation:
            self.details["operation"] = operation
