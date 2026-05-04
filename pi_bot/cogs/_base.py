"""Shared base class for all cogs."""
from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from ..bot import PiBot


class BaseCog(commands.Cog):
    """Holds a typed reference to the bot and exposes per-cog helpers."""

    def __init__(self, bot: "PiBot") -> None:
        self.bot = bot

    def _lang(self, ctx: commands.Context) -> str:
        return self.bot.state.get_server_language(
            ctx.guild.id if ctx.guild else None
        )

    def _prefix(self, ctx: commands.Context) -> str:
        return (ctx.clean_prefix or self.bot.config.default_prefix).strip()
