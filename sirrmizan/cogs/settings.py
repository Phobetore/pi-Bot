"""Server-side configuration commands (prefix, language, default roll)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ..dice_parser import DiceParseError, parse, parse_roll_input
from ..state import is_valid_prefix
from ..translations import SUPPORTED_LANGUAGES, t
from ._base import BaseCog

if TYPE_CHECKING:
    from ..bot import SirrMizan

logger = logging.getLogger(__name__)


class SettingsCog(BaseCog):
    async def _do_set_language(self, guild_id: int, lang_input: str) -> tuple[str, bool]:
        normalized = lang_input.lower().strip()
        if normalized not in SUPPORTED_LANGUAGES:
            return normalized, False
        await self.bot.state.set_server_language(guild_id, normalized)
        await self.bot.state.save()
        return normalized, True

    async def _do_set_prefix(self, guild_id: int, prefix_input: str) -> tuple[str, bool]:
        normalized = prefix_input.strip()
        if not is_valid_prefix(normalized):
            return normalized, False
        await self.bot.state.set_server_prefix(guild_id, normalized)
        await self.bot.state.save()
        return normalized, True

    async def _do_set_default_roll(self, guild_id: int, expression: str) -> tuple[str, str | None]:
        """Returns (normalized_expression, error_message). If error_message is
        None, the value was stored successfully."""
        cleaned = expression.strip()
        parsed, normalized, target = parse_roll_input(cleaned)
        if parsed is None or not parsed.has_dice:
            try:
                parse(cleaned)
            except DiceParseError as exc:
                return cleaned, str(exc)
            return cleaned, "no dice in expression"
        if target is not None:
            return normalized, f"unexpected target name {target!r}"
        await self.bot.state.set_server_default_roll(guild_id, normalized)
        await self.bot.state.save()
        return normalized, None

    @commands.command(name="setlang")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def set_language(self, ctx: commands.Context, lang: str) -> None:
        """Set the bot's language for this server. Available: en, fr, de, es."""
        current_lang = self._lang(ctx)
        assert ctx.guild is not None
        normalized, ok = await self._do_set_language(ctx.guild.id, lang)
        if not ok:
            await ctx.send(t(current_lang, "lang_invalid"))
            return
        await ctx.send(t(normalized, "lang_set", lang=normalized))

    @commands.command(name="setprefix")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def set_prefix(self, ctx: commands.Context, *, prefix: str) -> None:
        """Set a custom command prefix for this server."""
        lang = self._lang(ctx)
        assert ctx.guild is not None
        normalized, ok = await self._do_set_prefix(ctx.guild.id, prefix)
        if not ok:
            await ctx.send(t(lang, "prefix_invalid"))
            return
        await ctx.send(t(lang, "prefix_set", prefix=normalized))

    @commands.command(name="defaultRoll", aliases=["defaultroll"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 3, commands.BucketType.guild)
    async def set_default_roll(self, ctx: commands.Context, *, expression: str) -> None:
        """Set the default dice expression used when ``!roll`` has no argument."""
        lang = self._lang(ctx)
        assert ctx.guild is not None
        normalized, error = await self._do_set_default_roll(ctx.guild.id, expression)
        if error is not None:
            await ctx.send(t(lang, "defaultroll_invalid", error=error))
            return
        await ctx.send(t(lang, "defaultroll_set", expression=normalized))

    @discord.slash_command(name="setlang", description="Set the bot's language for this server")
    @discord.default_permissions(manage_guild=True)
    async def set_language_slash(
        self,
        ctx: discord.ApplicationContext,
        lang: discord.Option(  # type: ignore[valid-type]
            str, description="Language", choices=sorted(SUPPORTED_LANGUAGES)
        ),
    ) -> None:
        if not await self._slash_cooldown(ctx, "setlang"):
            return
        if ctx.guild_id is None:
            await ctx.respond(t("en", "guild_only"), ephemeral=True)
            return
        normalized, ok = await self._do_set_language(ctx.guild_id, lang)
        if not ok:
            await ctx.respond(t(self._lang(ctx), "lang_invalid"), ephemeral=True)
            return
        await ctx.respond(t(normalized, "lang_set", lang=normalized))

    @discord.slash_command(
        name="setprefix", description="Set a custom command prefix for this server"
    )
    @discord.default_permissions(manage_guild=True)
    async def set_prefix_slash(
        self,
        ctx: discord.ApplicationContext,
        prefix: discord.Option(  # type: ignore[valid-type]
            str, description="New prefix (1-5 visible non-alphanumeric characters)"
        ),
    ) -> None:
        if not await self._slash_cooldown(ctx, "setprefix"):
            return
        if ctx.guild_id is None:
            await ctx.respond(t("en", "guild_only"), ephemeral=True)
            return
        lang = self.bot.state.get_server_language(ctx.guild_id)
        normalized, ok = await self._do_set_prefix(ctx.guild_id, prefix)
        if not ok:
            await ctx.respond(t(lang, "prefix_invalid"), ephemeral=True)
            return
        await ctx.respond(t(lang, "prefix_set", prefix=normalized))

    @discord.slash_command(
        name="defaultroll",
        description="Set the default dice expression for !roll without arguments",
    )
    @discord.default_permissions(manage_guild=True)
    async def set_default_roll_slash(
        self,
        ctx: discord.ApplicationContext,
        expression: discord.Option(  # type: ignore[valid-type]
            str, description="Dice expression (e.g. 1d20)"
        ),
    ) -> None:
        if not await self._slash_cooldown(ctx, "defaultroll"):
            return
        if ctx.guild_id is None:
            await ctx.respond(t("en", "guild_only"), ephemeral=True)
            return
        lang = self.bot.state.get_server_language(ctx.guild_id)
        normalized, error = await self._do_set_default_roll(ctx.guild_id, expression)
        if error is not None:
            await ctx.respond(t(lang, "defaultroll_invalid", error=error), ephemeral=True)
            return
        await ctx.respond(t(lang, "defaultroll_set", expression=normalized))


def setup(bot: SirrMizan) -> None:
    bot.add_cog(SettingsCog(bot))
