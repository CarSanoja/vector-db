"""Write-Ahead Log interface."""
from abc import ABC, abstractmethod
from typing import Any, Optional, List, BinaryIO
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


class OperationType(Enum):
    """Types of WAL operations."""
    CREATE_LIBRARY = "CREATE_LIBRARY"
    UPDATE_LIBRARY = "UPDATE_LIBRARY"
    DELETE_LIBRARY = "DELETE_LIBRARY"
    CREATE_CHUNK = "CREATE_CHUNK"
    UPDATE_CHUNK = "UPDATE_CHUNK"
    DELETE_CHUNK = "DELETE_CHUNK"
    CREATE_DOCUMENT = "CREATE_DOCUMENT"
    UPDATE_DOCUMENT = "UPDATE_DOCUMENT"
    DELETE_DOCUMENT = "DELETE_DOCUMENT"
    INDEX_UPDATE = "INDEX_UPDATE"


@dataclass
class WALEntry:
    """Represents a single WAL entry."""
    sequence_number: int
    timestamp: datetime
    operation_type: OperationType
    resource_id: uuid.UUID
    data: dict
    checksum: str


class IWriteAheadLog(ABC):
    """Interface for Write-Ahead Log."""
    
    @abstractmethod
    async def append(
        self,
        operation_type: OperationType,
        resource_id: uuid.UUID,
        data: dict
    ) -> int:
        """Append an entry to the WAL."""
        pass
    
    @abstractmethod
    async def read(self, from_sequence: int = 0) -> List[WALEntry]:
        """Read entries from the WAL starting from a sequence number."""
        pass
    
    @abstractmethod
    async def checkpoint(self) -> int:
        """Create a checkpoint and return the sequence number."""
        pass
    
    @abstractmethod
    async def truncate(self, up_to_sequence: int) -> None:
        """Remove entries up to a sequence number."""
        pass
    
    @abstractmethod
    async def replay(self, from_sequence: int = 0) -> int:
        """Replay entries from a sequence number."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the WAL and release resources."""
        pass
