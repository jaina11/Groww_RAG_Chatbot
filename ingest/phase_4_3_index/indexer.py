"""ChromaDB PersistentClient wrapper for ingest-time upserts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Sequence

import chromadb
from chromadb.api.models.Collection import Collection

from ingest.phase_4_2_embed.embedder import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSION
from ingest.phase_4_3_index.chunk_id import make_chunk_id

DEFAULT_CHROMA_DIR = "data/chroma/"
DEFAULT_COLLECTION_NAME = "mf_faq_chunks"


def _chroma_metadata(metadata: Dict[str, object]) -> Dict[str, str | int | float | bool]:
    """
    Coerce chunk metadata to Chroma-compatible primitive values.
    """
    chroma_meta: Dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            chroma_meta[key] = value
        elif value is None:
            continue
        else:
            chroma_meta[key] = str(value)
    return chroma_meta


class ChromaIndexer:
    """Upsert precomputed embeddings into a persistent Chroma collection."""

    def __init__(
        self,
        chroma_dir: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        """
        Open a persistent Chroma client and get or create the target collection.
        """
        self.chroma_dir = chroma_dir or os.environ.get("CHROMA_DIR", DEFAULT_CHROMA_DIR)
        self.collection_name = collection_name or os.environ.get(
            "CHROMA_COLLECTION", DEFAULT_COLLECTION_NAME
        )
        self.embedding_model_id = os.environ.get(
            "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
        )

        Path(self.chroma_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self.chroma_dir)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def collection(self) -> Collection:
        """Return the active Chroma collection."""
        return self._collection

    def upsert_records(self, records: Sequence[Dict[str, object]]) -> int:
        """
        Upsert embedded JSONL records into Chroma.

        Each record must contain text, metadata, and a 384-dimensional embedding.
        Returns the number of records upserted.
        """
        if not records:
            return 0

        ids: List[str] = []
        embeddings: List[List[float]] = []
        documents: List[str] = []
        metadatas: List[Dict[str, str | int | float | bool]] = []

        for record in records:
            text = str(record["text"])
            metadata = dict(record["metadata"])
            embedding = [float(value) for value in record["embedding"]]

            if len(embedding) != EMBEDDING_DIMENSION:
                raise ValueError(
                    f"expected {EMBEDDING_DIMENSION}-dim embedding, got {len(embedding)}"
                )

            source_url = str(metadata["source_url"])
            chunk_index = int(metadata["chunk_index"])
            chunk_id = make_chunk_id(source_url, chunk_index)

            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(text)
            metadatas.append(_chroma_metadata(metadata))

        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(ids)
