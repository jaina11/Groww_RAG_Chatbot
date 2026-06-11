"""CLI entry point: python -m ingest.phase_4_2_embed"""

import sys

from ingest.phase_4_2_embed.pipeline import run_embed


def main() -> int:
    """
    Run the Phase 4.2 embed pipeline and exit non-zero on failure.
    """
    results = run_embed()
    if not results:
        return 1
    if all(result.success for result in results):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
