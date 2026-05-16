"""Color registry for user message embeds.

Internal canonical names are English; aliases in the supported languages are
accepted as user input. Adding a new color requires updating this module only.
"""

from __future__ import annotations

from typing import Final

CANONICAL_COLORS: Final[dict[str, int]] = {
    "blue": 0x3498DB,
    "red": 0xE74C3C,
    "green": 0x2ECC71,
    "yellow": 0xF1C40F,
    "purple": 0x9B59B6,
    "orange": 0xE67E22,
    "turquoise": 0x1ABC9C,
}

DEFAULT_COLOR: Final[str] = "blue"

# Aliases mapping any accepted user input to the canonical English name.
_ALIASES: Final[dict[str, str]] = {
    # English
    "blue": "blue",
    "red": "red",
    "green": "green",
    "yellow": "yellow",
    "purple": "purple",
    "orange": "orange",
    "turquoise": "turquoise",
    # French (legacy support)
    "bleu": "blue",
    "rouge": "red",
    "vert": "green",
    "jaune": "yellow",
    "violet": "purple",
    # German
    "blau": "blue",
    "rot": "red",
    "grün": "green",
    "gruen": "green",
    "gelb": "yellow",
    "lila": "purple",
    "türkis": "turquoise",
    "tuerkis": "turquoise",
    # Spanish
    "azul": "blue",
    "rojo": "red",
    "verde": "green",
    "amarillo": "yellow",
    "morado": "purple",
    "naranja": "orange",
    "turquesa": "turquoise",
}


def resolve(name: str) -> str | None:
    """Resolve a localized color name to its canonical key. Returns None if unknown."""
    if not isinstance(name, str):
        return None
    return _ALIASES.get(name.strip().lower())


def hex_for(name: str) -> int:
    """Return the integer color value for a canonical name (or default)."""
    return CANONICAL_COLORS.get(name, CANONICAL_COLORS[DEFAULT_COLOR])
