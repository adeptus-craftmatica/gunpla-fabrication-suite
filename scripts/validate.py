"""validate.py — Run every quality gate in one pass.

Run from the project root:
    python scripts/validate.py

Runs, in order: ruff check, ruff format --check, mypy, pytest. Stops at the
first failing step and prints a clear summary; exits nonzero if anything
failed, so it can be used as a pre-push or CI gate.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

_STEPS: list[tuple[str, list[str]]] = [
    ("ruff check", ["ruff", "check", "."]),
    ("ruff format --check", ["ruff", "format", "--check", "."]),
    ("mypy", ["mypy", "src"]),
    ("pytest", ["pytest"]),
]


def main() -> int:
    results: list[tuple[str, bool]] = []

    for name, cmd in _STEPS:
        print()
        print(f"==> {name}")
        result = subprocess.run(cmd, cwd=ROOT)
        passed = result.returncode == 0
        results.append((name, passed))
        if not passed:
            print(f"\n[FAIL] {name} failed (exit code {result.returncode}).")
            break

    print()
    print("=" * 40)
    print("Validation summary")
    print("=" * 40)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    if not all(passed for _name, passed in results):
        print("\nValidation failed.")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
