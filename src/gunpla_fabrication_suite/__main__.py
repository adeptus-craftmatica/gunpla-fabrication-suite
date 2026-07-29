"""Entry point for ``python -m gunpla_fabrication_suite``."""

from __future__ import annotations

import sys

from gunpla_fabrication_suite.application.bootstrap import run_application


def main() -> int:
    """Launch the application and return its process exit code."""
    return run_application()


if __name__ == "__main__":
    sys.exit(main())
