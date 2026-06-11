"""Orchestrate normalize + chunk over raw HTML scrape outputs."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ingest.phase_4_0_scraper.logging_config import setup_ingest_logger
from ingest.phase_4_0_scraper.scraper import SchemeEntry, load_url_registry
from ingest.phase_4_1_normalize.chunker import TextChunk, build_chunks
from ingest.phase_4_1_normalize.normalize import clean_html

RAW_FILE_PATTERN = re.compile(r"^(?P<scheme_id>[a-z0-9_]+)_(?P<date>\d{8})\.html$")


@dataclass(frozen=True)
class NormalizeResult:
    """Outcome of normalizing and chunking one raw HTML file."""

    scheme_id: str
    success: bool
    raw_path: Optional[Path] = None
    normalized_path: Optional[Path] = None
    chunks_path: Optional[Path] = None
    chunk_count: int = 0
    error: Optional[str] = None


def _parse_raw_filename(path: Path) -> Optional[Tuple[str, str]]:
    """
    Parse scheme_id and YYYYMMDD date from a raw HTML filename.
    """
    match = RAW_FILE_PATTERN.match(path.name)
    if not match:
        return None
    return match.group("scheme_id"), match.group("date")


def _fetched_at_from_date(date_stamp: str) -> str:
    """
    Convert a YYYYMMDD filename stamp into an ISO-8601 UTC timestamp.
    """
    parsed = datetime.strptime(date_stamp, "%Y%m%d").replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def _find_latest_raw_files(raw_dir: Path) -> Dict[str, Path]:
    """
    Return the newest raw HTML file per scheme_id based on the date in the filename.
    """
    latest: Dict[str, Tuple[str, Path]] = {}
    for path in sorted(raw_dir.glob("*.html")):
        parsed = _parse_raw_filename(path)
        if not parsed:
            continue
        scheme_id, date_stamp = parsed
        current = latest.get(scheme_id)
        if current is None or date_stamp > current[0]:
            latest[scheme_id] = (date_stamp, path)
    return {scheme_id: path for scheme_id, (_, path) in latest.items()}


def _registry_by_scheme_id(registry_path: Path) -> Dict[str, SchemeEntry]:
    """
    Load the URL registry keyed by scheme_id.
    """
    return {entry.scheme_id: entry for entry in load_url_registry(registry_path)}


def _serialize_chunks(chunks: List[TextChunk]) -> List[dict]:
    """
    Convert TextChunk objects into JSON-serializable dictionaries.
    """
    return [{"text": chunk.text, "metadata": chunk.metadata} for chunk in chunks]


def process_raw_file(
    raw_path: Path,
    entry: SchemeEntry,
    normalized_dir: Path,
    chunks_dir: Path,
    logger,
) -> NormalizeResult:
    """
    Normalize one raw HTML file and write normalized text plus chunk JSON.
    """
    parsed = _parse_raw_filename(raw_path)
    if not parsed:
        return NormalizeResult(
            scheme_id=entry.scheme_id,
            success=False,
            raw_path=raw_path,
            error="invalid_raw_filename",
        )

    scheme_id, date_stamp = parsed
    fetched_at = _fetched_at_from_date(date_stamp)

    try:
        html = raw_path.read_text(encoding="utf-8")
        if not html.strip():
            logger.error("empty raw html: path=%s", raw_path)
            return NormalizeResult(
                scheme_id=scheme_id,
                success=False,
                raw_path=raw_path,
                error="empty_raw_html",
            )

        normalized_text = clean_html(html)
        if not normalized_text.strip():
            logger.error("normalization produced empty text: path=%s", raw_path)
            return NormalizeResult(
                scheme_id=scheme_id,
                success=False,
                raw_path=raw_path,
                error="empty_normalized_text",
            )

        chunks = build_chunks(
            text=normalized_text,
            source_url=entry.url,
            scheme_id=entry.scheme_id,
            scheme_name=entry.scheme_name,
            amc=entry.amc,
            fetched_at=fetched_at,
        )
        if not chunks:
            logger.error("chunking produced no chunks: path=%s", raw_path)
            return NormalizeResult(
                scheme_id=scheme_id,
                success=False,
                raw_path=raw_path,
                error="no_chunks",
            )

        normalized_dir.mkdir(parents=True, exist_ok=True)
        chunks_dir.mkdir(parents=True, exist_ok=True)

        normalized_path = normalized_dir / f"{scheme_id}_{date_stamp}.txt"
        chunks_path = chunks_dir / f"{scheme_id}_{date_stamp}.json"

        normalized_path.write_text(normalized_text, encoding="utf-8")
        payload = {
            "scheme_id": scheme_id,
            "source_url": entry.url,
            "scheme_name": entry.scheme_name,
            "amc": entry.amc,
            "fetched_at": fetched_at,
            "chunk_count": len(chunks),
            "chunks": _serialize_chunks(chunks),
        }
        chunks_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        logger.info(
            "normalized and chunked: scheme_id=%s raw=%s chunks=%s normalized=%s output=%s",
            scheme_id,
            raw_path,
            len(chunks),
            normalized_path,
            chunks_path,
        )
        return NormalizeResult(
            scheme_id=scheme_id,
            success=True,
            raw_path=raw_path,
            normalized_path=normalized_path,
            chunks_path=chunks_path,
            chunk_count=len(chunks),
        )
    except Exception as exc:
        logger.error(
            "normalize failed: scheme_id=%s path=%s error=%s",
            scheme_id,
            raw_path,
            exc,
        )
        return NormalizeResult(
            scheme_id=scheme_id,
            success=False,
            raw_path=raw_path,
            error=str(exc),
        )


def run_normalize(
    raw_dir: Optional[Path] = None,
    normalized_dir: Optional[Path] = None,
    chunks_dir: Optional[Path] = None,
    registry_path: Optional[Path] = None,
) -> List[NormalizeResult]:
    """
    Normalize and chunk the latest raw HTML file for each scheme in the registry.

    Reads RAW_DATA_DIR, NORMALIZED_DATA_DIR, and CHUNKS_DATA_DIR from the
    environment when paths are not provided explicitly.
    """
    logger = setup_ingest_logger("ingest.phase_4_1_normalize")
    scraper_dir = Path(__file__).resolve().parent.parent / "phase_4_0_scraper"
    registry_path = registry_path or scraper_dir / "url_registry.json"
    raw_dir = raw_dir or Path(os.environ.get("RAW_DATA_DIR", "data/raw"))
    normalized_dir = normalized_dir or Path(
        os.environ.get("NORMALIZED_DATA_DIR", "data/normalized")
    )
    chunks_dir = chunks_dir or Path(os.environ.get("CHUNKS_DATA_DIR", "data/chunks"))

    logger.info(
        "starting normalize run: raw_dir=%s normalized_dir=%s chunks_dir=%s",
        raw_dir,
        normalized_dir,
        chunks_dir,
    )

    if not raw_dir.exists():
        logger.error("raw directory missing: %s", raw_dir)
        return []

    registry = _registry_by_scheme_id(registry_path)
    latest_raw_files = _find_latest_raw_files(raw_dir)
    results: List[NormalizeResult] = []

    for scheme_id, entry in registry.items():
        raw_path = latest_raw_files.get(scheme_id)
        if raw_path is None:
            logger.error("no raw html found for scheme_id=%s", scheme_id)
            results.append(
                NormalizeResult(
                    scheme_id=scheme_id,
                    success=False,
                    error="missing_raw_html",
                )
            )
            continue

        results.append(
            process_raw_file(
                raw_path=raw_path,
                entry=entry,
                normalized_dir=normalized_dir,
                chunks_dir=chunks_dir,
                logger=logger,
            )
        )

    success_count = sum(1 for result in results if result.success)
    logger.info(
        "normalize run complete: total=%s success=%s failed=%s",
        len(results),
        success_count,
        len(results) - success_count,
    )
    return results
