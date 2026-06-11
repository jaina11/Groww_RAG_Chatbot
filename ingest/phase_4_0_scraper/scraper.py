"""Allowlisted HTTP scraper for Groww scheme pages."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from ingest.phase_4_0_scraper.logging_config import setup_ingest_logger

DEFAULT_USER_AGENT = (
    "M2-RAG-Chatbot-Scraper/1.0 (+https://github.com; facts-only MF FAQ assistant)"
)
DEFAULT_REQUEST_TIMEOUT_SEC = 30
DEFAULT_RATE_LIMIT_SEC = 2.0


@dataclass(frozen=True)
class SchemeEntry:
    """One allowlisted scheme URL from the registry."""

    scheme_id: str
    scheme_name: str
    amc: str
    source_type: str
    url: str


@dataclass(frozen=True)
class ScrapeResult:
    """Outcome of scraping a single allowlisted URL."""

    entry: SchemeEntry
    success: bool
    output_path: Optional[Path] = None
    status_code: Optional[int] = None
    error: Optional[str] = None


def load_url_registry(registry_path: Path) -> List[SchemeEntry]:
    """
    Load the versioned allowlist of scheme URLs from JSON.

    Raises FileNotFoundError or json.JSONDecodeError if the registry is invalid.
    """
    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    entries: List[SchemeEntry] = []
    for item in raw:
        entries.append(
            SchemeEntry(
                scheme_id=item["scheme_id"],
                scheme_name=item["scheme_name"],
                amc=item["amc"],
                source_type=item["source_type"],
                url=item["url"],
            )
        )
    return entries


def _build_robot_parser(url: str) -> Optional[RobotFileParser]:
    """
    Fetch and parse robots.txt for the origin of the given URL.

    Returns None when robots.txt cannot be retrieved (caller may proceed).
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception:
        return None
    return parser


def _is_allowed_by_robots(url: str, user_agent: str, logger) -> bool:
    """
    Return True if robots.txt permits fetching the URL for this user agent.
    """
    parser = _build_robot_parser(url)
    if parser is None:
        logger.warning("robots.txt unavailable; proceeding cautiously: url=%s", url)
        return True
    allowed = parser.can_fetch(user_agent, url)
    if not allowed:
        logger.warning("robots.txt disallows fetch: url=%s", url)
    return allowed


def _output_path_for_scheme(scheme_id: str, raw_dir: Path, fetched_at: datetime) -> Path:
    """
    Build the dated raw HTML path: data/raw/<scheme_id>_<YYYYMMDD>.html.
    """
    date_stamp = fetched_at.strftime("%Y%m%d")
    return raw_dir / f"{scheme_id}_{date_stamp}.html"


def scrape_url(
    entry: SchemeEntry,
    raw_dir: Path,
    user_agent: str,
    timeout_sec: float,
    logger,
    fetched_at: Optional[datetime] = None,
) -> ScrapeResult:
    """
    Fetch one allowlisted URL and persist raw HTML to disk.

    On non-2xx, timeout, empty body, or robots.txt denial, logs the failure
    and returns success=False without raising.
    """
    fetched_at = fetched_at or datetime.now(timezone.utc)
    output_path = _output_path_for_scheme(entry.scheme_id, raw_dir, fetched_at)

    if not _is_allowed_by_robots(entry.url, user_agent, logger):
        return ScrapeResult(
            entry=entry,
            success=False,
            error="blocked_by_robots_txt",
        )

    try:
        response = requests.get(
            entry.url,
            headers={"User-Agent": user_agent},
            timeout=timeout_sec,
        )
    except requests.RequestException as exc:
        logger.error(
            "request failed: scheme_id=%s url=%s error=%s",
            entry.scheme_id,
            entry.url,
            exc,
        )
        return ScrapeResult(
            entry=entry,
            success=False,
            error=str(exc),
        )

    if response.status_code < 200 or response.status_code >= 300:
        logger.error(
            "non-2xx response: scheme_id=%s url=%s status=%s",
            entry.scheme_id,
            entry.url,
            response.status_code,
        )
        return ScrapeResult(
            entry=entry,
            success=False,
            status_code=response.status_code,
            error=f"http_status_{response.status_code}",
        )

    if not response.text or not response.text.strip():
        logger.error(
            "empty response body: scheme_id=%s url=%s status=%s",
            entry.scheme_id,
            entry.url,
            response.status_code,
        )
        return ScrapeResult(
            entry=entry,
            success=False,
            status_code=response.status_code,
            error="empty_body",
        )

    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(response.text, encoding="utf-8")
    logger.info(
        "saved raw html: scheme_id=%s path=%s bytes=%s status=%s",
        entry.scheme_id,
        output_path,
        len(response.text.encode("utf-8")),
        response.status_code,
    )
    return ScrapeResult(
        entry=entry,
        success=True,
        output_path=output_path,
        status_code=response.status_code,
    )


def run_scraper(
    registry_path: Optional[Path] = None,
    raw_dir: Optional[Path] = None,
) -> List[ScrapeResult]:
    """
    Scrape every URL in the allowlist registry with rate limiting.

    Reads RAW_DATA_DIR (default data/raw), SCRAPER_USER_AGENT, REQUEST_TIMEOUT_SEC,
    and RATE_LIMIT_SEC from the environment when not passed explicitly.
    """
    logger = setup_ingest_logger("ingest.phase_4_0_scraper")
    package_dir = Path(__file__).resolve().parent
    registry_path = registry_path or package_dir / "url_registry.json"
    raw_dir = raw_dir or Path(os.environ.get("RAW_DATA_DIR", "data/raw"))

    user_agent = os.environ.get("SCRAPER_USER_AGENT", DEFAULT_USER_AGENT)
    timeout_sec = float(os.environ.get("REQUEST_TIMEOUT_SEC", DEFAULT_REQUEST_TIMEOUT_SEC))
    rate_limit_sec = float(os.environ.get("RATE_LIMIT_SEC", DEFAULT_RATE_LIMIT_SEC))

    logger.info("starting scrape run: registry=%s raw_dir=%s", registry_path, raw_dir)
    entries = load_url_registry(registry_path)
    results: List[ScrapeResult] = []

    for index, entry in enumerate(entries):
        if index > 0 and rate_limit_sec > 0:
            time.sleep(rate_limit_sec)
        results.append(
            scrape_url(
                entry=entry,
                raw_dir=raw_dir,
                user_agent=user_agent,
                timeout_sec=timeout_sec,
                logger=logger,
            )
        )

    success_count = sum(1 for result in results if result.success)
    logger.info(
        "scrape run complete: total=%s success=%s failed=%s",
        len(results),
        success_count,
        len(results) - success_count,
    )
    return results
