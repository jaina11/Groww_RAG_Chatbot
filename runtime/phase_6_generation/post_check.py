"""Post-generation validation for facts-only responses."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Set

FOOTER_PREFIX = "Last updated from sources:"
MAX_BODY_SENTENCES = 3
URL_PATTERN = re.compile(r"https?://[^\s)>\"]+")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")

FORBIDDEN_PHRASES = [
    "invest in",
    "you should",
    "you should consider",
    "better than",
    "outperform",
    "guarantee",
]


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of post-generation compliance checks."""

    passed: bool
    errors: List[str]


def _extract_footer_date(text: str) -> str:
    """
    Return the footer date portion when the required footer line is present.
    """
    for line in text.splitlines():
        if line.strip().lower().startswith(FOOTER_PREFIX.lower()):
            return line.split(":", 1)[-1].strip()
    return ""


def _body_text(text: str) -> str:
    """
    Return answer body text excluding standalone URL lines and the footer.
    """
    body_lines: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith(FOOTER_PREFIX.lower()):
            continue
        if URL_PATTERN.fullmatch(stripped):
            continue
        body_lines.append(stripped)
    return " ".join(body_lines)


def count_sentences(text: str) -> int:
    """
    Count sentences in a text block using simple punctuation boundaries.
    """
    cleaned = text.strip()
    if not cleaned:
        return 0
    parts = [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(cleaned) if part.strip()]
    return len(parts)


def extract_urls(text: str) -> List[str]:
    """
    Extract HTTP(S) URLs from a response.
    """
    return URL_PATTERN.findall(text)


def validate_response(text: str, allowlisted_urls: Set[str]) -> ValidationResult:
    """
    Validate sentence count, citation URL presence, allowlist, and forbidden phrases.
    """
    errors: List[str] = []
    body = _body_text(text)
    sentence_count = count_sentences(body)
    if sentence_count > MAX_BODY_SENTENCES:
        errors.append(f"sentence_count>{MAX_BODY_SENTENCES}")

    urls = [url.rstrip(".,);]") for url in extract_urls(text)]
    if len(urls) != 1:
        errors.append(f"url_count={len(urls)}")
    elif urls[0] not in allowlisted_urls:
        errors.append("url_not_allowlisted")

    if not _extract_footer_date(text):
        errors.append("missing_footer")

    lowered = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            errors.append(f"forbidden_phrase:{phrase}")

    return ValidationResult(passed=not errors, errors=errors)
