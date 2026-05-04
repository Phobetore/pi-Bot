"""Tests for the color registry."""
from __future__ import annotations

import pytest

from pi_bot.colors import CANONICAL_COLORS, DEFAULT_COLOR, hex_for, resolve


class TestResolve:
    def test_canonical_passes_through(self) -> None:
        for name in CANONICAL_COLORS:
            assert resolve(name) == name

    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("rouge", "red"),
            ("bleu", "blue"),
            ("vert", "green"),
            ("jaune", "yellow"),
            ("violet", "purple"),
            ("rot", "red"),
            ("blau", "blue"),
            ("grün", "green"),
            ("gruen", "green"),
            ("gelb", "yellow"),
            ("lila", "purple"),
            ("rojo", "red"),
            ("azul", "blue"),
            ("verde", "green"),
            ("amarillo", "yellow"),
            ("morado", "purple"),
            ("naranja", "orange"),
        ],
    )
    def test_localized_aliases(self, alias: str, expected: str) -> None:
        assert resolve(alias) == expected

    def test_case_insensitive(self) -> None:
        assert resolve("RED") == "red"
        assert resolve("Rouge") == "red"

    def test_whitespace_stripped(self) -> None:
        assert resolve("  red  ") == "red"
        assert resolve("\tred\n") == "red"

    def test_unknown_returns_none(self) -> None:
        assert resolve("magenta") is None
        assert resolve("") is None

    def test_non_string_returns_none(self) -> None:
        assert resolve(None) is None  # type: ignore[arg-type]
        assert resolve(42) is None  # type: ignore[arg-type]


class TestHexFor:
    def test_canonical_returns_int(self) -> None:
        for name in CANONICAL_COLORS:
            value = hex_for(name)
            assert isinstance(value, int)
            assert 0 <= value <= 0xFFFFFF

    def test_unknown_returns_default(self) -> None:
        assert hex_for("nonexistent") == CANONICAL_COLORS[DEFAULT_COLOR]

    def test_default_color_is_canonical(self) -> None:
        assert DEFAULT_COLOR in CANONICAL_COLORS
