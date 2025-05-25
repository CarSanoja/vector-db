import pytest
from uuid import uuid4
import numpy as np

from src.domain.entities.library import Library, IndexType
from src.domain.entities.chunk import Chunk
from src.infrastructure.repositories.in_memory import (
    InMemoryLibraryRepository,
    InMemoryChunkRepository
)
from src.services.library_service import LibraryService
from src.services.chunk_service import ChunkService
from src.services.search_service import SearchService
from src.core.exceptions import NotFoundError, ConflictError, ValidationError


class TestLibraryService:
    """Test cases for LibraryService."""
    
    @pytest.fixture
    async def repository(self):
        """Create library repository."""
        return InMemoryLibraryRepository()
    
    @pytest.fixture
    async def service(self, repository):
        """Create library service."""
        return LibraryService(repository)
    
    @pytest.mark.asyncio
    async def test_create_library(self, service):
        """Test creating a library."""
        library = await service.create_library(
            name="Test Library",
            dimension=128,
            index_type=IndexType.HNSW,
            description="A test library"
        )
        
        assert library.name == "Test Library"
        assert library.dimension == 128
        assert library.index_type == IndexType.HNSW
        
        # Verify index was created
        index = service.get_index(library.id)
        assert index is not None
        assert index.dimension == 128
    
    @pytest.mark.asyncio
    async def test_create_duplicate_name(self, service):
        """Test creating library with duplicate name."""
        await service.create_library(
            name="Unique Name",
            dimension=64,
            index_type=IndexType.LSH
        )
        
        with pytest.raises(ConflictError):
            await service.create_library(
                name="Unique Name",
                dimension=64,
                index_type=IndexType.LSH
            )
    
    @pytest.mark.asyncio
    async def test_update_library(self, service):
        """Test updating library."""
        library = await service.create_library(
            name="Original Name",
            dimension=128,
            index_type=IndexType.HNSW
        )
        
        updated = await service.update_library(
            library.id,
            name="New Name",
            description="Updated description"
        )
        
        assert updated.name == "New Name"
        assert updated.description == "Updated description"
    
    @pytest.mark.asyncio
    async def test_delete_library(self, service):
        """Test deleting library."""
        library = await service.create_library(
            name="To Delete",
            dimension=64,
            index_type=IndexType.KD_TREE
        )
        
        deleted = await service.delete_library(library.id)
        assert deleted is True
        
        # Verify library is gone
        retrieved = await service.get_library(library.id)
        assert retrieved is None
        
        # Verify index is removed
        index = service.get_index(library.id)
        assert index is None


