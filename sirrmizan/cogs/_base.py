"""Shared base class for all cogs and slash-command helpers."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ..translations import t

if TYPE_CHECKING:
    from ..bot import SirrMizan


# Per-(user, command) timestamps for slash-command cooldowns.
# Module-level state is acceptable: cooldowns reset on bot restart, which is
# the expected lifecycle for an in-memory rate limit.
_slash_last_call: dict[tuple[int, str], float] = defaultdict(float)


class BaseCog(commands.Cog):
    """Holds a typed reference to the bot and exposes per-cog helpers."""

    def __init__(self, bot: SirrMizan) -> None:
        self.bot = bot

    def _lang(self, ctx: commands.Context) -> str:
        return self.bot.state.get_server_language(ctx.guild.id if ctx.guild else None)

    def _prefix(self, ctx: commands.Context) -> str:
        return (ctx.clean_prefix or self.bot.config.default_prefix).strip()

    async def _slash_cooldown(
        self,
        ctx: discord.ApplicationContext,
        key: str,
        seconds: float = 3.0,
    ) -> bool:
        """Per-user, per-key rate limit for a slash command.

        Returns ``True`` if the call may proceed (and updates the last-call
        timestamp), ``False`` after responding ephemerally with a localized
        cooldown message.

        Implemented inline rather than as a decorator because ``functools.wraps``
        does not copy ``__defaults__``, which py-cord relies on to discover
        ``discord.Option(...)`` annotations. A wrapping decorator silently
        breaks option parsing on slash commands that have parameters.
        """
        bucket_key = (ctx.author.id, key)
        now = time.monotonic()
        elapsed = now - _slash_last_call[bucket_key]
        if elapsed < seconds:
            lang = self.bot.state.get_server_language(ctx.guild_id if ctx.guild_id else None)
            await ctx.respond(
                t(lang, "command_cooldown", seconds=seconds - elapsed),
                ephemeral=True,
            )
            return False
        _slash_last_call[bucket_key] = now
        return True
