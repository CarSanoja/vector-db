"""File-based Write-Ahead Log implementation."""
import os
import json
import hashlib
import asyncio
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import uuid
import struct
import aiofiles
from asyncio import Lock

from .interface import IWriteAheadLog, WALEntry, OperationType
from src.core.logging import get_logger

logger = get_logger(__name__)


class FileWAL(IWriteAheadLog):
    """File-based WAL implementation with async I/O."""
    
    MAGIC_HEADER = b'VECWAL01'  # 8 bytes
    ENTRY_HEADER_SIZE = 32  # 4 + 8 + 4 + 16 bytes
    
    def __init__(self, wal_directory: Path, segment_size: int = 64 * 1024 * 1024):
        """Initialize FileWAL.
        
        Args:
            wal_directory: Directory to store WAL files
            segment_size: Maximum size of a WAL segment (default 64MB)
        """
        self.wal_directory = Path(wal_directory)
        self.segment_size = segment_size
        self.current_sequence = 0
        self.current_segment = 0
        self.current_file: Optional[BinaryIO] = None
        self.write_lock = Lock()
        
        # Create directory if it doesn't exist
        self.wal_directory.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self) -> None:
        """Initialize WAL and recover state."""
        await self._recover_state()
        await self._open_current_segment()
    
    async def append(
        self,
        operation_type: OperationType,
        resource_id: uuid.UUID,
        data: dict
    ) -> int:
        """Append an entry to the WAL."""
        async with self.write_lock:
            self.current_sequence += 1
            
            entry = WALEntry(
                sequence_number=self.current_sequence,
                timestamp=datetime.utcnow(),
                operation_type=operation_type,
                resource_id=resource_id,
                data=data,
                checksum=""
            )
            
            # Calculate checksum
            entry.checksum = self._calculate_checksum(entry)
            
            # Serialize entry
            serialized = self._serialize_entry(entry)
            
            # Check if we need a new segment
            if await self._should_rotate_segment(len(serialized)):
                await self._rotate_segment()
            
            # Write to file
            await self._write_entry(serialized)
            
            logger.debug(
                f"WAL entry appended",
                sequence=entry.sequence_number,
                operation=operation_type.value
            )
            
            return entry.sequence_number
    
    async def read(self, from_sequence: int = 0) -> List[WALEntry]:
        """Read entries from the WAL."""
        entries = []
        
        # Find segments to read
        segments = sorted([
            f for f in self.wal_directory.glob("wal_*.log")
            if f.is_file()
        ])
        
        for segment_file in segments:
            segment_entries = await self._read_segment(segment_file)
            for entry in segment_entries:
                if entry.sequence_number >= from_sequence:
                    entries.append(entry)
        
        return entries
    
    async def checkpoint(self) -> int:
        """Create a checkpoint."""
        async with self.write_lock:
            checkpoint_sequence = self.current_sequence
            
            # Flush current segment
            if self.current_file:
                await self.current_file.flush()
                os.fsync(self.current_file.fileno())
            
            # Write checkpoint marker
            checkpoint_file = self.wal_directory / f"checkpoint_{checkpoint_sequence}"
            async with aiofiles.open(checkpoint_file, 'w') as f:
                await f.write(json.dumps({
                    "sequence": checkpoint_sequence,
                    "timestamp": datetime.utcnow().isoformat(),
                    "segment": self.current_segment
                }))
            
            logger.info(f"Checkpoint created at sequence {checkpoint_sequence}")
            return checkpoint_sequence
    
    async def truncate(self, up_to_sequence: int) -> None:
        """Remove entries up to a sequence number."""
        segments = sorted([
            f for f in self.wal_directory.glob("wal_*.log")
            if f.is_file()
        ])
        
        for segment_file in segments:
            # Read segment to check sequences
            entries = await self._read_segment(segment_file)
            if not entries:
                continue
                
            # If all entries are before truncation point, delete segment
            if all(e.sequence_number <= up_to_sequence for e in entries):
                segment_file.unlink()
                logger.info(f"Truncated segment {segment_file.name}")
            else:
                # Partial truncation - rewrite segment
                remaining = [e for e in entries if e.sequence_number > up_to_sequence]
                if remaining:
                    await self._rewrite_segment(segment_file, remaining)
    
    async def replay(self, from_sequence: int = 0) -> int:
        """Replay entries from a sequence number."""
        entries = await self.read(from_sequence)
        
        # In a real implementation, this would apply the operations
        # For now, we just count them
        logger.info(f"Replaying {len(entries)} entries from sequence {from_sequence}")
        
        return len(entries)
    
    async def close(self) -> None:
        """Close the WAL."""
        async with self.write_lock:
            if self.current_file:
                await self.current_file.close()
                self.current_file = None
    
    # Private methods
    async def _recover_state(self) -> None:
        """Recover WAL state from existing files."""
        # Find latest checkpoint
        checkpoints = sorted(self.wal_directory.glob("checkpoint_*"))
        if checkpoints:
            latest_checkpoint = checkpoints[-1]
            with open(latest_checkpoint, 'r') as f:
                checkpoint_data = json.load(f)
                self.current_sequence = checkpoint_data["sequence"]
                self.current_segment = checkpoint_data["segment"]
        
        # Find highest sequence in WAL files
        segments = sorted(self.wal_directory.glob("wal_*.log"))
        for segment in segments:
            entries = await self._read_segment(segment)
            if entries:
                max_seq = max(e.sequence_number for e in entries)
                self.current_sequence = max(self.current_sequence, max_seq)
    
    async def _open_current_segment(self) -> None:
        """Open the current segment for writing."""
        segment_path = self.wal_directory / f"wal_{self.current_segment:08d}.log"
        self.current_file = open(segment_path, 'ab')
        
        # Write magic header if new file
        if self.current_file.tell() == 0:
            self.current_file.write(self.MAGIC_HEADER)
    
    async def _should_rotate_segment(self, entry_size: int) -> bool:
        """Check if segment should be rotated."""
        if not self.current_file:
            return True
        
        current_size = self.current_file.tell()
        return current_size + entry_size > self.segment_size
    
    async def _rotate_segment(self) -> None:
        """Rotate to a new segment."""
        if self.current_file:
            await self.current_file.close()
        
        self.current_segment += 1
        await self._open_current_segment()
    
    def _serialize_entry(self, entry: WALEntry) -> bytes:
        """Serialize a WAL entry to bytes."""
        # Serialize data as JSON
        data_json = json.dumps({
            "operation_type": entry.operation_type.value,
            "resource_id": str(entry.resource_id),
            "timestamp": entry.timestamp.isoformat(),
            "data": entry.data
        })
        data_bytes = data_json.encode('utf-8')
        
        # Create header: sequence(4) + timestamp(8) + data_len(4) + checksum(16)
        header = struct.pack(
            '<IQI16s',
            entry.sequence_number,
            int(entry.timestamp.timestamp() * 1000000),  # microseconds
            len(data_bytes),
            entry.checksum[:16].encode('utf-8')
        )
        
        return header + data_bytes
    
    async def _write_entry(self, serialized: bytes) -> None:
        """Write serialized entry to current segment."""
        self.current_file.write(serialized)
        await self.current_file.flush()
    
    async def _read_segment(self, segment_file: Path) -> List[WALEntry]:
        """Read all entries from a segment."""
        entries = []
        
        async with aiofiles.open(segment_file, 'rb') as f:
            # Read and verify magic header
            magic = await f.read(8)
            if magic != self.MAGIC_HEADER:
                logger.error(f"Invalid WAL segment: {segment_file}")
                return entries
            
            while True:
                # Read header
                header_data = await f.read(self.ENTRY_HEADER_SIZE)
                if len(header_data) < self.ENTRY_HEADER_SIZE:
                    break
                
                # Unpack header
                seq, timestamp_us, data_len, checksum = struct.unpack(
                    '<IQI16s', header_data
                )
                
                # Read data
                data_bytes = await f.read(data_len)
                if len(data_bytes) < data_len:
                    logger.error(f"Truncated entry in {segment_file}")
                    break
                
                # Deserialize
                try:
                    data_json = json.loads(data_bytes.decode('utf-8'))
                    entry = WALEntry(
                        sequence_number=seq,
                        timestamp=datetime.fromtimestamp(timestamp_us / 1000000),
                        operation_type=OperationType(data_json["operation_type"]),
                        resource_id=uuid.UUID(data_json["resource_id"]),
                        data=data_json["data"],
                        checksum=checksum.decode('utf-8').rstrip('\x00')
                    )
                    entries.append(entry)
                except Exception as e:
                    logger.error(f"Failed to deserialize entry: {e}")
                    continue
        
        return entries
    
    async def _rewrite_segment(self, segment_file: Path, entries: List[WALEntry]) -> None:
        """Rewrite a segment with given entries."""
        temp_file = segment_file.with_suffix('.tmp')
        
        async with aiofiles.open(temp_file, 'wb') as f:
            await f.write(self.MAGIC_HEADER)
            
            for entry in entries:
                serialized = self._serialize_entry(entry)
                await f.write(serialized)
        
        # Atomic rename
        temp_file.rename(segment_file)
    
    def _calculate_checksum(self, entry: WALEntry) -> str:
        """Calculate checksum for an entry."""
        data = f"{entry.sequence_number}:{entry.operation_type.value}:{entry.resource_id}:{json.dumps(entry.data)}"
        return hashlib.md5(data.encode()).hexdigest()
