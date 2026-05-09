"""Application configuration loaded from environment variables.

Configuration is sourced from environment variables (optionally provided through a
``.env`` file). For backward compatibility with the legacy layout, missing values
fall back to a ``config.json`` file when present.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when the runtime configuration is invalid or incomplete."""


@dataclass(frozen=True, slots=True)
class Config:
    token: str
    default_prefix: str
    data_dir: Path
    log_dir: Path
    save_interval: float
    log_level: str


def _read_legacy_config(path: Path) -> dict[str, object]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Failed to read legacy config {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Legacy config {path} must contain a JSON object")
    return data


def load_config(env_file: Path | None = None) -> Config:
    """Load configuration from environment, ``.env``, and a legacy ``config.json``.

    Precedence (highest first): real environment variables, ``.env`` file,
    legacy ``config.json``, defaults.
    """
    if env_file is not None:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    token = os.environ.get("SIRRMIZAN_TOKEN", "").strip() or None
    default_prefix = os.environ.get("SIRRMIZAN_DEFAULT_PREFIX", "").strip() or None

    legacy_path = Path(os.environ.get("SIRRMIZAN_CONFIG", "config.json"))
    if (token is None or default_prefix is None) and legacy_path.exists():
        legacy = _read_legacy_config(legacy_path)
        if token is None:
            legacy_token = legacy.get("token")
            if isinstance(legacy_token, str) and legacy_token.strip():
                token = legacy_token.strip()
        if default_prefix is None:
            legacy_prefix = legacy.get("prefix")
            if isinstance(legacy_prefix, str) and legacy_prefix.strip():
                default_prefix = legacy_prefix.strip()

    if not token:
        raise ConfigError(
            "SIRRMIZAN_TOKEN is required. Set it in your environment or .env file. "
            "See .env.example."
        )

    default_prefix = default_prefix or "!"
    if not 1 <= len(default_prefix) <= 5:
        raise ConfigError("SIRRMIZAN_DEFAULT_PREFIX must be 1-5 characters")

    data_dir = Path(os.environ.get("SIRRMIZAN_DATA_DIR", "data")).resolve()
    log_dir = Path(os.environ.get("SIRRMIZAN_LOG_DIR", "logs")).resolve()

    raw_save_interval = os.environ.get("SIRRMIZAN_SAVE_INTERVAL", "60")
    try:
        save_interval = float(raw_save_interval)
    except ValueError as exc:
        raise ConfigError(
            f"SIRRMIZAN_SAVE_INTERVAL must be a number, got {raw_save_interval!r}"
        ) from exc
    if save_interval <= 0:
        raise ConfigError("SIRRMIZAN_SAVE_INTERVAL must be strictly positive")

    log_level = os.environ.get("SIRRMIZAN_LOG_LEVEL", "INFO").upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigError(f"Invalid SIRRMIZAN_LOG_LEVEL: {log_level!r}")

    data_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    # Tighten permissions on POSIX (no-op on Windows). Stats and prefs are
    # stored here; nobody else needs to read them.
    for directory in (data_dir, log_dir):
        try:
            os.chmod(directory, 0o700)
        except OSError:
            pass

    return Config(
        token=token,
        default_prefix=default_prefix,
        data_dir=data_dir,
        log_dir=log_dir,
        save_interval=save_interval,
        log_level=log_level,
    )
