import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from src.core.logging import get_logger

logger = get_logger(__name__)


class ReadWriteLock:
    """Async read-write lock for managing concurrent access."""
    
    def __init__(self):
        self._read_count = 0
        self._write_locked = False
        self._pending_writers = 0
        self._read_ready = asyncio.Condition()
        self._write_ready = asyncio.Condition()
    
    @asynccontextmanager
    async def read(self):
        """Acquire read lock."""
        await self._acquire_read()
        try:
            yield
        finally:
            await self._release_read()
    
    @asynccontextmanager
    async def write(self):
        """Acquire write lock."""
        await self._acquire_write()
        try:
            yield
        finally:
            await self._release_write()
    
    async def _acquire_read(self):
        """Acquire read lock implementation."""
        async with self._read_ready:
            # Wait while there's a writer or pending writers
            while self._write_locked or self._pending_writers > 0:
                await self._read_ready.wait()
            
            self._read_count += 1
            logger.debug(f"Read lock acquired, readers: {self._read_count}")
    
    async def _release_read(self):
        """Release read lock implementation."""
        async with self._read_ready:
            self._read_count -= 1
            logger.debug(f"Read lock released, readers: {self._read_count}")
            
            # Notify writers if no more readers
            if self._read_count == 0:
                self._read_ready.notify_all()
    
    async def _acquire_write(self):
        """Acquire write lock implementation."""
        async with self._write_ready:
            self._pending_writers += 1
            
            # Wait for exclusive access
            while self._write_locked or self._read_count > 0:
                await self._write_ready.wait()
            
            self._pending_writers -= 1
            self._write_locked = True
            logger.debug("Write lock acquired")
    
    async def _release_write(self):
        """Release write lock implementation."""
        async with self._write_ready:
            self._write_locked = False
            logger.debug("Write lock released")
            
            # Notify all waiting readers and writers
            self._write_ready.notify_all()
            async with self._read_ready:
                self._read_ready.notify_all()