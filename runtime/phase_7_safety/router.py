"""Query router for advisory and comparative intents."""

from __future__ import annotations

import re
from dataclasses import dataclass

AMFI_EDUCATION_URL = "https://www.amfiindia.com/investor-corner/knowledge-center"

ADVISORY_KEYWORDS = (
    "should i",
    "which is better",
    "best fund",
    "recommend",
    "good for me",
    "will it give",
    "compare",
)


@dataclass(frozen=True)
class RouteDecision:
    """Outcome of pre-retrieval query routing."""

    query: str
    is_advisory: bool
    matched_keyword: str | None = None


def _normalize_query(query: str) -> str:
    """
    Lowercase and collapse whitespace for keyword matching.
    """
    return re.sub(r"\s+", " ", query.lower()).strip()


def route_query(query: str) -> RouteDecision:
    """
    Detect advisory or comparative queries that must be refused before retrieval.
    """
    normalized = _normalize_query(query)
    for keyword in ADVISORY_KEYWORDS:
        if keyword in normalized:
            return RouteDecision(
                query=query,
                is_advisory=True,
                matched_keyword=keyword,
            )
    return RouteDecision(query=query, is_advisory=False)


def build_refusal_message() -> str:
    """
    Return the polite facts-only refusal with an AMFI educational link.
    """
    return (
        "I can't provide investment advice, fund recommendations, or performance comparisons. "
        "I can only answer factual questions about the indexed HDFC mutual fund schemes.\n\n"
        f"{AMFI_EDUCATION_URL}"
    )