class TestChunkService:
    """Test cases for ChunkService."""
    
    @pytest.fixture
    async def library_service(self):
        """Create library service."""
        repo = InMemoryLibraryRepository()
        return LibraryService(repo)
    
    @pytest.fixture
    async def chunk_repository(self):
        """Create chunk repository."""
        return InMemoryChunkRepository()
    
    @pytest.fixture
    async def service(self, chunk_repository, library_service):
        """Create chunk service."""
        return ChunkService(chunk_repository, library_service)
    
    @pytest.fixture
    async def test_library(self, library_service):
        """Create a test library."""
        return await library_service.create_library(
            name="Test Library",
            dimension=8,
            index_type=IndexType.HNSW
        )
    
    @pytest.mark.asyncio
    async def test_create_chunk(self, service, test_library):
        """Test creating a chunk."""
        embedding = [0.1] * 8
        chunk = await service.create_chunk(
            library_id=test_library.id,
            content="Test content",
            embedding=embedding,
            metadata={"key": "value"}
        )
        
        assert chunk.content == "Test content"
        assert chunk.embedding == embedding
        assert chunk.metadata["library_id"] == str(test_library.id)
        assert chunk.metadata["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_create_chunk_wrong_dimension(self, service, test_library):
        """Test creating chunk with wrong embedding dimension."""
        with pytest.raises(ValidationError) as exc_info:
            await service.create_chunk(
                library_id=test_library.id,
                content="Test",
                embedding=[0.1] * 16  # Wrong dimension
            )
        assert "dimension" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_chunks_bulk(self, service, test_library):
        """Test bulk chunk creation."""
        chunks_data = [
            {
                "content": f"Chunk {i}",
                "embedding": [float(i)] * 8,
                "metadata": {"index": i}
            }
            for i in range(5)
        ]
        
        chunks = await service.create_chunks_bulk(
            library_id=test_library.id,
            chunks_data=chunks_data
        )
        
        assert len(chunks) == 5
        for i, chunk in enumerate(chunks):
            assert chunk.content == f"Chunk {i}"
            assert chunk.metadata["index"] == i
    
    @pytest.mark.asyncio
    async def test_update_chunk(self, service, test_library):
        """Test updating a chunk."""
        # Create chunk
        chunk = await service.create_chunk(
            library_id=test_library.id,
            content="Original",
            embedding=[0.1] * 8
        )
        
        # Update it
        new_embedding = [0.2] * 8
        updated = await service.update_chunk(
            chunk_id=chunk.id,
            content="Updated",
            embedding=new_embedding
        )
        
        assert updated.content == "Updated"
        assert updated.embedding == new_embedding
    
    @pytest.mark.asyncio
    async def test_delete_chunks_by_document(self, service, test_library):
        """Test deleting chunks by document."""
        document_id = uuid4()
        
        # Create chunks for document
        for i in range(3):
            await service.create_chunk(
                library_id=test_library.id,
                content=f"Doc chunk {i}",
                embedding=[float(i)] * 8,
                document_id=document_id
            )
        
        # Delete by document
        deleted_count = await service.delete_chunks_by_document(document_id)
        assert deleted_count == 3
        
        # Verify chunks are gone
        remaining = await service.get_chunks_by_document(document_id)
        assert len(remaining) == 0


class TestSearchService:
    """Test cases for SearchService."""
    
    @pytest.fixture
    async def services(self):
        """Create all required services."""
        lib_repo = InMemoryLibraryRepository()
        chunk_repo = InMemoryChunkRepository()
        
        lib_service = LibraryService(lib_repo)
        chunk_service = ChunkService(chunk_repo, lib_service)
        search_service = SearchService(chunk_repo, lib_service)
        
        return lib_service, chunk_service, search_service
    
    @pytest.fixture
    async def test_library_with_chunks(self, services):
        """Create a library with test chunks."""
        lib_service, chunk_service, _ = services
        
        # Create library
        library = await lib_service.create_library(
            name="Search Test Library",
            dimension=8,
            index_type=IndexType.HNSW
        )
        
        # Add chunks
        np.random.seed(42)
        chunks_data = []
        for i in range(20):
            embedding = np.random.randn(8).tolist()
            chunks_data.append({
                "content": f"Content {i}",
                "embedding": embedding,
                "metadata": {
                    "category": "A" if i < 10 else "B",
                    "score": i * 10
                }
            })
        
        await chunk_service.create_chunks_bulk(
            library_id=library.id,
            chunks_data=chunks_data
        )
        
        return library
    
    @pytest.mark.asyncio
    async def test_search_basic(self, services, test_library_with_chunks):
        """Test basic search functionality."""
        _, _, search_service = services
        library = test_library_with_chunks
        
        # Search with random query
        query_embedding = np.random.randn(8).tolist()
        results = await search_service.search(
            library_id=library.id,
            embedding=query_embedding,
            k=5
        )
        
        assert len(results) <= 5
        assert all(hasattr(r, 'chunk_id') for r in results)
        assert all(hasattr(r, 'distance') for r in results)
        assert all(hasattr(r, 'score') for r in results)
        
        # Results should be sorted by distance
        distances = [r.distance for r in results]
        assert distances == sorted(distances)
    
    @pytest.mark.asyncio
    async def test_search_with_metadata_filter(self, services, test_library_with_chunks):
        """Test search with metadata filtering."""
        _, _, search_service = services
        library = test_library_with_chunks
        
        query_embedding = np.random.randn(8).tolist()
        
        # Search with category filter
        results = await search_service.search(
            library_id=library.id,
            embedding=query_embedding,
            k=5,
            metadata_filters={"category": "A"}
        )
        
        # All results should have category A
        assert all(r.metadata.get("category") == "A" for r in results)
    
    @pytest.mark.asyncio
    async def test_search_wrong_dimension(self, services, test_library_with_chunks):
        """Test search with wrong embedding dimension."""
        _, _, search_service = services
        library = test_library_with_chunks
        
        with pytest.raises(ValidationError) as exc_info:
            await search_service.search(
                library_id=library.id,
                embedding=[0.1] * 16,  # Wrong dimension
                k=5
            )
        assert "dimension" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_multi_library_search(self, services):
        """Test searching across multiple libraries."""
        lib_service, chunk_service, search_service = services
        
        # Create two libraries
        lib1 = await lib_service.create_library(
            name="Library 1",
            dimension=8,
            index_type=IndexType.LSH
        )
        lib2 = await lib_service.create_library(
            name="Library 2",
            dimension=8,
            index_type=IndexType.HNSW
        )
        
        # Add chunks to both
        for lib in [lib1, lib2]:
            chunks_data = [
                {
                    "content": f"Lib {lib.name} chunk {i}",
                    "embedding": np.random.randn(8).tolist()
                }
                for i in range(5)
            ]
            await chunk_service.create_chunks_bulk(
                library_id=lib.id,
                chunks_data=chunks_data
            )
        
        # Multi-library search
        query_embedding = np.random.randn(8).tolist()
        results = await search_service.multi_library_search(
            library_ids=[lib1.id, lib2.id],
            embedding=query_embedding,
            k=3
        )
        
        assert len(results) == 2
        assert lib1.id in results
        assert lib2.id in results
        assert len(results[lib1.id]) <= 3
        assert len(results[lib2.id]) <= 3
    
    @pytest.mark.asyncio
    async def test_search_cache(self, services, test_library_with_chunks):
        """Test search result caching."""
        _, _, search_service = services
        library = test_library_with_chunks
        
        query_embedding = [0.1] * 8
        
        # First search
        results1 = await search_service.search(
            library_id=library.id,
            embedding=query_embedding,
            k=5
        )
        
        # Second search with same parameters (should hit cache)
        results2 = await search_service.search(
            library_id=library.id,
            embedding=query_embedding,
            k=5
        )
        
        # Results should be identical
        assert len(results1) == len(results2)
        assert all(r1.chunk_id == r2.chunk_id for r1, r2 in zip(results1, results2))
        
        # Clear cache
        search_service.clear_cache()
        
        # Third search (cache cleared)
        results3 = await search_service.search(
            library_id=library.id,
            embedding=query_embedding,
            k=5
        )
        
        # Results should still be the same (deterministic)
        assert len(results1) == len(results3)