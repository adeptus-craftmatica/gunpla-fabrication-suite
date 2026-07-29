"""Core application infrastructure.

This package provides generic services — plugin management, persistence,
events, logging, settings, and background jobs. It must never contain
Gunpla-domain business logic; that belongs in ``gunpla_fabrication_suite.plugins``.
"""

from __future__ import annotations
