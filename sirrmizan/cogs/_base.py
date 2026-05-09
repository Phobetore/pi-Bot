from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ..translations import t

if TYPE_CHECKING:
    from ..bot import SirrMizan


_slash_last_call: dict[tuple[int, str], float] = defaultdict(float)


class BaseCog(commands.Cog):
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
