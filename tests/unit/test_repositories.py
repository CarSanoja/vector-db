import asyncio
from uuid import uuid4

import pytest

from src.domain.entities.chunk import Chunk
from src.domain.entities.library import IndexType, Library
from src.infrastructure.repositories.in_memory import (
    InMemoryChunkRepository,
    InMemoryLibraryRepository,
)


class TestInMemoryLibraryRepository:
    """Test cases for InMemoryLibraryRepository."""

    @pytest.fixture
    def repository(self):
        """Create a repository instance."""
        return InMemoryLibraryRepository()

    @pytest.fixture
    def sample_library(self):
        """Create a sample library."""
        return Library(
            name="Test Library",
            description="A test library",
            index_type=IndexType.HNSW,
            dimension=128
        )

    @pytest.mark.asyncio
    async def test_create_library(self, repository, sample_library):
        """Test creating a library."""
        created = await repository.create(sample_library)

        assert created.id == sample_library.id
        assert created.name == sample_library.name
        assert created.dimension == sample_library.dimension

    @pytest.mark.asyncio
    async def test_get_library(self, repository, sample_library):
        """Test retrieving a library."""
        created = await repository.create(sample_library)
        retrieved = await repository.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_library(self, repository):
        """Test retrieving a non-existent library."""
        result = await repository.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_library(self, repository, sample_library):
        """Test updating a library."""
        created = await repository.create(sample_library)

        # Update the library
        created.name = "Updated Library"
        updated = await repository.update(created.id, created)

        assert updated is not None
        assert updated.name == "Updated Library"
        assert updated.id == created.id

    @pytest.mark.asyncio
    async def test_delete_library(self, repository, sample_library):
        """Test deleting a library."""
        created = await repository.create(sample_library)

        # Delete the library
        deleted = await repository.delete(created.id)
        assert deleted is True

        # Verify it's gone
        retrieved = await repository.get(created.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_libraries(self, repository):
        """Test listing libraries."""
        # Create multiple libraries
        libraries = [
            Library(name=f"Library {i}", dimension=128, index_type=IndexType.HNSW)
            for i in range(5)
        ]

        for lib in libraries:
            await repository.create(lib)

        # list all
        result = await repository.list()
        assert len(result) == 5

        # list with pagination
        result = await repository.list(limit=2, offset=1)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_by_name(self, repository):
        """Test getting library by name."""
        lib = Library(name="Unique Name", dimension=128, index_type=IndexType.HNSW)
        await repository.create(lib)

        result = await repository.get_by_name("Unique Name")
        assert result is not None
        assert result.name == "Unique Name"

        # Non-existent name
        result = await repository.get_by_name("Does Not Exist")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_index_type(self, repository):
        """Test listing libraries by index type."""
        # Create libraries with different index types
        await repository.create(Library(name="LSH 1", dimension=128, index_type=IndexType.LSH))
        await repository.create(Library(name="LSH 2", dimension=128, index_type=IndexType.LSH))
        await repository.create(Library(name="HNSW 1", dimension=128, index_type=IndexType.HNSW))

        # list by index type
        lsh_libs = await repository.list_by_index_type(IndexType.LSH)
        assert len(lsh_libs) == 2

        hnsw_libs = await repository.list_by_index_type(IndexType.HNSW)
        assert len(hnsw_libs) == 1


class TestInMemoryChunkRepository:
    """Test cases for InMemoryChunkRepository."""

    @pytest.fixture
    def repository(self):
        """Create a repository instance."""
        return InMemoryChunkRepository()

    @pytest.fixture
    def sample_chunk(self):
        """Create a sample chunk."""
        return Chunk(
            content="This is a test chunk",
            embedding=[0.1, 0.2, 0.3],
            document_id=uuid4(),
            chunk_index=0
        )

    @pytest.mark.asyncio
    async def test_create_chunk(self, repository, sample_chunk):
        """Test creating a chunk."""
        created = await repository.create(sample_chunk)

        assert created.id == sample_chunk.id
        assert created.content == sample_chunk.content
        assert created.embedding == sample_chunk.embedding

    @pytest.mark.asyncio
    async def test_create_bulk_chunks(self, repository):
        """Test bulk creation of chunks."""
        document_id = uuid4()
        chunks = [
            Chunk(
                content=f"Chunk {i}",
                embedding=[float(i)] * 3,
                document_id=document_id,
                chunk_index=i
            )
            for i in range(5)
        ]

        created = await repository.create_bulk(chunks)
        assert len(created) == 5

        # Verify all were created
        for i, chunk in enumerate(created):
            assert chunk.content == f"Chunk {i}"
            assert chunk.chunk_index == i

    @pytest.mark.asyncio
    async def test_get_by_document(self, repository):
        """Test getting chunks by document ID."""
        document_id = uuid4()

        # Create chunks for document
        chunks = [
            Chunk(
                content=f"Chunk {i}",
                embedding=[float(i)] * 3,
                document_id=document_id,
                chunk_index=i
            )
            for i in range(3)
        ]

        await repository.create_bulk(chunks)

        # Get by document
        result = await repository.get_by_document(document_id)
        assert len(result) == 3

        # Verify ordering by chunk_index
        for i, chunk in enumerate(result):
            assert chunk.chunk_index == i

    @pytest.mark.asyncio
    async def test_delete_by_document(self, repository):
        """Test deleting all chunks for a document."""
        document_id = uuid4()

        # Create chunks
        chunks = [
            Chunk(
                content=f"Chunk {i}",
                embedding=[float(i)] * 3,
                document_id=document_id,
                chunk_index=i
            )
            for i in range(3)
        ]

        await repository.create_bulk(chunks)

        # Delete by document
        deleted_count = await repository.delete_by_document(document_id)
        assert deleted_count == 3

        # Verify they're gone
        remaining = await repository.get_by_document(document_id)
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_search_by_metadata(self, repository):
        """Test searching chunks by metadata."""
        library_id = uuid4()

        # Create chunks with metadata
        chunks = [
            Chunk(
                content=f"Chunk {i}",
                embedding=[float(i)] * 3,
                metadata={
                    "library_id": str(library_id),
                    "category": "test" if i % 2 == 0 else "other",
                    "score": i * 10
                }
            )
            for i in range(5)
        ]

        await repository.create_bulk(chunks)

        # Search by simple filter
        result = await repository.search_by_metadata(
            library_id,
            {"category": "test"}
        )
        assert len(result) == 3  # Chunks 0, 2, 4

        # Search with operator filter
        result = await repository.search_by_metadata(
            library_id,
            {"score": {"$gte": 20}}
        )
        assert len(result) == 3  # Chunks 2, 3, 4


class TestReadWriteLock:
    """Test cases for ReadWriteLock."""

    @pytest.mark.asyncio
    async def test_multiple_readers(self):
        """Test multiple concurrent readers."""
        from src.infrastructure.locks import ReadWriteLock

        lock = ReadWriteLock()
        read_count = 0

        async def reader():
            nonlocal read_count
            async with lock.read():
                read_count += 1
                await asyncio.sleep(0.01)  # Simulate work
                read_count -= 1

        # Start multiple readers
        readers = [asyncio.create_task(reader()) for _ in range(5)]
        await asyncio.gather(*readers)

        assert read_count == 0  # All readers finished

    @pytest.mark.asyncio
    async def test_writer_exclusivity(self):
        """Test writer has exclusive access."""
        from src.infrastructure.locks import ReadWriteLock

        lock = ReadWriteLock()
        active_writers = 0

        async def writer():
            nonlocal active_writers
            async with lock.write():
                active_writers += 1
                assert active_writers == 1  # Only one writer
                await asyncio.sleep(0.01)
                active_writers -= 1

        # Start multiple writers
        writers = [asyncio.create_task(writer()) for _ in range(3)]
        await asyncio.gather(*writers)

        assert active_writers == 0
