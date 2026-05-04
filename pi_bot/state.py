"""In-memory state with persistent JSON storage.

All mutating operations acquire the same ``asyncio.Lock`` and set a dirty flag.
Persistence is performed by ``save()``, which writes each JSON file atomically
and clears the dirty flag. The bot's periodic save loop calls ``save()`` only
when ``is_dirty`` is true, avoiding spurious writes.

The state is intentionally narrow: three JSON files plus a few helpers. For
larger needs, migrate to SQLite (the API surface here is small enough to swap).
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from . import colors
from .persistence import read_json, write_json_atomic
from .translations import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("pi_bot.audit")

# Visible non-alphanumeric ASCII allowed in prefixes.
_PREFIX_PATTERN = re.compile(r"^[!?\.,;:/\\~#\$%&\*\+\-=<>\|\^@&]{1,5}$")


def is_valid_prefix(prefix: str) -> bool:
    return bool(_PREFIX_PATTERN.match(prefix))


class State:
    """Encapsulates loaded state and provides safe mutation methods."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._lock = asyncio.Lock()
        self._dirty = False

        self._users_path = data_dir / "user_preferences.json"
        self._stats_path = data_dir / "user_stats.json"
        self._servers_path = data_dir / "server_preferences.json"

        self._user_preferences: dict[str, Any] = {"users": {}}
        self._user_stats: dict[str, dict[str, int]] = {}
        self._server_prefs: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def load(self) -> None:
        """Synchronously load state from disk and migrate legacy formats."""
        users = read_json(self._users_path, {"users": {}})
        if not isinstance(users, dict):
            users = {"users": {}}
        users.setdefault("users", {})
        if not isinstance(users["users"], dict):
            users["users"] = {}
        self._user_preferences = users

        stats = read_json(self._stats_path, {})
        self._user_stats = stats if isinstance(stats, dict) else {}

        servers = read_json(self._servers_path, {})
        self._server_prefs = servers if isinstance(servers, dict) else {}

        self._migrate()

    def _migrate(self) -> None:
        """Forward-only data migrations. Marks dirty if anything changes."""
        users = self._user_preferences.get("users", {})
        for prefs in users.values():
            if not isinstance(prefs, dict):
                continue
            color = prefs.get("color")
            if isinstance(color, str):
                resolved = colors.resolve(color)
                if resolved is not None and resolved != color:
                    prefs["color"] = resolved
                    self._dirty = True
                elif resolved is None:
                    prefs["color"] = colors.DEFAULT_COLOR
                    self._dirty = True

        # Drop legacy `colors` mapping that used to be inside the file.
        if "colors" in self._user_preferences:
            self._user_preferences.pop("colors", None)
            self._dirty = True

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    async def save(self) -> None:
        async with self._lock:
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        write_json_atomic(self._users_path, self._user_preferences)
        write_json_atomic(self._stats_path, self._user_stats)
        write_json_atomic(self._servers_path, self._server_prefs)
        self._dirty = False

    # ------------------------------------------------------------------
    # User preferences
    # ------------------------------------------------------------------
    def get_user_color_name(self, user_id: int) -> str:
        users = self._user_preferences.get("users", {})
        prefs = users.get(str(user_id), {})
        name = prefs.get("color") if isinstance(prefs, dict) else None
        if isinstance(name, str) and name in colors.CANONICAL_COLORS:
            return name
        return colors.DEFAULT_COLOR

    def get_user_color_hex(self, user_id: int) -> int:
        return colors.hex_for(self.get_user_color_name(user_id))

    async def set_user_color(self, user_id: int, color_input: str) -> str:
        """Set a user's color. Returns the canonical name. Raises ValueError if unknown."""
        canonical = colors.resolve(color_input)
        if canonical is None:
            raise ValueError(f"unknown color: {color_input!r}")
        async with self._lock:
            users = self._user_preferences.setdefault("users", {})
            users.setdefault(str(user_id), {})["color"] = canonical
            self._dirty = True
        return canonical

    # ------------------------------------------------------------------
    # User stats
    # ------------------------------------------------------------------
    def get_user_dice_count(self, user_id: int) -> int:
        entry = self._user_stats.get(str(user_id), {})
        if not isinstance(entry, dict):
            return 0
        value = entry.get("dice_rolls_count", 0)
        return int(value) if isinstance(value, int) else 0

    async def increment_dice_rolls(self, user_id: int) -> None:
        async with self._lock:
            entry = self._user_stats.setdefault(str(user_id), {})
            entry["dice_rolls_count"] = entry.get("dice_rolls_count", 0) + 1
            self._dirty = True

    # ------------------------------------------------------------------
    # Server preferences
    # ------------------------------------------------------------------
    def get_server_prefix(self, guild_id: int, default: str) -> str:
        entry = self._server_prefs.get(str(guild_id), {})
        if isinstance(entry, dict):
            value = entry.get("prefix")
            if isinstance(value, str) and is_valid_prefix(value):
                return value
        return default

    async def set_server_prefix(self, guild_id: int, prefix: str) -> None:
        if not is_valid_prefix(prefix):
            raise ValueError(f"invalid prefix: {prefix!r}")
        async with self._lock:
            self._server_prefs.setdefault(str(guild_id), {})["prefix"] = prefix
            self._dirty = True
        audit_logger.info("prefix_changed guild=%s prefix=%r", guild_id, prefix)

    def get_server_language(self, guild_id: int | None) -> str:
        if guild_id is None:
            return "en"
        entry = self._server_prefs.get(str(guild_id), {})
        if isinstance(entry, dict):
            value = entry.get("language")
            if isinstance(value, str) and value in SUPPORTED_LANGUAGES:
                return value
        return "en"

    async def set_server_language(self, guild_id: int, lang: str) -> None:
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unsupported language: {lang!r}")
        async with self._lock:
            self._server_prefs.setdefault(str(guild_id), {})["language"] = lang
            self._dirty = True
        audit_logger.info("language_changed guild=%s lang=%s", guild_id, lang)

    def get_server_default_roll(self, guild_id: int | None) -> str | None:
        if guild_id is None:
            return None
        entry = self._server_prefs.get(str(guild_id), {})
        if isinstance(entry, dict):
            value = entry.get("default_roll")
            if isinstance(value, str):
                return value
        return None

    async def set_server_default_roll(self, guild_id: int, expression: str) -> None:
        async with self._lock:
            self._server_prefs.setdefault(str(guild_id), {})["default_roll"] = expression
            self._dirty = True
        audit_logger.info(
            "default_roll_changed guild=%s expression=%r", guild_id, expression
        )
