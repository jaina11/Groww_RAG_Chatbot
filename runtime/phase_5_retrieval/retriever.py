"""Dense retrieval from ChromaDB using BGE query embeddings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import chromadb

from ingest.phase_4_2_embed.embedder import BGEEmbedder
from runtime.phase_5_retrieval.logging_config import setup_runtime_logger
from runtime.phase_5_retrieval.scheme_resolver import resolve_scheme_id

DEFAULT_CHROMA_DIR = "data/chroma/"
DEFAULT_COLLECTION_NAME = "mf_faq_chunks"
DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class RetrievedChunk:
    """One retrieved chunk with similarity score."""

    text: str
    metadata: Dict[str, object]
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    """Retrieval output for a single user query."""

    query: str
    chunks: List[RetrievedChunk]
    citation_url: Optional[str]
    scheme_filter: Optional[str] = None


def _distance_to_score(distance: float) -> float:
    """
    Convert Chroma cosine distance to a similarity score in [0, 1].
    """
    return max(0.0, min(1.0, 1.0 - float(distance)))


class ChromaRetriever:
    """Query the persistent Chroma collection with BGE query embeddings."""

    def __init__(
        self,
        chroma_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
        top_k: Optional[int] = None,
        embedder: Optional[BGEEmbedder] = None,
    ) -> None:
        """
        Connect to Chroma and prepare the BGE embedder for query encoding.
        """
        self.chroma_dir = chroma_dir or os.environ.get("CHROMA_DIR", DEFAULT_CHROMA_DIR)
        self.collection_name = collection_name or os.environ.get(
            "CHROMA_COLLECTION", DEFAULT_COLLECTION_NAME
        )
        self.top_k = top_k or int(os.environ.get("RETRIEVAL_TOP_K", DEFAULT_TOP_K))
        self.embedder = embedder or BGEEmbedder()
        self._client = chromadb.PersistentClient(path=self.chroma_dir)
        self._collection = self._client.get_collection(name=self.collection_name)
        self._logger = setup_runtime_logger("runtime.phase_5_retrieval")

    def retrieve(self, query: str) -> RetrievalResult:
        """
        Embed the query, search Chroma for top-k chunks, and pick a citation URL.

        Applies an optional metadata filter on scheme_id when one is detected
        in the query text.
        """
        scheme_id = resolve_scheme_id(query)
        query_embedding = self.embedder.embed_query(query)

        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": self.top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if scheme_id:
            query_kwargs["where"] = {"scheme_id": scheme_id}

        response = self._collection.query(**query_kwargs)

        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]

        chunks: List[RetrievedChunk] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            chunks.append(
                RetrievedChunk(
                    text=str(document),
                    metadata=dict(metadata or {}),
                    score=_distance_to_score(distance),
                )
            )

        citation_url = None
        if chunks:
            citation_url = str(chunks[0].metadata.get("source_url", "")) or None

        self._logger.info(
            "retrieval complete: query=%r scheme_filter=%s retrieval_count=%s citation_url=%s",
            query,
            scheme_id,
            len(chunks),
            citation_url,
        )
        return RetrievalResult(
            query=query,
            chunks=chunks,
            citation_url=citation_url,
            scheme_filter=scheme_id,
        )


def retrieve(query: str) -> RetrievalResult:
    """
    Run dense retrieval for a user query using default runtime configuration.
    """
    retriever = ChromaRetriever()
    return retriever.retrieve(query)
