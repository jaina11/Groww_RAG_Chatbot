"""CLI entry point: python -m ingest.phase_4_0_scraper"""

import sys

from ingest.phase_4_0_scraper.scraper import run_scraper


def main() -> int:
    """
    Run the Phase 4.0 scraper and exit non-zero if any URL fails.
    """
    results = run_scraper()
    if not results:
        return 1
    if all(result.success for result in results):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
