"""Allowlisted citation URLs from the ingest URL registry."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Set

DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2]
    / "ingest"
    / "phase_4_0_scraper"
    / "url_registry.json"
)


@lru_cache(maxsize=1)
def load_allowlisted_urls(registry_path: str | None = None) -> Set[str]:
    """
    Load the set of allowlisted Groww scheme URLs for citation validation.
    """
    path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {str(entry["url"]) for entry in entries}
