"""Atomic JSON persistence helpers.

Writes go to a temporary file in the same directory as the target, then are
``os.replace``-d into place. ``os.replace`` is atomic on the same filesystem on
both POSIX and Windows, ensuring readers never observe a half-written file.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def read_json(path: Path, default: Any) -> Any:
    """Read a JSON file. Returns ``default`` if missing.

    If the file exists but is corrupted, it is moved aside as ``<path>.corrupted``
    and ``default`` is returned. The function never raises ``FileNotFoundError``
    nor ``JSONDecodeError`` — callers do not have to wrap it.
    """
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        backup = path.with_suffix(path.suffix + ".corrupted")
        try:
            os.replace(path, backup)
            logger.error("Corrupted JSON at %s — moved to %s", path, backup)
        except OSError:
            logger.exception("Failed to move corrupted JSON %s aside", path)
        return default


def write_json_atomic(path: Path, data: Any) -> None:
    """Write JSON atomically.

    Strategy:
    1. Write to a temp file in the same directory.
    2. ``fsync`` the temp file to flush kernel buffers.
    3. ``os.replace`` into place.

    On any error during writing, the temp file is removed. If a temp file
    already happens to exist for some reason, it is overwritten.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Failed to remove temp file %s", tmp_path)
        raise
