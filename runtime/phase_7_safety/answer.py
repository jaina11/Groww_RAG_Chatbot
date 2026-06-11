"""Wire Phase 5 retrieval, Phase 6 generation, and Phase 7 safety routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv

from runtime.phase_5_retrieval.logging_config import setup_runtime_logger
from runtime.phase_5_retrieval.retriever import retrieve
from runtime.phase_6_generation.allowlist import load_allowlisted_urls
from runtime.phase_6_generation.generator import GenerationResult, generate_answer
from runtime.phase_7_safety.post_check import check_generated_answer, contains_forbidden_phrase
from runtime.phase_7_safety.router import AMFI_EDUCATION_URL, build_refusal_message, route_query


@dataclass(frozen=True)
class AnswerResult:
    """End-to-end safe answer for a user query."""

    query: str
    answer: str
    route: str
    refused: bool
    citation_url: Optional[str]
    fetched_at: Optional[str]
    matched_keyword: Optional[str]
    validation_passed: bool
    regenerated: bool
    used_fallback: bool
    validation_errors: List[str]
    forbidden_phrases_found: List[str]


def _load_environment() -> None:
    """
    Load environment variables from a local .env file when present.
    """
    load_dotenv()


def answer(query: str) -> AnswerResult:
    """
    Route the query, refuse advisory prompts, otherwise retrieve and generate.

    Applies post-generation forbidden-phrase and compliance checks via Phase 6,
    with an additional safety-layer log when forbidden phrases are detected.
    """
    _load_environment()
    logger = setup_runtime_logger("runtime.phase_7_safety")

    decision = route_query(query)
    if decision.is_advisory:
        logger.info(
            "advisory refusal: query=%r matched_keyword=%s",
            query,
            decision.matched_keyword,
        )
        return AnswerResult(
            query=query,
            answer=build_refusal_message(),
            route="advisory",
            refused=True,
            citation_url=AMFI_EDUCATION_URL,
            fetched_at=None,
            matched_keyword=decision.matched_keyword,
            validation_passed=True,
            regenerated=False,
            used_fallback=False,
            validation_errors=[],
            forbidden_phrases_found=[],
        )

    retrieval = retrieve(query)
    generation: GenerationResult = generate_answer(query, retrieval_result=retrieval)

    allowlisted_urls = load_allowlisted_urls()
    validation = check_generated_answer(generation.answer, allowlisted_urls)
    forbidden_found = contains_forbidden_phrase(generation.answer)
    if forbidden_found:
        logger.warning(
            "forbidden phrases in generated answer: query=%r phrases=%s",
            query,
            forbidden_found,
        )

    logger.info(
        "answer complete: query=%r route=factual refused=%s validation_passed=%s",
        query,
        False,
        generation.validation_passed and validation.passed,
    )
    return AnswerResult(
        query=query,
        answer=generation.answer,
        route="factual",
        refused=False,
        citation_url=generation.citation_url,
        fetched_at=generation.fetched_at,
        matched_keyword=None,
        validation_passed=generation.validation_passed and validation.passed,
        regenerated=generation.regenerated,
        used_fallback=generation.used_fallback,
        validation_errors=generation.validation_errors or validation.errors,
        forbidden_phrases_found=forbidden_found,
    )
