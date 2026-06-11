"""Read chunk JSON files and write embedded JSONL outputs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ingest.phase_4_0_scraper.logging_config import setup_ingest_logger
from ingest.phase_4_2_embed.embedder import (
    BGEEmbedder,
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
)


@dataclass(frozen=True)
class EmbedResult:
    """Outcome of embedding one chunk JSON file."""

    chunks_path: Path
    success: bool
    embedded_path: Optional[Path] = None
    chunk_count: int = 0
    error: Optional[str] = None


def _load_chunk_file(chunks_path: Path) -> List[Dict[str, object]]:
    """
    Load chunk records from a Phase 4.1 JSON output file.
    """
    payload = json.loads(chunks_path.read_text(encoding="utf-8"))
    chunks = payload.get("chunks", [])
    if not isinstance(chunks, list):
        raise ValueError(f"invalid chunks payload in {chunks_path}")
    return chunks


def _write_jsonl(records: List[Dict[str, object]], output_path: Path) -> None:
    """
    Write embedded records as one JSON object per line.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")


def embed_chunk_file(
    chunks_path: Path,
    embedded_dir: Path,
    embedder: BGEEmbedder,
    logger,
) -> EmbedResult:
    """
    Embed all chunks in one JSON file and write a matching JSONL file.
    """
    try:
        chunk_items = _load_chunk_file(chunks_path)
        if not chunk_items:
            logger.error("no chunks found: path=%s", chunks_path)
            return EmbedResult(
                chunks_path=chunks_path,
                success=False,
                error="no_chunks",
            )

        texts = [str(item["text"]) for item in chunk_items]
        metadata_list = [dict(item["metadata"]) for item in chunk_items]
        embeddings = embedder.embed_passages(texts)

        records: List[Dict[str, object]] = []
        for text, metadata, embedding in zip(texts, metadata_list, embeddings):
            records.append(
                {
                    "text": text,
                    "metadata": metadata,
                    "embedding": embedding,
                }
            )

        output_path = embedded_dir / f"{chunks_path.stem}.jsonl"
        _write_jsonl(records, output_path)
        logger.info(
            "embedded chunks: input=%s output=%s chunk_count=%s",
            chunks_path,
            output_path,
            len(records),
        )
        return EmbedResult(
            chunks_path=chunks_path,
            success=True,
            embedded_path=output_path,
            chunk_count=len(records),
        )
    except Exception as exc:
        logger.error("embed failed: path=%s error=%s", chunks_path, exc)
        return EmbedResult(
            chunks_path=chunks_path,
            success=False,
            error=str(exc),
        )


def run_embed(
    chunks_dir: Optional[Path] = None,
    embedded_dir: Optional[Path] = None,
    model_name: Optional[str] = None,
) -> List[EmbedResult]:
    """
    Embed every JSON chunk file under data/chunks into data/embedded JSONL files.

    Logs total chunk count and embedding model name to logs/ingest.log.
    """
    logger = setup_ingest_logger("ingest.phase_4_2_embed")
    chunks_dir = chunks_dir or Path(os.environ.get("CHUNKS_DATA_DIR", "data/chunks"))
    embedded_dir = embedded_dir or Path(os.environ.get("EMBEDDED_DATA_DIR", "data/embedded"))

    logger.info(
        "starting embed run: chunks_dir=%s embedded_dir=%s",
        chunks_dir,
        embedded_dir,
    )

    if not chunks_dir.exists():
        logger.error("chunks directory missing: %s", chunks_dir)
        return []

    embedder = BGEEmbedder(model_name=model_name)
    logger.info(
        "loaded embedding model: model=%s query_prefix=%r dimension=%s",
        embedder.model_name,
        embedder.query_prefix,
        EMBEDDING_DIMENSION,
    )

    chunk_files = sorted(chunks_dir.glob("*.json"))
    if not chunk_files:
        logger.error("no chunk json files found in %s", chunks_dir)
        return []

    results: List[EmbedResult] = []
    total_chunks = 0
    for chunks_path in chunk_files:
        result = embed_chunk_file(
            chunks_path=chunks_path,
            embedded_dir=embedded_dir,
            embedder=embedder,
            logger=logger,
        )
        results.append(result)
        if result.success:
            total_chunks += result.chunk_count

    success_count = sum(1 for result in results if result.success)
    logger.info(
        "embed run complete: files=%s success=%s failed=%s total_chunks=%s model=%s",
        len(results),
        success_count,
        len(results) - success_count,
        total_chunks,
        embedder.model_name or DEFAULT_EMBEDDING_MODEL,
    )
    return results
