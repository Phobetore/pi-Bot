"""Structured logging setup.

Two named loggers exist:

* ``pi_bot`` — application logs, written to ``app.log`` and stderr.
* ``pi_bot.audit`` — security-relevant events, written to ``audit.log`` only
  (``propagate=False`` so audit entries do not leak into the general log).
"""
from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(log_dir: Path, level: str = "INFO") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    # Defensive: tighten directory permissions on POSIX (no-op on Windows).
    try:
        os.chmod(log_dir, 0o700)
    except OSError:
        pass

    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    # Root: only third-party noise. We send our own logs at the configured
    # level via a stderr handler attached here, and they reach it through
    # propagation from the ``pi_bot`` logger.
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(level)
    root.addHandler(stderr_handler)

    # ``pi_bot`` logger: own rotating file + propagation to root for stderr.
    app_logger = logging.getLogger("pi_bot")
    app_logger.setLevel(level)
    for handler in list(app_logger.handlers):
        app_logger.removeHandler(handler)
    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    app_logger.addHandler(app_handler)
    app_logger.propagate = True

    # ``pi_bot.audit``: dedicated file, no propagation.
    audit_logger = logging.getLogger("pi_bot.audit")
    audit_logger.setLevel(logging.INFO)
    for handler in list(audit_logger.handlers):
        audit_logger.removeHandler(handler)
    audit_handler = logging.handlers.RotatingFileHandler(
        log_dir / "audit.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    audit_handler.setFormatter(formatter)
    audit_logger.addHandler(audit_handler)
    audit_logger.propagate = False
