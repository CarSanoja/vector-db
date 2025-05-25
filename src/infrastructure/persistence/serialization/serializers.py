"""Serialization utilities for various data types."""
import json
import numpy as np
import msgpack
from typing import Any, Dict, List, Union
from datetime import datetime
from uuid import UUID
from enum import Enum

from src.domain.entities.library import Library, IndexType
from src.domain.entities.chunk import Chunk
from src.domain.entities.document import Document


class ExtendedJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles additional types."""
    
    def default(self, obj):
        if isinstance(obj, (datetime,)):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


class MessagePackSerializer:
    """MessagePack serializer with custom type support."""
    
    @staticmethod
    def encode(obj: Any) -> bytes:
        """Encode object to MessagePack bytes."""
        return msgpack.packb(obj, default=MessagePackSerializer._encode_custom, use_bin_type=True)
    
    @staticmethod
    def decode(data: bytes) -> Any:
        """Decode MessagePack bytes to object."""
        return msgpack.unpackb(data, object_hook=MessagePackSerializer._decode_custom, raw=False)
    
    @staticmethod
    def _encode_custom(obj):
        """Encode custom types for MessagePack."""
        if isinstance(obj, datetime):
            return {'__datetime__': True, 'data': obj.isoformat()}
        elif isinstance(obj, UUID):
            return {'__uuid__': True, 'data': str(obj)}
        elif isinstance(obj, np.ndarray):
            return {
                '__ndarray__': True,
                'data': obj.tolist(),
                'dtype': str(obj.dtype),
                'shape': obj.shape
            }
        elif isinstance(obj, Enum):
            return {'__enum__': True, 'class': obj.__class__.__name__, 'value': obj.value}
        elif isinstance(obj, (Library, Chunk, Document)):
            return {
                '__entity__': True,
                'class': obj.__class__.__name__,
                'data': obj.__dict__
            }
        return obj
    
    @staticmethod
    def _decode_custom(obj):
        """Decode custom types from MessagePack."""
        if '__datetime__' in obj:
            return datetime.fromisoformat(obj['data'])
        elif '__uuid__' in obj:
            return UUID(obj['data'])
        elif '__ndarray__' in obj:
            return np.array(obj['data'], dtype=obj['dtype']).reshape(obj['shape'])
        elif '__enum__' in obj:
            # Simple mapping for IndexType
            if obj['class'] == 'IndexType':
                return IndexType(obj['value'])
            return obj['value']
        elif '__entity__' in obj:
            # Entity reconstruction would need proper factory
            # For now, return the data dict
            return obj['data']
        return obj


class VectorSerializer:
    """Specialized serializer for vector embeddings."""
    
    @staticmethod
    def serialize_vectors(vectors: List[np.ndarray]) -> bytes:
        """Serialize multiple vectors efficiently."""
        if not vectors:
            return b''
        
        # Assume all vectors have same dimension
        dim = vectors[0].shape[0]
        num_vectors = len(vectors)
        
        # Stack vectors into single array
        stacked = np.vstack(vectors).astype(np.float32)
        
        # Create header: num_vectors (4 bytes) + dimension (4 bytes)
        header = np.array([num_vectors, dim], dtype=np.int32)
        
        # Concatenate header and data
        return header.tobytes() + stacked.tobytes()
    
    @staticmethod
    def deserialize_vectors(data: bytes) -> List[np.ndarray]:
        """Deserialize vectors from bytes."""
        if not data:
            return []
        
        # Read header
        header = np.frombuffer(data[:8], dtype=np.int32)
        num_vectors, dim = header
        
        # Read vectors
        vectors_data = np.frombuffer(data[8:], dtype=np.float32)
        vectors_array = vectors_data.reshape((num_vectors, dim))
        
        # Convert to list of arrays
        return [vectors_array[i] for i in range(num_vectors)]


class StateSerializer:
    """Serializer for complete system state."""
    
    @staticmethod
    def serialize_state(state: Dict[str, Any]) -> bytes:
        """Serialize complete system state."""
        # Separate vectors from other data
        vectors_data = {}
        other_data = {}
        
        for key, value in state.items():
            if key.endswith('_vectors') and isinstance(value, list):
                # Assume it's a list of vectors
                vectors_data[key] = value
            else:
                other_data[key] = value
        
        # Serialize vectors separately for efficiency
        serialized_vectors = {}
        for key, vectors in vectors_data.items():
            if vectors and isinstance(vectors[0], np.ndarray):
                serialized_vectors[key] = VectorSerializer.serialize_vectors(vectors)
            else:
                serialized_vectors[key] = b''
        
        # Combine everything
        complete_state = {
            'data': other_data,
            'vectors': {k: v.hex() for k, v in serialized_vectors.items()},
            'version': '1.0'
        }
        
        return MessagePackSerializer.encode(complete_state)
    
    @staticmethod
    def deserialize_state(data: bytes) -> Dict[str, Any]:
        """Deserialize complete system state."""
        complete_state = MessagePackSerializer.decode(data)
        
        if 'version' not in complete_state:
            raise ValueError("Invalid state format: missing version")
        
        # Restore other data
        state = complete_state['data']
        
        # Restore vectors
        if 'vectors' in complete_state:
            for key, hex_data in complete_state['vectors'].items():
                if hex_data:
                    vector_bytes = bytes.fromhex(hex_data)
                    state[key] = VectorSerializer.deserialize_vectors(vector_bytes)
                else:
                    state[key] = []
        
        return state
