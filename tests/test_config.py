"""Tests for configuration loading."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pi_bot.config import ConfigError, load_config


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Strip pi-Bot env vars and chdir to a fresh tmp directory.

    This prevents test order from leaking values between cases and prevents
    a real ``config.json`` in the project root from being picked up.
    """
    for key in (
        "PI_BOT_TOKEN",
        "PI_BOT_DEFAULT_PREFIX",
        "PI_BOT_DATA_DIR",
        "PI_BOT_LOG_DIR",
        "PI_BOT_SAVE_INTERVAL",
        "PI_BOT_LOG_LEVEL",
        "PI_BOT_CONFIG",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


def test_missing_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConfigError):
        load_config()


def test_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PI_BOT_TOKEN", "abc")
    cfg = load_config()
    assert cfg.token == "abc"
    assert cfg.default_prefix == "!"


def test_token_from_legacy_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"token": "from_legacy", "prefix": "?"}), encoding="utf-8")
    monkeypatch.setenv("PI_BOT_CONFIG", str(legacy))
    cfg = load_config()
    assert cfg.token == "from_legacy"
    assert cfg.default_prefix == "?"


def test_env_overrides_legacy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"token": "legacy", "prefix": "?"}), encoding="utf-8")
    monkeypatch.setenv("PI_BOT_CONFIG", str(legacy))
    monkeypatch.setenv("PI_BOT_TOKEN", "env_token")
    cfg = load_config()
    assert cfg.token == "env_token"
    # Prefix not set in env → falls back to legacy.
    assert cfg.default_prefix == "?"


def test_invalid_prefix_length(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PI_BOT_TOKEN", "abc")
    monkeypatch.setenv("PI_BOT_DEFAULT_PREFIX", "toolong")
    with pytest.raises(ConfigError):
        load_config()


def test_invalid_save_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PI_BOT_TOKEN", "abc")
    monkeypatch.setenv("PI_BOT_SAVE_INTERVAL", "0")
    with pytest.raises(ConfigError):
        load_config()


def test_invalid_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PI_BOT_TOKEN", "abc")
    monkeypatch.setenv("PI_BOT_LOG_LEVEL", "VERBOSE")
    with pytest.raises(ConfigError):
        load_config()


def test_creates_data_and_log_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PI_BOT_TOKEN", "abc")
    monkeypatch.setenv("PI_BOT_DATA_DIR", str(tmp_path / "d"))
    monkeypatch.setenv("PI_BOT_LOG_DIR", str(tmp_path / "l"))
    cfg = load_config()
    assert cfg.data_dir.exists()
    assert cfg.log_dir.exists()
