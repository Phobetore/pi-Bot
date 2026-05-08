"""Tests for the dice expression parser."""
from __future__ import annotations

import pytest

from sirrmizan.dice_parser import (
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

    # ── Whitespace tolerance ──────────────────────────────────────────
    def test_tabs_treated_as_whitespace(self) -> None:
        assert self._summary("1d20\t+5") == ("1d20+5", None)

    def test_newlines_treated_as_whitespace(self) -> None:
        assert self._summary("1d20\n+5") == ("1d20+5", None)

    def test_multiple_spaces_collapsed(self) -> None:
        assert self._summary("1d20    +    5") == ("1d20+5", None)

    def test_leading_trailing_whitespace_stripped(self) -> None:
        assert self._summary("   1d20+5   ") == ("1d20+5", None)

    def test_target_with_extra_internal_spaces_normalized(self) -> None:
        # Extra spaces inside a multi-word target collapse to single spaces.
        assert self._summary("1d20 Big   Boss") == ("1d20", "Big Boss")

    # ── Stray operators handled gracefully ────────────────────────────
    def test_lone_operator_between_dice_and_target_is_dropped(self) -> None:
        # ``1d20 + Goblin`` — the stray ``+`` would otherwise stick to ``Goblin``.
        assert self._summary("1d20 + Goblin") == ("1d20", "Goblin")

    def test_lone_minus_between_dice_and_target_is_dropped(self) -> None:
        assert self._summary("1d20 - Goblin") == ("1d20", "Goblin")

    def test_lone_plus_before_target_is_dropped(self) -> None:
        # No expression at all, just ``+ Goblin``. Target should be "Goblin".
        assert self._summary("+ Goblin") == ("", "Goblin")

    def test_lone_plus_before_dice_merges(self) -> None:
        # ``+`` followed by digits IS merged.
        assert self._summary("+ 1d20") == ("+1d20", None)

    def test_lone_minus_before_dice_merges(self) -> None:
        assert self._summary("- 1d20") == ("-1d20", None)

    def test_trailing_plus_with_target_is_lenient(self) -> None:
        # ``1d20+`` has a stray trailing ``+`` that doesn't bind to anything.
        # We split it off and discard it, keeping the well-formed prefix.
        assert self._summary("1d20+ Goblin") == ("1d20", "Goblin")

    def test_trailing_minus_with_target_is_lenient(self) -> None:
        assert self._summary("1d20- Goblin") == ("1d20", "Goblin")

    def test_trailing_plus_then_number_keeps_operator(self) -> None:
        # When the trailing ``+`` is followed by a number after a space, the
        # split-off operator merges with the number to form a modifier.
        assert self._summary("1d20+ 5 Goblin") == ("1d20+5", "Goblin")

    def test_trailing_minus_then_number_keeps_operator(self) -> None:
        assert self._summary("1d20- 5 Goblin") == ("1d20-5", "Goblin")

    def test_trailing_op_alone_is_dropped(self) -> None:
        # ``1d20+`` with nothing after just rolls 1d20.
        assert self._summary("1d20+") == ("1d20", None)
        assert self._summary("1d20-") == ("1d20", None)

    def test_double_trailing_op_alone_is_dropped(self) -> None:
        # Both trailing operators are split off and dropped.
        assert self._summary("1d20++") == ("1d20", None)

    def test_redundant_operator_before_signed_number_is_dropped(self) -> None:
        # ``1d20+ +5`` — the standalone ``+`` is redundant because ``+5``
        # already carries its own sign.
        assert self._summary("1d20+ +5") == ("1d20+5", None)

    def test_redundant_operator_before_negative_number_is_dropped(self) -> None:
        assert self._summary("1d20+ -5") == ("1d20-5", None)

    def test_trailing_operator_in_target_is_dropped(self) -> None:
        # Stray trailing ``+`` after a target name should not appear in the
        # rendered target.
        assert self._summary("1d20 Goblin +") == ("1d20", "Goblin")

    # ── Negative chains ───────────────────────────────────────────────
    def test_chain_of_negative_modifiers(self) -> None:
        assert self._summary("1d20 -5 -3") == ("1d20-5-3", None)

    def test_subtract_dice_term_with_target(self) -> None:
        assert self._summary("1d20 -1d4 Boss") == ("1d20-1d4", "Boss")

    def test_negative_modifier_only_with_target(self) -> None:
        assert self._summary("-5 Boss") == ("-5", "Boss")

    # ── Greedy semantics ──────────────────────────────────────────────
    def test_greedy_picks_longest_valid_prefix(self) -> None:
        # ``5`` between dice and target is parsed as +5 modifier.
        assert self._summary("1d20 5 Boss") == ("1d20+5", "Boss")

    def test_three_dice_terms(self) -> None:
        assert self._summary("1d20 1d20 1d20") == ("1d20+1d20+1d20", None)

    def test_long_chain_with_target(self) -> None:
        result = self._summary("1d20 + 2d6 + 4 + 1d4 + 3 Goblin")
        assert result == ("1d20+2d6+4+1d4+3", "Goblin")

    # ── Limits & invalid inputs ───────────────────────────────────────
    def test_over_max_rolls_returns_no_expression(self) -> None:
        expr, expr_str, target = parse_roll_input("100d6")
        assert expr is None
        assert target == "100d6"

    def test_over_max_faces_returns_no_expression(self) -> None:
        expr, expr_str, target = parse_roll_input("1d100000")
        assert expr is None
        assert target == "1d100000"

    def test_zero_rolls_returns_no_expression(self) -> None:
        expr, _, target = parse_roll_input("0d6")
        assert expr is None
        assert target == "0d6"

    def test_invalid_second_term_keeps_only_valid_prefix(self) -> None:
        # ``1d20`` is valid; ``100d6`` exceeds max rolls. Greedy keeps just
        # the valid first term and pushes the over-limit term to target.
        assert self._summary("1d20 100d6") == ("1d20", "100d6")

    def test_invalid_dice_with_letter_suffix(self) -> None:
        # ``5x`` — digit then letter, not a token. Becomes target.
        assert self._summary("5x") == ("", "5x")

    def test_broken_dice_token(self) -> None:
        # ``1d`` missing faces. No expression match.
        assert self._summary("1d") == ("", "1d")

    def test_double_sign_token(self) -> None:
        expr, _, target = parse_roll_input("++5")
        assert expr is None
        assert target == "++5"

    # ── Cosmetic / target content ─────────────────────────────────────
    def test_unicode_target(self) -> None:
        assert self._summary("1d20 Café Naïve") == ("1d20", "Café Naïve")

    def test_target_with_mention_text(self) -> None:
        # Mentions in target name don't trigger pings (bot-wide
        # allowed_mentions=None) but they still survive in the target string.
        assert self._summary("1d20 @everyone") == ("1d20", "@everyone")

    def test_target_with_emoji(self) -> None:
        assert self._summary("1d20 🐉Boss") == ("1d20", "🐉Boss")

    def test_target_with_markdown(self) -> None:
        assert self._summary("1d20 **Boss**") == ("1d20", "**Boss**")

    # ── Case sensitivity ──────────────────────────────────────────────
    def test_uppercase_d(self) -> None:
        assert self._summary("1D20") == ("1D20", None)

    def test_mixed_case_d(self) -> None:
        # Greedy joins ``1D6`` after ``1d20`` with a synthetic ``+``.
        assert self._summary("1d20 1D6") == ("1d20+1D6", None)

    # ── Modifier-only edge cases ──────────────────────────────────────
    def test_zero_modifier_only(self) -> None:
        assert self._summary("0") == ("0", None)

    def test_zero_modifier_with_target(self) -> None:
        assert self._summary("+0 Boss") == ("+0", "Boss")
