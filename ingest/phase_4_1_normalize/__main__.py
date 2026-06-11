"""CLI entry point: python -m ingest.phase_4_1_normalize"""

import sys

from ingest.phase_4_1_normalize.pipeline import run_normalize


def main() -> int:
    """
    Run the Phase 4.1 normalize + chunk pipeline and exit non-zero on failure.
    """
    results = run_normalize()
    if not results:
        return 1
    if all(result.success for result in results):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
