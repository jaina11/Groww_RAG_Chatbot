"""CLI entry point: python -m runtime.phase_6_generation \"your query\""""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Any, Dict

from runtime.phase_6_generation.generator import GenerationResult, generate_answer


def _serialize_result(result: GenerationResult) -> Dict[str, Any]:
    """
    Convert a GenerationResult into a JSON-serializable dictionary.
    """
    return asdict(result)


def main(argv: list[str] | None = None) -> int:
    """
    Generate an answer for a CLI query and print JSON to stdout.
    """
    parser = argparse.ArgumentParser(description="Phase 6 Groq generation CLI")
    parser.add_argument("query", nargs="+", help="User query text")
    args = parser.parse_args(argv)

    query = " ".join(args.query).strip()
    if not query:
        print("Query must not be empty.", file=sys.stderr)
        return 1

    result = generate_answer(query)
    print(json.dumps(_serialize_result(result), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
