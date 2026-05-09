"""In-memory state, persisted as three JSON files."""

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
audit_logger = logging.getLogger("sirrmizan.audit")

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

    def load(self) -> None:
        """Synchronously load state from disk, sanitize, and migrate."""
        users = read_json(self._users_path, {"users": {}})
        self._user_preferences = users if isinstance(users, dict) else {"users": {}}

        stats = read_json(self._stats_path, {})
        self._user_stats = stats if isinstance(stats, dict) else {}

        servers = read_json(self._servers_path, {})
        self._server_prefs = servers if isinstance(servers, dict) else {}

        self._sanitize()
        self._migrate()

    def _sanitize(self) -> None:
        """Drop on-disk values that don't match the expected schema."""
        raw_users = self._user_preferences.get("users")
        if not isinstance(raw_users, dict):
            self._user_preferences = {"users": {}}
            self._dirty = True
        else:
            cleaned_users: dict[str, dict[str, Any]] = {}
            for uid, prefs in raw_users.items():
                if not (isinstance(uid, str) and isinstance(prefs, dict)):
                    self._dirty = True
                    continue
                clean: dict[str, Any] = {}
                color = prefs.get("color")
                if isinstance(color, str):
                    clean["color"] = color
                compact = prefs.get("compact")
                if isinstance(compact, bool):
                    clean["compact"] = compact
                elif "compact" in prefs:
                    self._dirty = True
                cleaned_users[uid] = clean
            if cleaned_users != raw_users:
                self._dirty = True
            self._user_preferences["users"] = cleaned_users

        cleaned_stats: dict[str, dict[str, int]] = {}
        for uid, entry in self._user_stats.items():
            if not (isinstance(uid, str) and isinstance(entry, dict)):
                self._dirty = True
                continue
            count = entry.get("dice_rolls_count", 0)
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                count = 0
                self._dirty = True
            cleaned_stats[uid] = {"dice_rolls_count": count}
        if cleaned_stats != self._user_stats:
            self._dirty = True
        self._user_stats = cleaned_stats

        cleaned_servers: dict[str, dict[str, Any]] = {}
        for gid, entry in self._server_prefs.items():
            if not (isinstance(gid, str) and isinstance(entry, dict)):
                self._dirty = True
                continue
            clean_server: dict[str, Any] = {}
            for key in ("prefix", "language", "default_roll"):
                value = entry.get(key)
                if isinstance(value, str):
                    clean_server[key] = value
                elif key in entry:
                    self._dirty = True
            cleaned_servers[gid] = clean_server
        if cleaned_servers != self._server_prefs:
            self._dirty = True
        self._server_prefs = cleaned_servers

    def _migrate(self) -> None:
        users = self._user_preferences.get("users", {})
        for prefs in users.values():
            color = prefs.get("color")
            if isinstance(color, str):
                resolved = colors.resolve(color)
                if resolved is not None and resolved != color:
                    prefs["color"] = resolved
                    self._dirty = True
                elif resolved is None:
                    prefs["color"] = colors.DEFAULT_COLOR
                    self._dirty = True

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
        # Run the synchronous fsync-heavy work in a worker thread so a slow
        # disk does not block the event loop and starve the Discord gateway
        # heartbeat task.
        async with self._lock:
            await asyncio.get_running_loop().run_in_executor(None, self._save_unlocked)

    def _save_unlocked(self) -> None:
        write_json_atomic(self._users_path, self._user_preferences)
        write_json_atomic(self._stats_path, self._user_stats)
        write_json_atomic(self._servers_path, self._server_prefs)
        self._dirty = False

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

    def get_user_compact(self, user_id: int) -> bool:
        """Whether this user prefers compact roll output. Defaults to False."""
        users = self._user_preferences.get("users", {})
        prefs = users.get(str(user_id), {})
        if isinstance(prefs, dict):
            value = prefs.get("compact")
            if isinstance(value, bool):
                return value
        return False

    async def set_user_compact(self, user_id: int, compact: bool) -> None:
        async with self._lock:
            users = self._user_preferences.setdefault("users", {})
            users.setdefault(str(user_id), {})["compact"] = bool(compact)
            self._dirty = True

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
        audit_logger.info("default_roll_changed guild=%s expression=%r", guild_id, expression)
