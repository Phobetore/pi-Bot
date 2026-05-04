"""Shared pytest fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest

from pi_bot.state import State


@pytest.fixture
def state(tmp_path: Path) -> State:
    s = State(tmp_path)
    s.load()
    return s
