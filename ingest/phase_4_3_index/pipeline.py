"""Load embedded JSONL files and upsert them into ChromaDB."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ingest.phase_4_0_scraper.logging_config import setup_ingest_logger
from ingest.phase_4_3_index.indexer import ChromaIndexer


@dataclass(frozen=True)
class IndexResult:
    """Outcome of indexing one embedded JSONL file."""

    embedded_path: Path
    success: bool
    upsert_count: int = 0
    error: Optional[str] = None


def _load_jsonl(embedded_path: Path) -> List[Dict[str, object]]:
    """
    Load embedded records from a JSONL file.
    """
    records: List[Dict[str, object]] = []
    for line in embedded_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def _write_manifest(
    manifest_path: Path,
    indexer: ChromaIndexer,
    chunk_count: int,
    run_id: str,
    indexed_at: str,
) -> None:
    """
    Emit the operator manifest for this index run.
    """
    manifest = {
        "embedding_model_id": indexer.embedding_model_id,
        "run_id": run_id,
        "collection_name": indexer.collection_name,
        "chroma_persist_path": indexer.chroma_dir,
        "chunk_count": chunk_count,
        "updated_at": indexed_at,
        "indexed_at": indexed_at,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def index_embedded_file(
    embedded_path: Path,
    indexer: ChromaIndexer,
    logger,
) -> IndexResult:
    """
    Upsert all records from one embedded JSONL file into Chroma.
    """
    try:
        records = _load_jsonl(embedded_path)
        if not records:
            logger.error("no embedded records found: path=%s", embedded_path)
            return IndexResult(
                embedded_path=embedded_path,
                success=False,
                error="no_records",
            )

        upsert_count = indexer.upsert_records(records)
        logger.info(
            "upserted chunks: input=%s upsert_count=%s",
            embedded_path,
            upsert_count,
        )
        return IndexResult(
            embedded_path=embedded_path,
            success=True,
            upsert_count=upsert_count,
        )
    except Exception as exc:
        logger.error("index failed: path=%s error=%s", embedded_path, exc)
        return IndexResult(
            embedded_path=embedded_path,
            success=False,
            error=str(exc),
        )


def run_index(
    embedded_dir: Optional[Path] = None,
    chroma_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> List[IndexResult]:
    """
    Upsert all embedded JSONL files into the persistent Chroma collection.

    Writes data/chroma/manifest.json and logs total upsert count to logs/ingest.log.
    """
    logger = setup_ingest_logger("ingest.phase_4_3_index")
    embedded_dir = embedded_dir or Path(os.environ.get("EMBEDDED_DATA_DIR", "data/embedded"))
    chroma_path = chroma_dir or os.environ.get("CHROMA_DIR", "data/chroma/")

    logger.info(
        "starting index run: embedded_dir=%s chroma_dir=%s collection=%s",
        embedded_dir,
        chroma_path,
        collection_name or os.environ.get("CHROMA_COLLECTION", "mf_faq_chunks"),
    )

    if not embedded_dir.exists():
        logger.error("embedded directory missing: %s", embedded_dir)
        return []

    embedded_files = sorted(embedded_dir.glob("*.jsonl"))
    if not embedded_files:
        logger.error("no embedded jsonl files found in %s", embedded_dir)
        return []

    indexer = ChromaIndexer(chroma_dir=chroma_path, collection_name=collection_name)
    results: List[IndexResult] = []
    total_upserts = 0

    for embedded_path in embedded_files:
        result = index_embedded_file(
            embedded_path=embedded_path,
            indexer=indexer,
            logger=logger,
        )
        results.append(result)
        if result.success:
            total_upserts += result.upsert_count

    indexed_at = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())
    manifest_path = Path(chroma_path) / "manifest.json"
    _write_manifest(
        manifest_path=manifest_path,
        indexer=indexer,
        chunk_count=total_upserts,
        run_id=run_id,
        indexed_at=indexed_at,
    )

    success_count = sum(1 for result in results if result.success)
    logger.info(
        "index run complete: files=%s success=%s failed=%s upsert_count=%s collection=%s manifest=%s",
        len(results),
        success_count,
        len(results) - success_count,
        total_upserts,
        indexer.collection_name,
        manifest_path,
    )
    return results
