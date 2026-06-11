"""Map pipeline results into API response fields."""

from __future__ import annotations

import re
from typing import Optional

from runtime.phase_7_safety.answer import AnswerResult
from runtime.phase_8_threads.chat import PostMessageResult

FOOTER_PREFIX = "Last updated from sources:"
URL_PATTERN = re.compile(r"https?://[^\s)>\"]+")


def extract_footer(text: str) -> str:
    """
    Extract the footer line from an assistant answer when present.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(FOOTER_PREFIX.lower()):
            return stripped
    return ""


def extract_answer_body(text: str) -> str:
    """
    Return the user-visible answer body without standalone URL lines or footer.
    """
    body_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith(FOOTER_PREFIX.lower()):
            continue
        if URL_PATTERN.fullmatch(stripped):
            continue
        body_lines.append(stripped)
    return "\n".join(body_lines).strip()


def build_post_message_response(result: PostMessageResult) -> dict:
    """
    Build the POST /threads/{id}/messages response dictionary.
    """
    answer_result: AnswerResult = result.answer_result
    full_answer = answer_result.answer
    return {
        "answer": extract_answer_body(full_answer) or full_answer.strip(),
        "citation_url": answer_result.citation_url,
        "footer": extract_footer(full_answer),
        "thread_id": result.thread_id,
        "refused": answer_result.refused,
    }
