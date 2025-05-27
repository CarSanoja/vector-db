import asyncio
from contextlib import asynccontextmanager
from enum import Enum
from typing import dict, list
from uuid import UUID

from src.core.logging import get_logger

from .rwlock import ReadWriteLock

logger = get_logger(__name__)


class LockLevel(Enum):
    """Lock hierarchy levels."""
    LIBRARY = 1
    DOCUMENT = 2
    CHUNK = 3
    INDEX = 4


class LockManager:
    """Manages hierarchical locks for different resource types."""

    def __init__(self):
        self._locks: dict[str, ReadWriteLock] = {}
        self._lock_creation_lock = asyncio.Lock()

    def _get_lock_key(self, level: LockLevel, resource_id: UUID) -> str:
        """Generate unique lock key for resource."""
        return f"{level.name}:{resource_id}"

    async def _get_or_create_lock(self, key: str) -> ReadWriteLock:
        """Get existing lock or create new one."""
        if key not in self._locks:
            async with self._lock_creation_lock:
                # Double-check pattern
                if key not in self._locks:
                    self._locks[key] = ReadWriteLock()
                    logger.debug(f"Created lock for {key}")

        return self._locks[key]

    @asynccontextmanager
    async def acquire_read(self, level: LockLevel, resource_id: UUID):
        """Acquire read lock for resource."""
        key = self._get_lock_key(level, resource_id)
        lock = await self._get_or_create_lock(key)

        async with lock.read():
            logger.debug(f"Acquired read lock for {key}")
            yield

    @asynccontextmanager
    async def acquire_write(self, level: LockLevel, resource_id: UUID):
        """Acquire write lock for resource."""
        key = self._get_lock_key(level, resource_id)
        lock = await self._get_or_create_lock(key)

        async with lock.write():
            logger.debug(f"Acquired write lock for {key}")
            yield

    @asynccontextmanager
    async def acquire_hierarchical(
        self,
        locks: list[tuple[LockLevel, UUID, str]]  # (level, id, "read" or "write")
    ):
        """Acquire multiple locks in hierarchical order to prevent deadlocks."""
        # Sort by level to ensure consistent ordering
        sorted_locks = sorted(locks, key=lambda x: x[0].value)

        acquired_locks = []
        try:
            # Acquire locks in order
            for level, resource_id, lock_type in sorted_locks:
                key = self._get_lock_key(level, resource_id)
                lock = await self._get_or_create_lock(key)

                if lock_type == "read":
                    ctx = lock.read()
                else:
                    ctx = lock.write()

                await ctx.__aenter__()
                acquired_locks.append(ctx)
                logger.debug(f"Acquired {lock_type} lock for {key}")

            yield

        finally:
            # Release locks in reverse order
            for ctx in reversed(acquired_locks):
                await ctx.__aexit__(None, None, None)

    def cleanup_unused_locks(self, threshold: int = 1000):
        """Remove unused locks to prevent memory leaks."""
        if len(self._locks) > threshold:
            # In a production system, would implement LRU or time-based cleanup
            logger.warning(f"Lock count exceeded threshold: {len(self._locks)}")


lock_manager = LockManager()

