"""Convenience launcher: ``python main.py``.

Equivalent to ``python -m gunpla_fabrication_suite``; kept for users who run the
application directly from a source checkout without installing the package.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gunpla_fabrication_suite.application.bootstrap import run_application  # noqa: E402

if __name__ == "__main__":
    sys.exit(run_application())
