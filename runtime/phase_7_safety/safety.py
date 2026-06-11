"""Safety routing: factual keyword exemptions and advisory detection."""

from __future__ import annotations

import re
from dataclasses import dataclass

from runtime.phase_5_retrieval.scheme_resolver import resolve_scheme_id

AMFI_EDUCATION_URL = "https://www.amfiindia.com/investor-corner/knowledge-center"

FACTUAL_KEYWORDS = (
    "top holdings",
    "holdings",
    "expense ratio",
    "exit load",
    "minimum sip",
    "portfolio",
    "stocks held",
)

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


def _matches_factual_keyword(normalized: str) -> bool:
    """
    Return True when the query clearly asks for indexed factual fund data.
    """
    return any(keyword in normalized for keyword in FACTUAL_KEYWORDS)


def is_scheme_scoped_query(query: str) -> bool:
    """
    Return True when the query names a specific indexed HDFC scheme.
    """
    return resolve_scheme_id(query) is not None


def route_query(query: str) -> RouteDecision:
    """
    Detect advisory or comparative queries that must be refused before retrieval.

    Factual keywords such as holdings are checked first so legitimate fund
    fact queries are not misrouted as advisory.
    """
    normalized = _normalize_query(query)

    if _matches_factual_keyword(normalized):
        return RouteDecision(query=query, is_advisory=False)

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
