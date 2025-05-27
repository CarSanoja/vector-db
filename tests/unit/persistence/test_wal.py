"""Tests for Write-Ahead Log."""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from src.infrastructure.persistence.wal.file_wal import FileWAL
from src.infrastructure.persistence.wal.interface import OperationType


@pytest.mark.asyncio
async def test_wal_basic_operations():
    """Test basic WAL operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wal = FileWAL(Path(tmpdir))
        await wal.initialize()

        resource_id = uuid4()
        seq1 = await wal.append(
            OperationType.CREATE_LIBRARY,
            resource_id,
            {"name": "Test Library"}
        )
        assert seq1 == 1

        seq2 = await wal.append(
            OperationType.UPDATE_LIBRARY,
            resource_id,
            {"name": "Updated Library"}
        )
        assert seq2 == 2

        entries = await wal.read(from_sequence=0)
        assert len(entries) == 2
        assert entries[0].sequence_number == 1
        assert entries[0].operation_type == OperationType.CREATE_LIBRARY
        assert entries[1].sequence_number == 2

        await wal.close()


@pytest.mark.asyncio
async def test_wal_checkpoint_and_truncate():
    """Test WAL checkpoint and truncation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wal = FileWAL(Path(tmpdir))
        await wal.initialize()

        for i in range(5):
            await wal.append(
                OperationType.CREATE_CHUNK,
                uuid4(),
                {"index": i}
            )

        checkpoint_seq = await wal.checkpoint()
        assert checkpoint_seq == 5

        for i in range(5, 8):
            await wal.append(
                OperationType.CREATE_CHUNK,
                uuid4(),
                {"index": i}
            )

        await wal.truncate(checkpoint_seq)

        entries = await wal.read(from_sequence=0)
        assert len(entries) == 3
        assert entries[0].sequence_number == 6

        await wal.close()


@pytest.mark.asyncio
async def test_wal_recovery():
    """Test WAL recovery after crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wal_dir = Path(tmpdir)

        wal1 = FileWAL(wal_dir)
        await wal1.initialize()
        resource_id = uuid4()
        for i in range(3):
            await wal1.append(
                OperationType.CREATE_LIBRARY,
                resource_id,
                {"index": i}
            )

        # Don't close properly (simulate crash)
        # Force close the async file handle
        await wal1.current_file.close()
        wal1.current_file = None

        # Second session - recover
        wal2 = FileWAL(wal_dir)
        await wal2.initialize()

        # Should be able to read previous entries
        entries = await wal2.read()
        assert len(entries) == 3
        assert wal2.current_sequence == 3

        # Should be able to continue
        seq = await wal2.append(
            OperationType.UPDATE_LIBRARY,
            resource_id,
            {"recovered": True}
        )
        assert seq == 4

        await wal2.close()
