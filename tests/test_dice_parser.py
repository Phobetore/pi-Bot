"""Tests for the dice expression parser."""
from __future__ import annotations

import pytest

from pi_bot.dice_parser import (
    MAX_FACES,
    MAX_ROLLS_PER_TERM,
    DiceParseError,
    parse,
    parse_roll_input,
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


class TestParseRollInput:
    """Free-form input splitter used by the !roll command."""

    @staticmethod
    def _summary(raw: str) -> tuple[str, str | None]:
        expr, expr_str, target = parse_roll_input(raw)
        return expr_str, target

    # ── Without target ────────────────────────────────────────────────
    def test_single_dice(self) -> None:
        assert self._summary("1d20") == ("1d20", None)

    def test_single_modifier(self) -> None:
        assert self._summary("5") == ("5", None)

    def test_compound_no_spaces(self) -> None:
        assert self._summary("1d20+5") == ("1d20+5", None)

    def test_dice_with_separated_modifier(self) -> None:
        # The exact example from the bug report.
        assert self._summary("1d20 +20") == ("1d20+20", None)

    def test_dice_with_spaces_around_operator(self) -> None:
        assert self._summary("2d6 + 5") == ("2d6+5", None)

    def test_negative_with_spaces(self) -> None:
        assert self._summary("1d20 - 5") == ("1d20-5", None)

    def test_modifier_then_dice(self) -> None:
        # Sign injection must keep the boundary: "+5" + "1d20" → "+5+1d20",
        # NOT "+51d20" (which would be 51 rolls of d20).
        assert self._summary("+5 1d20") == ("+5+1d20", None)

    def test_two_dice_terms(self) -> None:
        assert self._summary("1d20 1d6") == ("1d20+1d6", None)

    def test_complex_chain(self) -> None:
        assert self._summary("1d20 +2d6 +4") == ("1d20+2d6+4", None)

    # ── With target ───────────────────────────────────────────────────
    def test_dice_with_target(self) -> None:
        assert self._summary("1d20 Goblin") == ("1d20", "Goblin")

    def test_compound_with_target(self) -> None:
        assert self._summary("1d20+5 Goblin") == ("1d20+5", "Goblin")

    def test_full_request_from_user(self) -> None:
        # The other exact example from the bug report.
        assert self._summary("1d20 +2d6 +4 Goblin") == ("1d20+2d6+4", "Goblin")

    def test_modifier_then_target(self) -> None:
        assert self._summary("+5 Goblin") == ("+5", "Goblin")

    def test_multi_word_target(self) -> None:
        assert self._summary("1d20 Big Boss") == ("1d20", "Big Boss")

    def test_target_with_number_in_name(self) -> None:
        # ``Boss5`` is a single token containing letters → target.
        assert self._summary("1d20 Boss5") == ("1d20", "Boss5")

    def test_spaces_around_op_with_target(self) -> None:
        assert self._summary("2d6 + 5 Goblin") == ("2d6+5", "Goblin")

    def test_negative_modifier_with_target(self) -> None:
        assert self._summary("1d20 - 5 Boss") == ("1d20-5", "Boss")

    def test_target_only_returns_no_expression(self) -> None:
        expr, expr_str, target = parse_roll_input("Goblin")
        assert expr is None
        assert expr_str == ""
        assert target == "Goblin"

    def test_empty_input(self) -> None:
        expr, expr_str, target = parse_roll_input("")
        assert expr is None
        assert expr_str == ""
        assert target is None

    def test_whitespace_only_input(self) -> None:
        assert parse_roll_input("   \t  ") == (None, "", None)

    # ── Edge cases that must not silently misparse ────────────────────
    def test_target_starting_with_digit_kept_as_target(self) -> None:
        # ``1d20`` is the expression; ``2nd Boss`` is the target name (the
        # first word is a number, but ``2nd`` isn't a valid token, so
        # everything from ``2nd`` onward goes to target).
        assert self._summary("1d20 2nd Boss") == ("1d20", "2nd Boss")

    def test_returns_parsed_object(self) -> None:
        expr, expr_str, target = parse_roll_input("1d6+3 Goblin")
        assert expr is not None
        assert expr.has_dice
        assert expr.modifier_total == 3
        assert expr_str == "1d6+3"
        assert target == "Goblin"
