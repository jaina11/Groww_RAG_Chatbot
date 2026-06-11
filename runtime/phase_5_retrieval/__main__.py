"""CLI entry point: python -m runtime.phase_5_retrieval \"your query here\""""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from runtime.phase_5_retrieval.retriever import RetrievalResult, retrieve


def _serialize_result(result: RetrievalResult) -> Dict[str, Any]:
    """
    Convert a RetrievalResult into a JSON-serializable dictionary.
    """
    return {
        "query": result.query,
        "scheme_filter": result.scheme_filter,
        "citation_url": result.citation_url,
        "chunks": [
            {
                "text": chunk.text,
                "metadata": chunk.metadata,
                "score": chunk.score,
            }
            for chunk in result.chunks
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """
    Retrieve top chunks for a CLI query and print JSON to stdout.
    """
    parser = argparse.ArgumentParser(description="Phase 5 dense retrieval CLI")
    parser.add_argument("query", nargs="+", help="User query text")
    args = parser.parse_args(argv)

    query = " ".join(args.query).strip()
    if not query:
        print("Query must not be empty.", file=sys.stderr)
        return 1

    result = retrieve(query)
    print(json.dumps(_serialize_result(result), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
