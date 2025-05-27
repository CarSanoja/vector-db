#!/usr/bin/env python3
"""
Utility: Generate embeddings using sentence-transformers (optional).
"""

try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Note: Install sentence-transformers for real embeddings")
    print("pip install sentence-transformers")

import numpy as np


class EmbeddingGenerator:
    """Generate embeddings for text."""

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        if TRANSFORMERS_AVAILABLE:
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
        else:
            self.model = None
            self.dimension = 384  

    def generate(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for texts."""
        if self.model:
            # Real embeddings
            embeddings = self.model.encode(texts)
            return [emb.astype(np.float32) for emb in embeddings]
        else:
            # Random embeddings as fallback
            embeddings = []
            for text in texts:
                np.random.seed(hash(text) % 2**32)
                emb = np.random.randn(self.dimension).astype(np.float32)
                emb = emb / np.linalg.norm(emb)
                embeddings.append(emb)
            return embeddings



if __name__ == "__main__":
    generator = EmbeddingGenerator()

    texts = [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is transforming the world",
        "Vector databases enable semantic search"
    ]

    embeddings = generator.generate(texts)

    print(f"Generated {len(embeddings)} embeddings")
    print(f"Dimension: {len(embeddings[0])}")
    print(f"First embedding: {embeddings[0][:10]}...")
