"""Tests for atomic JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path

from sirrmizan.persistence import read_json, write_json_atomic


def test_read_missing_returns_default(tmp_path: Path) -> None:
    assert read_json(tmp_path / "absent.json", default={"a": 1}) == {"a": 1}


def test_write_then_read(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    payload = {"hello": "world", "n": 42}
    write_json_atomic(target, payload)
    assert read_json(target, default={}) == payload


def test_write_overwrites_existing(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    write_json_atomic(target, {"v": 1})
    write_json_atomic(target, {"v": 2})
    assert read_json(target, default={}) == {"v": 2}


def test_write_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "file.json"
    write_json_atomic(target, {"ok": True})
    assert target.exists()
    assert read_json(target, default={}) == {"ok": True}


def test_corrupted_file_is_moved_aside(tmp_path: Path) -> None:
    target = tmp_path / "broken.json"
    target.write_text("{this is not json", encoding="utf-8")
    result = read_json(target, default={"fallback": True})
    assert result == {"fallback": True}
    backup = target.with_suffix(".json.corrupted")
    assert backup.exists()
    assert not target.exists()


def test_atomic_write_no_temp_file_left(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    write_json_atomic(target, {"x": 1})
    leftovers = [p for p in tmp_path.iterdir() if p.name != target.name]
    assert leftovers == []


def test_unicode_preserved(tmp_path: Path) -> None:
    target = tmp_path / "u.json"
    payload = {"text": "café — naïve", "emoji": "🎲"}
    write_json_atomic(target, payload)
    raw = target.read_text(encoding="utf-8")
    assert "café" in raw
    assert json.loads(raw) == payload
