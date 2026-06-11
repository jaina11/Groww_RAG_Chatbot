"""CLI entry point for Phase 8 multi-thread chat."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Any, Dict, List

from runtime.phase_8_threads.chat import (
    get_active_thread,
    post_user_message,
    set_active_thread,
)
from runtime.phase_8_threads.store import create_thread, get_history, list_threads


def _message_to_dict(message) -> Dict[str, Any]:
    """
    Convert a MessageRecord into a JSON-serializable dictionary.
    """
    return asdict(message)


def _cmd_new_thread() -> int:
    """
    Create a new thread and mark it as the active CLI thread.
    """
    thread = create_thread()
    set_active_thread(thread.id)
    print(json.dumps(asdict(thread), indent=2))
    return 0


def _cmd_say(query: str) -> int:
    """
    Post a user message to the active thread and print the assistant answer.
    """
    thread_id = get_active_thread()
    if not thread_id:
        print(
            "No active thread. Run: python -m runtime.phase_8_threads new-thread",
            file=sys.stderr,
        )
        return 1

    result = post_user_message(thread_id=thread_id, query=query)
    print(
        json.dumps(
            {
                "thread_id": result.thread_id,
                "user_message": _message_to_dict(result.user_message),
                "assistant_message": _message_to_dict(result.assistant_message),
                "answer_result": asdict(result.answer_result),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def _cmd_history() -> int:
    """
    Print recent message history for the active thread.
    """
    thread_id = get_active_thread()
    if not thread_id:
        print(
            "No active thread. Run: python -m runtime.phase_8_threads new-thread",
            file=sys.stderr,
        )
        return 1

    messages: List[Dict[str, Any]] = [
        _message_to_dict(message) for message in get_history(thread_id)
    ]
    print(
        json.dumps(
            {"thread_id": thread_id, "messages": messages},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def _cmd_list_threads() -> int:
    """
    Print all stored threads.
    """
    threads = [asdict(thread) for thread in list_threads()]
    print(json.dumps({"threads": threads}, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    """
    Dispatch Phase 8 thread CLI commands.
    """
    parser = argparse.ArgumentParser(description="Phase 8 multi-thread chat CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("new-thread", help="Create a new chat thread")
    say_parser = subparsers.add_parser("say", help="Send a message in the active thread")
    say_parser.add_argument("query", nargs="+", help="User query text")
    subparsers.add_parser("history", help="Show recent history for the active thread")
    subparsers.add_parser("list-threads", help="List all stored threads")

    args = parser.parse_args(argv)

    if args.command == "new-thread":
        return _cmd_new_thread()
    if args.command == "say":
        query = " ".join(args.query).strip()
        if not query:
            print("Query must not be empty.", file=sys.stderr)
            return 1
        return _cmd_say(query)
    if args.command == "history":
        return _cmd_history()
    if args.command == "list-threads":
        return _cmd_list_threads()

    print(f"Unknown command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
