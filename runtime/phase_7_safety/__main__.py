"""CLI entry point: python -m runtime.phase_7_safety \"your query\""""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Any, Dict

from runtime.phase_7_safety.answer import AnswerResult, answer
from runtime.phase_7_safety.router import route_query


def _serialize_result(result: AnswerResult) -> Dict[str, Any]:
    """
    Convert an AnswerResult into a JSON-serializable dictionary.
    """
    return asdict(result)


def main(argv: list[str] | None = None) -> int:
    """
    Run the Phase 7 safety pipeline for a CLI query and print JSON to stdout.
    """
    parser = argparse.ArgumentParser(description="Phase 7 safety + answer CLI")
    parser.add_argument("query", nargs="+", help="User query text")
    parser.add_argument(
        "--route-only",
        action="store_true",
        help="Only run the advisory router without retrieval or generation",
    )
    args = parser.parse_args(argv)

    query = " ".join(args.query).strip()
    if not query:
        print("Query must not be empty.", file=sys.stderr)
        return 1

    if args.route_only:
        decision = route_query(query)
        print(
            json.dumps(
                {
                    "query": decision.query,
                    "is_advisory": decision.is_advisory,
                    "matched_keyword": decision.matched_keyword,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    result = answer(query)
    print(json.dumps(_serialize_result(result), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
