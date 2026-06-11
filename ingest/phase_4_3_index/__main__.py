"""CLI entry point: python -m ingest.phase_4_3_index"""

import sys

from ingest.phase_4_3_index.pipeline import run_index


def main() -> int:
    """
    Run the Phase 4.3 Chroma index pipeline and exit non-zero on failure.
    """
    results = run_index()
    if not results:
        return 1
    if all(result.success for result in results):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
