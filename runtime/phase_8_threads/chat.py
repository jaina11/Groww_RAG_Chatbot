"""Thread-scoped chat operations wired to the Phase 7 answer pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from runtime.phase_5_retrieval.logging_config import setup_runtime_logger
from runtime.phase_7_safety.answer import AnswerResult, answer
from runtime.phase_8_threads.store import MessageRecord, add_message, get_history

DEFAULT_ACTIVE_THREAD_FILE = "data/active_thread.txt"


@dataclass(frozen=True)
class PostMessageResult:
    """Outcome of posting a user message in one thread."""

    thread_id: str
    user_message: MessageRecord
    assistant_message: MessageRecord
    answer_result: AnswerResult


def _load_environment() -> None:
    """
    Load environment variables from a local .env file when present.
    """
    load_dotenv()


def _active_thread_file() -> Path:
    """
    Return the path used to persist the CLI's active thread id.
    """
    return Path(os.environ.get("ACTIVE_THREAD_FILE", DEFAULT_ACTIVE_THREAD_FILE))


def set_active_thread(thread_id: str) -> None:
    """
    Persist the active thread id for CLI commands that omit an explicit thread.
    """
    path = _active_thread_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(thread_id, encoding="utf-8")


def get_active_thread() -> Optional[str]:
    """
    Read the active thread id when one has been selected or created.
    """
    path = _active_thread_file()
    if not path.exists():
        return None
    thread_id = path.read_text(encoding="utf-8").strip()
    return thread_id or None


def post_user_message(
    thread_id: str,
    query: str,
) -> PostMessageResult:
    """
    Store the user message, run Phase 7 answer(), and store the assistant reply.

    Each thread keeps its own isolated history; no context is shared across threads.
    """
    _load_environment()
    logger = setup_runtime_logger("runtime.phase_8_threads")

    user_message = add_message(thread_id=thread_id, role="user", content=query)
    answer_result = answer(query)
    assistant_message = add_message(
        thread_id=thread_id,
        role="assistant",
        content=answer_result.answer,
    )

    logger.info(
        "posted message: thread_id=%s route=%s refused=%s history_count=%s",
        thread_id,
        answer_result.route,
        answer_result.refused,
        len(get_history(thread_id)),
    )
    return PostMessageResult(
        thread_id=thread_id,
        user_message=user_message,
        assistant_message=assistant_message,
        answer_result=answer_result,
    )
