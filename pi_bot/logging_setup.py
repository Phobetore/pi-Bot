"""Structured logging setup.

Two named loggers exist:

* ``pi_bot`` — application logs, written to ``app.log`` and stderr.
* ``pi_bot.audit`` — security-relevant events, written to ``audit.log`` only.

The audit logger is isolated (``propagate=False``) so audit entries do not leak
into the general application log.
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(log_dir: Path, level: str = "INFO") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    root = logging.getLogger()
    root.setLevel(logging.WARNING)  # Reduce noise from third-party libs.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(level)
    root.addHandler(stderr_handler)

    app_logger = logging.getLogger("pi_bot")
    app_logger.setLevel(level)
    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    app_logger.addHandler(app_handler)
    # The app logger should NOT propagate to root, otherwise messages appear twice
    # on stderr (once from app handler propagating, once from the stderr handler).
    # We keep propagation enabled so stderr gets app logs too, but remove the
    # root's stream handler from receiving duplicates by attaching it only at
    # root level. Net effect: stderr handler is already on root; pi_bot logs
    # propagate up and reach it once. File handler is unique to pi_bot.
    app_logger.propagate = True

    audit_logger = logging.getLogger("pi_bot.audit")
    audit_logger.setLevel(logging.INFO)
    audit_handler = logging.handlers.RotatingFileHandler(
        log_dir / "audit.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    audit_handler.setFormatter(formatter)
    # Replace any pre-existing handlers to avoid duplication on reload.
    for handler in list(audit_logger.handlers):
        audit_logger.removeHandler(handler)
    audit_logger.addHandler(audit_handler)
    audit_logger.propagate = False
