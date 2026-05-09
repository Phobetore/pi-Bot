"""Custom localized help command."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .. import colors
from ..translations import t
from ._base import BaseCog, slash_cooldown

if TYPE_CHECKING:
    from ..bot import SirrMizan


class HelpCog(BaseCog):
    def _build_help_embed(self, lang: str, prefix: str) -> discord.Embed:
        embed = discord.Embed(
            title=t(lang, "help_title"),
            description=t(lang, "help_description"),
            color=discord.Color.purple(),
        )
        embed.add_field(
            name=f"🎲 `{prefix}roll` / `{prefix}r` — {t(lang, 'roll_title')}",
            value=f"{t(lang, 'roll_desc')}\n```\n{prefix}roll 2d6+3 Goblin\n```",
            inline=False,
        )
        color_options = ", ".join(sorted(colors.CANONICAL_COLORS))
        embed.add_field(
            name=f"🎨 `{prefix}setcolor` — {t(lang, 'setcolor_title')}",
            value=(
                f"{t(lang, 'setcolor_desc')}\n"
                f"{t(lang, 'color_options')}: {color_options}\n"
                f"```\n{prefix}setcolor red\n```"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"✏️ `{prefix}getcolor` — {t(lang, 'getcolor_title')}",
            value=f"{t(lang, 'getcolor_desc')}\n```\n{prefix}getcolor\n```",
            inline=False,
        )
        embed.add_field(
            name=f"📏 `{prefix}setrollshort` — {t(lang, 'rollshort_title')}",
            value=(
                f"{t(lang, 'rollshort_desc')}\n"
                f"```\n{prefix}setrollshort on\n{prefix}setrollshort off\n```"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"🔁 `{prefix}defaultRoll` — {t(lang, 'defaultroll_title')}",
            value=(
                f"{t(lang, 'defaultroll_desc')}\n"
                f"```\n{prefix}defaultRoll 1d20\n```"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"🌐 `{prefix}setlang` — {t(lang, 'setlang_title')}",
            value=f"{t(lang, 'setlang_desc')}\n```\n{prefix}setlang fr\n```",
            inline=False,
        )
        embed.add_field(
            name=f"🔧 `{prefix}setprefix` — {t(lang, 'setprefix_title')}",
            value=f"{t(lang, 'setprefix_desc')}\n```\n{prefix}setprefix ?\n```",
            inline=False,
        )
        embed.set_footer(text=t(lang, "help_footer"))
        return embed

    @commands.command(name="help", aliases=["h"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def help_command(self, ctx: commands.Context) -> None:
        lang = self._lang(ctx)
        prefix = self._prefix(ctx)
        await ctx.send(embed=self._build_help_embed(lang, prefix))

    @discord.slash_command(name="help", description="Show available commands")
    @slash_cooldown(3)
    async def help_slash(self, ctx: discord.ApplicationContext) -> None:
        lang = self.bot.state.get_server_language(
            ctx.guild_id if ctx.guild_id else None
        )
        prefix = self.bot.config.default_prefix
        await ctx.respond(embed=self._build_help_embed(lang, prefix), ephemeral=True)


def setup(bot: "SirrMizan") -> None:
    bot.add_cog(HelpCog(bot))
