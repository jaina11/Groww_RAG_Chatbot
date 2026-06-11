"""Orchestrate retrieval, Groq generation, and post-generation checks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv

from runtime.phase_5_retrieval.retriever import RetrievalResult, retrieve
from runtime.phase_5_retrieval.scheme_resolver import resolve_scheme_id
from runtime.phase_6_generation.allowlist import load_allowlisted_urls
from runtime.phase_6_generation.groq_client import GroqClient
from runtime.phase_6_generation.post_check import (
    FOOTER_PREFIX,
    FORBIDDEN_PHRASES,
    URL_PATTERN,
    ValidationResult,
    count_sentences,
    extract_urls,
    validate_response,
)
from runtime.phase_6_generation.prompt_builder import build_messages
from runtime.phase_5_retrieval.logging_config import setup_runtime_logger
from runtime.phase_7_safety.safety import is_scheme_scoped_query

EMPTY_INDEX_MESSAGE = (
    "Data not yet indexed. Please try after the next scheduled update."
)
GROQ_FAILURE_MESSAGE = (
    "Unable to process your query right now. Please try again."
)
DEFAULT_MAX_SENTENCES = 3
HOLDINGS_MAX_SENTENCES = 5
HOLDINGS_QUERY_KEYWORDS = (
    "holdings",
    "portfolio",
    "stocks held",
)
HOLDINGS_TOP_N = 5
UNSCOPED_QUERY_ADDENDUM = (
    "NOTE: The user did not name a specific fund. "
    "Answer using only the PRIMARY CITATION scheme from the retrieved context. "
    "Do not list facts for multiple schemes in the same answer."
)
HOLDINGS_QUERY_ADDENDUM = (
    "If asked about top holdings or portfolio, list the top 5 holdings by weight "
    "percentage from the context. Format as:\n"
    "1. Company Name - X%\n"
    "2. Company Name - X%\n"
    "This counts as one response unit, not 5 sentences."
)


@dataclass(frozen=True)
class GenerationResult:
    """Final generation output for a user query."""

    query: str
    answer: str
    citation_url: Optional[str]
    fetched_at: Optional[str]
    validation_passed: bool
    regenerated: bool
    used_fallback: bool
    validation_errors: List[str]


def _load_environment() -> None:
    """
    Load environment variables from a local .env file when present.
    """
    load_dotenv()


def _format_fetched_at(fetched_at: str) -> str:
    """
    Reduce an ISO timestamp to a YYYY-MM-DD footer date.
    """
    return fetched_at[:10] if fetched_at else "unknown"


def _is_holdings_query(query: str) -> bool:
    """
    Return True when the user is asking about fund holdings or portfolio composition.
    """
    normalized = " ".join(query.lower().split())
    return any(keyword in normalized for keyword in HOLDINGS_QUERY_KEYWORDS)


def _uses_holdings_relaxed_validation(query: str) -> bool:
    """
    Return True when holdings/portfolio answers skip sentence-count validation.
    """
    normalized = " ".join(query.lower().split())
    return "holdings" in normalized or "portfolio" in normalized


def _max_sentences_for_query(query: str) -> int:
    """
    Return the allowed body sentence limit for a query type.
    """
    if _is_holdings_query(query):
        return HOLDINGS_MAX_SENTENCES
    return DEFAULT_MAX_SENTENCES


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


def _extract_footer_date(text: str) -> str:
    """
    Return the footer date portion when the required footer line is present.
    """
    for line in text.splitlines():
        if line.strip().lower().startswith(FOOTER_PREFIX.lower()):
            return line.split(":", 1)[-1].strip()
    return ""


def _validate_answer(
    text: str,
    allowlisted_urls: set[str],
    max_sentences: int,
    query: str = "",
) -> ValidationResult:
    """
    Validate generated output against the configured sentence limit.
    """
    if _uses_holdings_relaxed_validation(query):
        errors: List[str] = []
        urls = [url.rstrip(".,);]") for url in extract_urls(text)]
        if len(urls) != 1:
            errors.append(f"url_count={len(urls)}")
        elif urls[0] not in allowlisted_urls:
            errors.append("url_not_allowlisted")

        lowered = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                errors.append(f"forbidden_phrase:{phrase}")

        return ValidationResult(passed=not errors, errors=errors)

    if max_sentences == DEFAULT_MAX_SENTENCES:
        return validate_response(text, allowlisted_urls)

    errors: List[str] = []
    body = _body_text(text)
    sentence_count = count_sentences(body)
    if sentence_count > max_sentences:
        errors.append(f"sentence_count>{max_sentences}")

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


def _retrieve_for_query(query: str, logger) -> RetrievalResult:
    """
    Retrieve context, searching all schemes when no fund is named in the query.
    """
    scheme_id = resolve_scheme_id(query)
    if scheme_id:
        logger.info(
            "retrieval scoped to scheme: query=%r scheme_id=%s",
            query,
            scheme_id,
        )
    else:
        logger.info(
            "retrieval unscoped across all schemes: query=%r scheme_filter=None",
            query,
        )
    return retrieve(query)


def _log_validation_failure(
    logger,
    *,
    query: str,
    answer: str,
    validation: ValidationResult,
    max_sentences: int,
    attempt: str,
) -> None:
    """
    Log detailed validation diagnostics when generation output fails checks.
    """
    body = _body_text(answer)
    sentence_count = count_sentences(body)
    urls = [url.rstrip(".,);]") for url in extract_urls(answer)]
    footer_date = _extract_footer_date(answer)
    forbidden = [
        phrase for phrase in FORBIDDEN_PHRASES if phrase in answer.lower()
    ]
    logger.warning(
        (
            "validation failed (%s): query=%r max_sentences=%s errors=%s "
            "sentence_count=%s url_count=%s urls=%s footer_present=%s "
            "forbidden_phrases=%s body_preview=%r"
        ),
        attempt,
        query,
        max_sentences,
        validation.errors,
        sentence_count,
        len(urls),
        urls,
        bool(footer_date),
        forbidden,
        body[:240],
    )


def _apply_query_instructions_to_messages(
    messages: List[dict],
    *,
    query: str,
    max_sentences: int,
) -> List[dict]:
    """
    Patch prompts for holdings limits and unscoped fund queries.
    """
    adjusted = _apply_sentence_limit_to_messages(messages, max_sentences)
    addenda: List[str] = []
    if _is_holdings_query(query):
        addenda.append(HOLDINGS_QUERY_ADDENDUM)
    if not is_scheme_scoped_query(query):
        addenda.append(UNSCOPED_QUERY_ADDENDUM)
    if not addenda:
        return adjusted

    patched: List[dict] = []
    for message in adjusted:
        if message["role"] != "system":
            patched.append(message)
            continue
        patched.append(
            {
                **message,
                "content": f"{message['content']}\n" + "\n".join(addenda),
            }
        )
    return patched


def _apply_sentence_limit_to_messages(messages: List[dict], max_sentences: int) -> List[dict]:
    """
    Adjust prompt instructions to match the allowed sentence limit for this query.
    """
    if max_sentences == DEFAULT_MAX_SENTENCES:
        return messages

    adjusted: List[dict] = []
    for message in messages:
        content = str(message["content"])
        content = content.replace(
            "Use at most 3 short factual sentences in the body.",
            f"Use at most {max_sentences} short factual sentences in the body.",
        )
        content = content.replace(
            "Reply again with at most 3 short sentences",
            f"Reply again with at most {max_sentences} short sentences",
        )
        adjusted.append({**message, "content": content})
    return adjusted


def _fallback_answer(citation_url: str, fetched_at: str) -> str:
    """
    Return a safe templated answer when generation fails validation.
    """
    footer_date = _format_fetched_at(fetched_at)
    return (
        "I could not generate a compliant answer from the indexed sources. "
        f"Please refer to the scheme page for verified fund details.\n"
        f"{citation_url}\n\n"
        f"Last updated from sources: {footer_date}"
    )


def generate_answer(
    query: str,
    retrieval_result: Optional[RetrievalResult] = None,
    groq_client: Optional[GroqClient] = None,
) -> GenerationResult:
    """
    Retrieve context, call Groq, validate output, and retry or fall back if needed.
    """
    _load_environment()
    logger = setup_runtime_logger("runtime.phase_6_generation")
    allowlisted_urls = load_allowlisted_urls()

    retrieval = retrieval_result or _retrieve_for_query(query, logger)
    if not retrieval.chunks or not retrieval.citation_url:
        logger.info("generation skipped: empty index for query=%r", query)
        return GenerationResult(
            query=query,
            answer=EMPTY_INDEX_MESSAGE,
            citation_url=None,
            fetched_at=None,
            validation_passed=True,
            regenerated=False,
            used_fallback=False,
            validation_errors=[],
        )

    top_metadata = retrieval.chunks[0].metadata
    citation_url = retrieval.citation_url
    fetched_at = str(top_metadata.get("fetched_at", ""))
    client = groq_client or GroqClient()

    regenerated = False
    used_fallback = False
    validation_errors: List[str] = []
    max_sentences = _max_sentences_for_query(query)

    try:
        messages = _apply_query_instructions_to_messages(
            build_messages(
                query=query,
                chunks=retrieval.chunks,
                citation_url=citation_url,
                fetched_at=fetched_at,
                strict=False,
            ),
            query=query,
            max_sentences=max_sentences,
        )
        answer = client.complete(messages)

        validation = _validate_answer(
            answer, allowlisted_urls, max_sentences, query=query
        )
        if not validation.passed:
            validation_errors = validation.errors
            _log_validation_failure(
                logger,
                query=query,
                answer=answer,
                validation=validation,
                max_sentences=max_sentences,
                attempt="initial",
            )
            regenerated = True
            strict_messages = _apply_query_instructions_to_messages(
                build_messages(
                    query=query,
                    chunks=retrieval.chunks,
                    citation_url=citation_url,
                    fetched_at=fetched_at,
                    strict=True,
                ),
                query=query,
                max_sentences=max_sentences,
            )
            answer = client.complete(strict_messages, temperature=0.0)
            validation = _validate_answer(
                answer, allowlisted_urls, max_sentences, query=query
            )
            if not validation.passed:
                _log_validation_failure(
                    logger,
                    query=query,
                    answer=answer,
                    validation=validation,
                    max_sentences=max_sentences,
                    attempt="strict_retry",
                )

        if not validation.passed:
            validation_errors = validation.errors
            used_fallback = True
            answer = _fallback_answer(citation_url, fetched_at)
            validation = _validate_answer(
                answer, allowlisted_urls, DEFAULT_MAX_SENTENCES, query=query
            )
    except Exception as exc:
        logger.error("generation failed: query=%r error=%s", query, exc)
        return GenerationResult(
            query=query,
            answer=GROQ_FAILURE_MESSAGE,
            citation_url=citation_url,
            fetched_at=fetched_at,
            validation_passed=False,
            regenerated=regenerated,
            used_fallback=True,
            validation_errors=[str(exc)],
        )

    logger.info(
        "generation complete: query=%r validation_passed=%s regenerated=%s used_fallback=%s",
        query,
        validation.passed,
        regenerated,
        used_fallback,
    )
    return GenerationResult(
        query=query,
        answer=answer,
        citation_url=citation_url,
        fetched_at=fetched_at,
        validation_passed=validation.passed,
        regenerated=regenerated,
        used_fallback=used_fallback,
        validation_errors=validation.errors if not validation.passed else [],
    )
