"""Dice expression parser.

Grammar:

    expression  := term (sign term)*
    term        := signed_dice | signed_int
    signed_dice := [+-]? UINT 'd' UINT
    signed_int  := [+-]? UINT

``parse_roll_input`` is the higher-level wrapper for !roll — splits
free-form input into expression + optional target name and tolerates
spaces around operators.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_ROLLS_PER_TERM = 50
MAX_FACES = 99999
MAX_EXPRESSION_LENGTH = 100

# A token starting with `+`, `-`, or no sign at all (only allowed as the very
# first token). Either ``NdM`` (dice) or ``N`` (constant modifier).
_PIECE_RE = re.compile(r"(?P<dice>[+-]?\d+[dD]\d+)|(?P<mod>[+-]?\d+)")


class DiceParseError(ValueError):
    """Raised when an expression cannot be parsed."""


@dataclass(frozen=True, slots=True)
class DicePart:
    rolls: int
    faces: int
    sign: int  # +1 or -1


@dataclass(frozen=True, slots=True)
class ParsedExpression:
    dice: tuple[DicePart, ...]
    modifiers: tuple[int, ...]

    @property
    def has_dice(self) -> bool:
        return bool(self.dice)

    @property
    def is_empty(self) -> bool:
        return not self.dice and not self.modifiers

    @property
    def modifier_total(self) -> int:
        return sum(self.modifiers)


def parse(expression: str) -> ParsedExpression:
    """Parse ``expression`` into structured dice parts and modifiers.

    Whitespace is not allowed inside the expression (caller should strip and
    pass exactly one token).

    Raises:
        DiceParseError: For empty input, unrecognized syntax, or out-of-range
            values.
    """
    if expression is None:
        raise DiceParseError("expression is empty")
    if not isinstance(expression, str):
        raise DiceParseError("expression must be a string")

    expression = expression.strip()
    if not expression:
        raise DiceParseError("expression is empty")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise DiceParseError(f"expression too long (limit: {MAX_EXPRESSION_LENGTH} characters)")

    dice: list[DicePart] = []
    modifiers: list[int] = []
    pos = 0
    first_token = True

    while pos < len(expression):
        match = _PIECE_RE.match(expression, pos)
        if match is None or match.start() != pos:
            raise DiceParseError(f"unexpected character {expression[pos]!r} at position {pos}")

        # Non-leading tokens require an explicit sign; otherwise "2d63d6"
        # would split into 2d6 + 3d6.
        token_text = match.group(0)
        if not first_token and token_text[0] not in "+-":
            raise DiceParseError(f"missing sign before token {token_text!r} at position {pos}")
        first_token = False

        dice_token = match.group("dice")
        mod_token = match.group("mod")

        if dice_token is not None:
            sign = -1 if dice_token.startswith("-") else 1
            unsigned = dice_token.lstrip("+-").lower()
            rolls_str, faces_str = unsigned.split("d")
            rolls = int(rolls_str)
            faces = int(faces_str)
            if not 1 <= rolls <= MAX_ROLLS_PER_TERM:
                raise DiceParseError(
                    f"invalid number of rolls in {dice_token!r} (must be 1-{MAX_ROLLS_PER_TERM})"
                )
            if not 1 <= faces <= MAX_FACES:
                raise DiceParseError(
                    f"invalid number of faces in {dice_token!r} (must be 1-{MAX_FACES})"
                )
            dice.append(DicePart(rolls=rolls, faces=faces, sign=sign))
        else:
            assert mod_token is not None
            modifiers.append(int(mod_token))

        pos = match.end()

    if pos != len(expression):
        raise DiceParseError(f"trailing characters: {expression[pos:]!r}")

    return ParsedExpression(dice=tuple(dice), modifiers=tuple(modifiers))


def _split_trailing_ops(tokens: list[str]) -> list[str]:
    """Split trailing +/- off compound tokens: ['1d20+', 'x'] -> ['1d20', '+', 'x']."""
    out: list[str] = []
    for tok in tokens:
        trailing: list[str] = []
        while len(tok) > 1 and tok[-1] in "+-":
            trailing.append(tok[-1])
            tok = tok[:-1]
        out.append(tok)
        out.extend(reversed(trailing))
    return out


def _normalize_tokens(tokens: list[str]) -> list[str]:
    """Glue lone +/- onto the next numeric token, drop redundant sign pairs."""
    tokens = _split_trailing_ops(tokens)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        next_tok = tokens[i + 1] if i + 1 < len(tokens) else ""
        if tok in ("+", "-"):
            if next_tok and next_tok[0].isdigit():
                out.append(tok + next_tok)
                i += 2
                continue
            if next_tok and next_tok[0] in "+-":
                i += 1
                continue
        out.append(tok)
        i += 1
    return out


def _join_expression_tokens(tokens: list[str]) -> str:
    """Join with a synthetic '+' between unsigned non-leading tokens.

    Without this, "+5" followed by "1d20" would collapse into "+51d20".
    """
    if not tokens:
        return ""
    out = tokens[0]
    for tok in tokens[1:]:
        if tok and tok[0] not in "+-":
            out += "+"
        out += tok
    return out


def parse_roll_input(
    raw: str,
) -> tuple[ParsedExpression | None, str, str | None]:
    """Split free-form roll input into (expression, expression_str, target).

    Picks the longest leading run of tokens that parses as an expression;
    the rest is the target name.
    """
    raw = (raw or "").strip()
    if not raw:
        return None, "", None

    tokens = _normalize_tokens(raw.split())
    if not tokens:
        return None, "", None

    longest_k = 0
    longest_expr: ParsedExpression | None = None
    longest_str = ""

    for k in range(1, len(tokens) + 1):
        candidate = _join_expression_tokens(tokens[:k])
        try:
            parsed = parse(candidate)
        except DiceParseError:
            continue
        longest_k = k
        longest_expr = parsed
        longest_str = candidate

    target_words = list(tokens[longest_k:])
    while target_words and target_words[0] in ("+", "-"):
        target_words.pop(0)
    while target_words and target_words[-1] in ("+", "-"):
        target_words.pop()

    target = " ".join(target_words) if target_words else None
    return longest_expr, longest_str, target
