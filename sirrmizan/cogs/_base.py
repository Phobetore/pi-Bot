"""Shared base class for all cogs and slash-command helpers."""
from __future__ import annotations

import time
from collections import defaultdict
from functools import wraps
from typing import TYPE_CHECKING, Any, Awaitable, Callable

import discord
from discord.ext import commands

from ..translations import t

if TYPE_CHECKING:
    from ..bot import SirrMizan


class BaseCog(commands.Cog):
    """Holds a typed reference to the bot and exposes per-cog helpers."""

    def __init__(self, bot: "SirrMizan") -> None:
        self.bot = bot

    def _lang(self, ctx: commands.Context) -> str:
        return self.bot.state.get_server_language(
            ctx.guild.id if ctx.guild else None
        )

    def _prefix(self, ctx: commands.Context) -> str:
        return (ctx.clean_prefix or self.bot.config.default_prefix).strip()


# ---------------------------------------------------------------------------
# Cooldowns for slash commands
# ---------------------------------------------------------------------------
# ``commands.cooldown`` from discord.ext only applies to prefix commands.
# For slash commands we track a per-(user, command) timestamp ourselves and
# respond ephemerally with a localized message when the limit is hit.

_SlashHandler = Callable[..., Awaitable[Any]]
_last_call: dict[tuple[int, str], float] = defaultdict(float)


def slash_cooldown(seconds: float) -> Callable[[_SlashHandler], _SlashHandler]:
    """Decorator: enforce a per-user, per-command rate limit on a slash handler.

    Must be applied **after** ``@discord.slash_command(...)`` so it wraps the
    handler before py-cord registers it.
    """

    def decorator(func: _SlashHandler) -> _SlashHandler:
        @wraps(func)
        async def wrapper(
            self: BaseCog,
            ctx: discord.ApplicationContext,
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            key = (ctx.author.id, func.__name__)
            now = time.monotonic()
            elapsed = now - _last_call[key]
            if elapsed < seconds:
                lang = self.bot.state.get_server_language(
                    ctx.guild_id if ctx.guild_id else None
                )
                await ctx.respond(
                    t(lang, "command_cooldown", seconds=seconds - elapsed),
                    ephemeral=True,
                )
                return None
            _last_call[key] = now
            return await func(self, ctx, *args, **kwargs)

        return wrapper

    return decorator
