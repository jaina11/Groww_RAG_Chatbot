"""Safety-layer wrappers around post-generation validation."""

from __future__ import annotations

from typing import List, Set

from runtime.phase_6_generation.post_check import (
    FORBIDDEN_PHRASES,
    ValidationResult,
    validate_response,
)


def contains_forbidden_phrase(text: str) -> List[str]:
    """
    Return any forbidden advisory phrases found in generated text.
    """
    lowered = text.lower()
    return [phrase for phrase in FORBIDDEN_PHRASES if phrase in lowered]


def check_generated_answer(text: str, allowlisted_urls: Set[str]) -> ValidationResult:
    """
    Run the full post-generation compliance check on an assistant answer.
    """
    return validate_response(text, allowlisted_urls)
