"""Deterministic chunk identifiers for idempotent Chroma upserts."""

from __future__ import annotations

import hashlib


def make_chunk_id(source_url: str, chunk_index: int) -> str:
    """
    Build a stable chunk_id from source_url and chunk_index.

    Uses SHA-256 so repeated ingest runs upsert the same logical chunk.
    """
    payload = f"{source_url}|{chunk_index}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
