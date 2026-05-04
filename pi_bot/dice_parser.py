"""Strict dice expression parser.

Grammar (informal):

    expression  := term (sign term)*
    term        := signed_dice | signed_int
    signed_dice := [+-]? UINT 'd' UINT
    signed_int  := [+-]? UINT

The parser consumes the whole input — any garbage character produces
``DiceParseError``. Numerical limits prevent abuse (``50`` rolls per term,
faces capped at ``99999``). The expression itself is capped at 100 characters.
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
        raise DiceParseError(
            f"expression too long (limit: {MAX_EXPRESSION_LENGTH} characters)"
        )

    dice: list[DicePart] = []
    modifiers: list[int] = []
    pos = 0
    first_token = True

    while pos < len(expression):
        match = _PIECE_RE.match(expression, pos)
        if match is None or match.start() != pos:
            raise DiceParseError(
                f"unexpected character {expression[pos]!r} at position {pos}"
            )

        # All non-leading tokens must start with an explicit sign — otherwise
        # ``2d63d6`` would parse as 2d6 then 3d6 silently.
        token_text = match.group(0)
        if not first_token and token_text[0] not in "+-":
            raise DiceParseError(
                f"missing sign before token {token_text!r} at position {pos}"
            )
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
                    f"invalid number of rolls in {dice_token!r} "
                    f"(must be 1-{MAX_ROLLS_PER_TERM})"
                )
            if not 1 <= faces <= MAX_FACES:
                raise DiceParseError(
                    f"invalid number of faces in {dice_token!r} "
                    f"(must be 1-{MAX_FACES})"
                )
            dice.append(DicePart(rolls=rolls, faces=faces, sign=sign))
        else:
            assert mod_token is not None
            modifiers.append(int(mod_token))

        pos = match.end()

    if pos != len(expression):
        raise DiceParseError(f"trailing characters: {expression[pos:]!r}")

    return ParsedExpression(dice=tuple(dice), modifiers=tuple(modifiers))
