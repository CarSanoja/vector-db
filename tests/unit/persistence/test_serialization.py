"""Tests for serialization utilities."""
import pytest
import numpy as np
from datetime import datetime
from uuid import uuid4

from src.infrastructure.persistence.serialization.serializers import (
   MessagePackSerializer,
   VectorSerializer,
   StateSerializer
)
from src.domain.entities.library import Library, IndexType


def test_messagepack_serializer():
   """Test MessagePack serialization of various types."""
   # Test basic types
   data = {
       "string": "test",
       "int": 42,
       "float": 3.14,
       "list": [1, 2, 3],
       "dict": {"nested": True}
   }
   
   serialized = MessagePackSerializer.encode(data)
   deserialized = MessagePackSerializer.decode(serialized)
   assert deserialized == data
   
   # Test custom types
   custom_data = {
       "datetime": datetime.utcnow(),
       "uuid": uuid4(),
       "numpy": np.array([1.0, 2.0, 3.0]),
       "enum": IndexType.HNSW
   }
   
   serialized = MessagePackSerializer.encode(custom_data)
   deserialized = MessagePackSerializer.decode(serialized)
   
   assert deserialized["datetime"] == custom_data["datetime"]
   assert deserialized["uuid"] == custom_data["uuid"]
   assert np.array_equal(deserialized["numpy"], custom_data["numpy"])
   assert deserialized["enum"] == custom_data["enum"]


def test_vector_serializer():
   """Test vector serialization."""
   # Create test vectors
   vectors = [
       np.random.randn(128).astype(np.float32)
       for _ in range(10)
   ]
   
   # Serialize
   serialized = VectorSerializer.serialize_vectors(vectors)
   assert len(serialized) > 0
   
   # Deserialize
   deserialized = VectorSerializer.deserialize_vectors(serialized)
   assert len(deserialized) == len(vectors)
   
   # Check equality
   for orig, deser in zip(vectors, deserialized):
       assert np.allclose(orig, deser)
   
   # Test empty vectors
   empty_serialized = VectorSerializer.serialize_vectors([])
   empty_deserialized = VectorSerializer.deserialize_vectors(empty_serialized)
   assert empty_deserialized == []


def test_state_serializer():
   """Test complete state serialization."""
   # Create complex state
   state = {
       "libraries": {
           "lib1": {"name": "Test", "dimension": 128},
           "lib2": {"name": "Test2", "dimension": 256}
       },
       "chunk_vectors": [
           np.random.randn(128).astype(np.float32)
           for _ in range(5)
       ],
       "metadata": {
           "version": "1.0",
           "created_at": datetime.utcnow(),
           "entity_count": 100
       }
   }
   
   # Serialize
   serialized = StateSerializer.serialize_state(state)
   assert isinstance(serialized, bytes)
   
   # Deserialize
   deserialized = StateSerializer.deserialize_state(serialized)
   
   # Check non-vector data
   assert deserialized["libraries"] == state["libraries"]
   assert deserialized["metadata"]["version"] == state["metadata"]["version"]
   
   # Check vectors
   assert len(deserialized["chunk_vectors"]) == len(state["chunk_vectors"])
   for orig, deser in zip(state["chunk_vectors"], deserialized["chunk_vectors"]):
       assert np.allclose(orig, deser)
