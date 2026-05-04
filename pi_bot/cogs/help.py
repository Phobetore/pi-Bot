"""Custom localized help command."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .. import colors
from ..translations import t

if TYPE_CHECKING:
    from ..bot import PiBot


class HelpCog(commands.Cog):
    def __init__(self, bot: "PiBot") -> None:
        self.bot = bot

    @commands.command(name="help", aliases=["h"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def help_command(self, ctx: commands.Context) -> None:
        lang = self.bot.state.get_server_language(
            ctx.guild.id if ctx.guild else None
        )
        prefix = (ctx.clean_prefix or self.bot.config.default_prefix).strip()

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
        await ctx.send(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(HelpCog(bot))  # type: ignore[arg-type]
