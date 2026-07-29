"""Structured logging configuration.

Log records are written both to the console and to a rotating file inside the
application's managed logs directory. Categories such as ``plugins``,
``database``, or ``migrations`` are conventionally expressed as the logger
name (``get_logger("plugins")``), not as extra formatting.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import cast

import structlog

_CONFIGURED = False


def configure_logging(logs_dir: Path, *, level: int = logging.INFO) -> None:
    """Configure structlog and stdlib logging to write to ``logs_dir``.

    Safe to call more than once; only the first call has an effect.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "gunpla_fabrication_suite.log"

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


def get_logger(category: str) -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound to a diagnostic category.

    Args:
        category: A short category name, e.g. ``"plugins"``, ``"database"``,
            ``"migrations"``, or ``"ui"``.
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(category))
