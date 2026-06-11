"""Local BGE embedding via sentence-transformers."""

from __future__ import annotations

import os
from typing import List, Sequence

from sentence_transformers import SentenceTransformer

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_QUERY_PREFIX = "Represent this sentence: "
EMBEDDING_DIMENSION = 384


class BGEEmbedder:
    """Embed passage text with BAAI/bge-small-en-v1.5 (384-dimensional vectors)."""

    def __init__(self, model_name: str | None = None) -> None:
        """
        Load the local sentence-transformers model for ingest-time passage embedding.
        """
        self.model_name = model_name or os.environ.get(
            "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
        )
        self.query_prefix = os.environ.get("EMBEDDING_QUERY_PREFIX", DEFAULT_QUERY_PREFIX)
        self._model = SentenceTransformer(self.model_name)

    def embed_passages(self, texts: Sequence[str]) -> List[List[float]]:
        """
        Embed document/passage chunks without the query prefix.

        BGE uses the query prefix only at retrieval time; corpus chunks are encoded
        as plain passage text. Vectors are L2-normalized for cosine similarity.
        """
        if not texts:
            return []

        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        embeddings: List[List[float]] = []
        for vector in vectors:
            embedding = [float(value) for value in vector]
            if len(embedding) != EMBEDDING_DIMENSION:
                raise ValueError(
                    f"expected {EMBEDDING_DIMENSION}-dim embedding, got {len(embedding)}"
                )
            embeddings.append(embedding)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a user query with the BGE retrieval prefix.
        """
        prefixed = f"{self.query_prefix}{text}"
        vectors = self.embed_passages([prefixed])
        return vectors[0]
