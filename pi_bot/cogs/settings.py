"""Server-side configuration commands (prefix, language, default roll)."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord.ext import commands

from ..dice_parser import DiceParseError, parse
from ..state import is_valid_prefix
from ..translations import SUPPORTED_LANGUAGES, t
from ._base import BaseCog

if TYPE_CHECKING:
    from ..bot import PiBot

logger = logging.getLogger(__name__)


class SettingsCog(BaseCog):
    @commands.command(name="setlang")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def set_language(self, ctx: commands.Context, lang: str) -> None:
        """Set the bot's language for this server. Available: en, fr, de, es."""
        current_lang = self._lang(ctx)
        normalized = lang.lower().strip()
        if normalized not in SUPPORTED_LANGUAGES:
            await ctx.send(t(current_lang, "lang_invalid"))
            return
        assert ctx.guild is not None  # @guild_only enforces this
        await self.bot.state.set_server_language(ctx.guild.id, normalized)
        await self.bot.state.save()
        await ctx.send(t(normalized, "lang_set", lang=normalized))

    @commands.command(name="setprefix")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def set_prefix(self, ctx: commands.Context, *, prefix: str) -> None:
        """Set a custom command prefix for this server."""
        lang = self._lang(ctx)
        normalized = prefix.strip()
        if not is_valid_prefix(normalized):
            await ctx.send(t(lang, "prefix_invalid"))
            return
        assert ctx.guild is not None
        await self.bot.state.set_server_prefix(ctx.guild.id, normalized)
        await self.bot.state.save()
        await ctx.send(t(lang, "prefix_set", prefix=normalized))

    @commands.command(name="defaultRoll", aliases=["defaultroll"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def set_default_roll(
        self, ctx: commands.Context, *, expression: str
    ) -> None:
        """Set the default dice expression used when ``!roll`` has no argument."""
        lang = self._lang(ctx)
        cleaned = expression.strip()
        try:
            parsed = parse(cleaned)
        except DiceParseError as exc:
            await ctx.send(t(lang, "defaultroll_invalid", error=str(exc)))
            return
        if not parsed.has_dice:
            await ctx.send(t(lang, "defaultroll_invalid", error="no dice in expression"))
            return
        assert ctx.guild is not None
        await self.bot.state.set_server_default_roll(ctx.guild.id, cleaned)
        await self.bot.state.save()
        await ctx.send(t(lang, "defaultroll_set", expression=cleaned))


def setup(bot: "PiBot") -> None:
    bot.add_cog(SettingsCog(bot))
