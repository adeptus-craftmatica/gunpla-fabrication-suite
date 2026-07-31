"""Relaunch the application as a fresh process, for changes that need a clean start."""

from __future__ import annotations

import sys

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QWidget


def restart_application(window: QWidget) -> None:
    """Launch a fresh, detached copy of this process, then close ``window``.

    ``window`` is expected to be the app's main window — closing it runs
    the normal shutdown sequence (geometry save, plugin shutdown) and
    unwinds the event loop exactly like a manual quit, so nothing here
    duplicates that logic.

    ``sys.executable`` means something different frozen vs. not (same
    distinction ``resolve_migrations_root``/`_builtin_plugins_root`` make):
    in a frozen build it *is* the whole program, so ``sys.argv[0]``
    (that same path again) must be dropped from the arguments to avoid
    passing it twice; in a source checkout it's just the interpreter, so
    the full ``sys.argv`` (including the script path at index 0) is
    needed for Python to know what to run.
    """
    if getattr(sys, "frozen", False):
        QProcess.startDetached(sys.executable, sys.argv[1:])
    else:
        QProcess.startDetached(sys.executable, sys.argv)
    window.close()
