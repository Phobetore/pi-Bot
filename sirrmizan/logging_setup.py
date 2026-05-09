"""Logging setup.

``sirrmizan``       → app.log + stderr.
``sirrmizan.audit`` → audit.log only (propagate=False).

Also installs a guard on ``discord.gateway`` that exits the process when
py-cord reports the event loop blocked too long. systemd's
``Restart=on-failure`` brings the bot back. This avoids the failure mode
where the gateway is durably stuck but ``systemctl is-active`` still
reports healthy.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import re
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"

_GATEWAY_BLOCKED_THRESHOLD_SECONDS = 60
_GATEWAY_BLOCKED_RE = re.compile(r"heartbeat blocked for more than (\d+) seconds", re.IGNORECASE)


class _GatewayHealthcheck(logging.Handler):
    """Exit the process when py-cord reports the loop blocked too long."""

    def emit(self, record: logging.LogRecord) -> None:
        match = _GATEWAY_BLOCKED_RE.search(record.getMessage())
        if not match:
            return
        seconds = int(match.group(1))
        if seconds < _GATEWAY_BLOCKED_THRESHOLD_SECONDS:
            return
        logging.getLogger("sirrmizan").error(
            "discord.gateway heartbeat blocked %ss — exiting so systemd restarts us",
            seconds,
        )
        # Force-flush handlers so the diagnostic line lands in app.log.
        for handler in logging.getLogger("sirrmizan").handlers:
            try:
                handler.flush()
            except Exception:  # pragma: no cover
                pass
        os._exit(1)


def configure_logging(log_dir: Path, level: str = "INFO") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(log_dir, 0o700)
    except OSError:
        pass

    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(level)
    root.addHandler(stderr_handler)

    app_logger = logging.getLogger("sirrmizan")
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

    audit_logger = logging.getLogger("sirrmizan.audit")
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

    # Gateway health guard: install once, idempotent on reload.
    gateway_logger = logging.getLogger("discord.gateway")
    if not any(isinstance(h, _GatewayHealthcheck) for h in gateway_logger.handlers):
        gateway_logger.addHandler(_GatewayHealthcheck())
