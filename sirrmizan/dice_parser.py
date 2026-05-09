"""Strict dice expression parser.

Grammar (informal):

    expression  := term (sign term)*
    term        := signed_dice | signed_int
    signed_dice := [+-]? UINT 'd' UINT
    signed_int  := [+-]? UINT

The parser consumes the whole input — any garbage character produces
``DiceParseError``. Numerical limits prevent abuse (``50`` rolls per term,
faces capped at ``99999``). The expression itself is capped at 100 characters.

This module also exposes :func:`parse_roll_input`, a higher-level helper that
splits free-form ``!roll`` arguments into an expression and an optional target
name, tolerating arbitrary whitespace inside and around operators.
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

        # All non-leading tokens must start with an explicit sign — otherwise
        # ``2d63d6`` would parse as 2d6 then 3d6 silently.
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


# ---------------------------------------------------------------------------
# Free-form input splitter
# ---------------------------------------------------------------------------


def _split_trailing_ops(tokens: list[str]) -> list[str]:
    """Split off trailing ``+``/``-`` characters from compound tokens.

    ``['1d20+', 'Goblin']`` → ``['1d20', '+', 'Goblin']``.
    ``['1d20++']``          → ``['1d20', '+', '+']``.

    Tokens that ARE just an operator (``+``, ``-``) are left alone.
    """
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
    """Pre-process a token list to make space-tolerant joining unambiguous.

    Two passes:

    1. Trailing-operator split — ``1d20+`` becomes ``1d20`` then ``+``.
    2. Lone-operator handling:
       - Followed by a numeric token: glue them (``+``, ``5`` → ``+5``).
       - Followed by another sign token: drop the lone operator as redundant
         (``+ +5`` → ``+5``).
       - Otherwise: leave the lone operator in place; later steps will strip
         it from the target name if it ends up there.
    """
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
                # The next token already carries its own sign; this lone
                # operator is redundant garbage.
                i += 1
                continue
        out.append(tok)
        i += 1
    return out


def _join_expression_tokens(tokens: list[str]) -> str:
    """Concatenate tokens, prefixing unsigned non-leading tokens with ``+``.

    Without this, ``+5`` followed by ``1d20`` would be glued as ``+51d20``
    (51 rolls of d20) instead of ``+5+1d20``.
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

    Walks tokens left-to-right, picking the longest prefix whose joined form
    parses as a valid expression. The remaining tokens are joined with a
    single space to form the target name. Whitespace around operators is
    tolerated (``2d6 + 5 Goblin`` works the same as ``2d6+5 Goblin``).

    Returns:
        ``(parsed, joined_str, target)``. ``parsed`` is ``None`` if no leading
        tokens form a valid expression — in that case, ``joined_str`` is empty
        and the entire (normalized) input is the target.
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

    # Greedy: try every prefix length and remember the longest one that parses.
    for k in range(1, len(tokens) + 1):
        candidate = _join_expression_tokens(tokens[:k])
        try:
            parsed = parse(candidate)
        except DiceParseError:
            continue
        longest_k = k
        longest_expr = parsed
        longest_str = candidate

    # Discard any leading or trailing lone +/- tokens from the target — they
    # are leftover operators that didn't bind to a numeric token (e.g. user
    # typed ``1d20 + Goblin`` or ``1d20 Goblin +``).
    target_words = list(tokens[longest_k:])
    while target_words and target_words[0] in ("+", "-"):
        target_words.pop(0)
    while target_words and target_words[-1] in ("+", "-"):
        target_words.pop()

    target = " ".join(target_words) if target_words else None
    return longest_expr, longest_str, target
