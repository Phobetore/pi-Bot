"""Tests for the dice expression parser."""
from __future__ import annotations

import pytest

from pi_bot.dice_parser import (
    MAX_FACES,
    MAX_ROLLS_PER_TERM,
    DiceParseError,
    parse,
)


class TestSimpleExpressions:
    def test_single_die(self) -> None:
        result = parse("1d20")
        assert len(result.dice) == 1
        assert result.dice[0].rolls == 1
        assert result.dice[0].faces == 20
        assert result.dice[0].sign == 1
        assert result.modifiers == ()

    def test_multiple_dice_same_term(self) -> None:
        result = parse("3d6")
        assert result.dice[0].rolls == 3
        assert result.dice[0].faces == 6

    def test_modifier_only(self) -> None:
        result = parse("5")
        assert result.dice == ()
        assert result.modifiers == (5,)

    def test_negative_modifier_only(self) -> None:
        result = parse("-3")
        assert result.dice == ()
        assert result.modifiers == (-3,)

    def test_uppercase_d(self) -> None:
        result = parse("2D6")
        assert result.dice[0].rolls == 2
        assert result.dice[0].faces == 6


class TestCompoundExpressions:
    def test_dice_plus_modifier(self) -> None:
        result = parse("2d6+3")
        assert result.dice[0].rolls == 2
        assert result.dice[0].faces == 6
        assert result.modifiers == (3,)

    def test_dice_minus_modifier(self) -> None:
        result = parse("1d20-1")
        assert result.modifiers == (-1,)

    def test_two_dice_terms(self) -> None:
        result = parse("1d6+1d4")
        assert len(result.dice) == 2
        assert result.dice[0].sign == 1
        assert result.dice[1].sign == 1

    def test_subtracted_dice_term(self) -> None:
        result = parse("2d6-1d4")
        assert result.dice[0].sign == 1
        assert result.dice[1].sign == -1
        assert result.dice[1].rolls == 1
        assert result.dice[1].faces == 4

    def test_modifier_first_then_dice(self) -> None:
        result = parse("5+1d6")
        assert result.modifiers == (5,)
        assert result.dice[0].rolls == 1

    def test_explicit_positive_sign(self) -> None:
        result = parse("+2d6+3")
        assert result.dice[0].sign == 1

    def test_modifier_total(self) -> None:
        result = parse("1d6+3-1")
        assert result.modifier_total == 2


class TestRejectedInputs:
    def test_empty(self) -> None:
        with pytest.raises(DiceParseError):
            parse("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(DiceParseError):
            parse("   ")

    def test_none(self) -> None:
        with pytest.raises(DiceParseError):
            parse(None)  # type: ignore[arg-type]

    def test_missing_sign_between_terms(self) -> None:
        with pytest.raises(DiceParseError):
            parse("2d63d6")

    def test_internal_space(self) -> None:
        with pytest.raises(DiceParseError):
            parse("2d6 +3")

    def test_garbage_suffix(self) -> None:
        with pytest.raises(DiceParseError):
            parse("2d6abc")

    def test_zero_rolls(self) -> None:
        with pytest.raises(DiceParseError):
            parse("0d6")

    def test_zero_faces(self) -> None:
        with pytest.raises(DiceParseError):
            parse("1d0")

    def test_too_many_rolls(self) -> None:
        with pytest.raises(DiceParseError):
            parse(f"{MAX_ROLLS_PER_TERM + 1}d6")

    def test_too_many_faces(self) -> None:
        with pytest.raises(DiceParseError):
            parse(f"1d{MAX_FACES + 1}")

    def test_too_long(self) -> None:
        with pytest.raises(DiceParseError):
            parse("1" + "+1" * 60)

    def test_letters_only(self) -> None:
        with pytest.raises(DiceParseError):
            parse("foo")

    def test_only_d(self) -> None:
        with pytest.raises(DiceParseError):
            parse("d6")


class TestBoundaries:
    def test_max_rolls_accepted(self) -> None:
        result = parse(f"{MAX_ROLLS_PER_TERM}d6")
        assert result.dice[0].rolls == MAX_ROLLS_PER_TERM

    def test_max_faces_accepted(self) -> None:
        result = parse(f"1d{MAX_FACES}")
        assert result.dice[0].faces == MAX_FACES
