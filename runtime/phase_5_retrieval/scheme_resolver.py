"""Resolve scheme_id from a user query when confidence is high."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2]
    / "ingest"
    / "phase_4_0_scraper"
    / "url_registry.json"
)

SCHEME_ALIASES: Dict[str, List[str]] = {
    "hdfc_elss": ["elss", "tax saver", "tax-saver"],
    "hdfc_large_cap": ["large cap", "large-cap", "largecap"],
    "hdfc_mid_cap": ["mid cap", "mid-cap", "midcap"],
    "hdfc_focused": ["focused fund", "focused"],
    "hdfc_equity": ["equity fund", "hdfc equity"],
}


def _normalize_query(query: str) -> str:
    """
    Lowercase and collapse whitespace for alias matching.
    """
    return re.sub(r"\s+", " ", query.lower()).strip()


def load_scheme_aliases(registry_path: Optional[Path] = None) -> List[Tuple[str, List[str]]]:
    """
    Build ordered alias lists from the URL registry and built-in scheme keywords.

    Longer aliases are checked first to reduce accidental partial matches.
    """
    registry_path = registry_path or DEFAULT_REGISTRY_PATH
    entries = json.loads(registry_path.read_text(encoding="utf-8"))

    alias_map: Dict[str, List[str]] = {}
    for entry in entries:
        scheme_id = entry["scheme_id"]
        aliases = set(SCHEME_ALIASES.get(scheme_id, []))
        scheme_name = str(entry.get("scheme_name", "")).lower()
        if scheme_name:
            aliases.add(scheme_name)
        alias_map[scheme_id] = sorted(aliases, key=len, reverse=True)

    ordered: List[Tuple[str, List[str]]] = []
    for scheme_id, aliases in alias_map.items():
        ordered.append((scheme_id, aliases))
    ordered.sort(key=lambda item: max((len(alias) for alias in item[1]), default=0), reverse=True)
    return ordered


def resolve_scheme_id(query: str, registry_path: Optional[Path] = None) -> Optional[str]:
    """
    Return scheme_id when a known scheme alias appears in the query.

    Returns None when no scheme can be resolved with sufficient confidence.
    """
    normalized = _normalize_query(query)
    for scheme_id, aliases in load_scheme_aliases(registry_path):
        for alias in aliases:
            if alias in normalized:
                return scheme_id
    return None
