"""Dice rolling commands."""
from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from .. import colors
from ..dice_parser import DiceParseError, ParsedExpression, parse
from ..translations import t

if TYPE_CHECKING:
    from ..bot import PiBot

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("pi_bot.audit")

# SystemRandom is seeded from the OS entropy pool — appropriate when fairness
# matters to users.
_RNG = secrets.SystemRandom()

_HIGH_ROLL_THRESHOLD = 999


class DiceCog(commands.Cog):
    def __init__(self, bot: "PiBot") -> None:
        self.bot = bot

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _lang(self, ctx: commands.Context) -> str:
        return self.bot.state.get_server_language(
            ctx.guild.id if ctx.guild else None
        )

    def _author_color(self, user_id: int) -> discord.Color:
        return discord.Color(self.bot.state.get_user_color_hex(user_id))

    def _roll_dice(
        self, expr: ParsedExpression
    ) -> tuple[int, list[str], list[int]]:
        """Roll the dice from ``expr`` and return (total, summary_lines, signed_results)."""
        dice_total = 0
        summary_lines: list[str] = []
        signed_results: list[int] = []

        for part in expr.dice:
            results = [_RNG.randint(1, part.faces) for _ in range(part.rolls)]
            dice_total += part.sign * sum(results)
            sign_prefix = "" if part.sign > 0 else "-"
            summary_lines.append(
                f"{sign_prefix}{part.rolls}d{part.faces}: "
                + ", ".join(str(r) for r in results)
            )
            for r in results:
                signed_results.append(part.sign * r)

        return dice_total + expr.modifier_total, summary_lines, signed_results

    @staticmethod
    def _format_calculation(
        signed_results: list[int], modifiers: tuple[int, ...]
    ) -> str:
        parts: list[str] = []
        for value in signed_results:
            parts.append(str(value))
        for mod in modifiers:
            parts.append(f"{mod:+d}")
        if not parts:
            return ""
        first, *rest = parts
        out = first
        for token in rest:
            if token.startswith("-"):
                out += f" - {token[1:]}"
            elif token.startswith("+"):
                out += f" + {token[1:]}"
            else:
                out += f" + {token}"
        return out

    def _build_embed(
        self,
        ctx: commands.Context,
        *,
        total: int,
        summary_lines: list[str],
        signed_results: list[int],
        modifiers: tuple[int, ...],
        target_name: Optional[str],
    ) -> discord.Embed:
        lang = self._lang(ctx)
        embed = discord.Embed(
            title=f"🎲 {t(lang, 'embed_result')}: **{total}**",
            description=(
                f"🔻 {t(lang, 'embed_for')} **{target_name}**" if target_name else None
            ),
            color=self._author_color(ctx.author.id),
        )
        if summary_lines:
            embed.add_field(
                name=t(lang, "embed_dice_details"),
                value="\n".join(summary_lines),
                inline=False,
            )

        # Show calculation only when there is meaningful structure to show.
        show_calc = (len(signed_results) + len(modifiers)) > 1
        if show_calc:
            value = self._format_calculation(signed_results, modifiers)
            if value:
                embed.add_field(
                    name=t(lang, "embed_calculation"), value=value, inline=False
                )

        avatar_url: Optional[str] = None
        guild_avatar = getattr(ctx.author, "guild_avatar", None)
        if guild_avatar is not None:
            avatar_url = guild_avatar.url
        elif ctx.author.avatar is not None:
            avatar_url = ctx.author.avatar.url

        embed.set_footer(
            text=f"{t(lang, 'embed_rolled_by')} {ctx.author.display_name}",
            icon_url=avatar_url,
        )
        return embed

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    @commands.command(name="roll", aliases=["r"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def roll(
        self, ctx: commands.Context, *, args: Optional[str] = None
    ) -> None:
        """Roll dice. Example: ``!roll 2d6+3 Goblin``."""
        lang = self._lang(ctx)
        guild_id = ctx.guild.id if ctx.guild else None
        default_roll = self.bot.state.get_server_default_roll(guild_id)
        prefix = (ctx.clean_prefix or self.bot.config.default_prefix).strip()

        raw = (args or "").strip()
        if not raw:
            if default_roll is None:
                await ctx.send(t(lang, "defaultroll_missing", prefix=prefix))
                return
            raw = default_roll

        if len(raw) > 100:
            await ctx.send(t(lang, "roll_input_too_long"))
            return

        # Split: first whitespace-delimited token is the expression, rest is
        # an optional target name.
        head, _, tail = raw.partition(" ")
        target_name = tail.strip() or None

        try:
            expr = parse(head)
        except DiceParseError as exc:
            # Maybe the user wanted to use the default roll with a target name:
            # `!r Goblin` → use default + name "Goblin".
            if default_roll is not None and target_name is None:
                try:
                    expr = parse(default_roll)
                    target_name = head
                except DiceParseError:
                    await ctx.send(t(lang, "roll_invalid", error=str(exc)))
                    return
            else:
                await ctx.send(t(lang, "roll_invalid", error=str(exc)))
                return

        if expr.is_empty:
            await ctx.send(t(lang, "roll_invalid", error="no dice or modifier"))
            return

        total, summary_lines, signed_results = self._roll_dice(expr)
        await self.bot.state.increment_dice_rolls(ctx.author.id)

        if total > _HIGH_ROLL_THRESHOLD:
            audit_logger.info(
                "high_roll user=%s guild=%s total=%d expression=%r",
                ctx.author.id,
                guild_id,
                total,
                head,
            )

        embed = self._build_embed(
            ctx,
            total=total,
            summary_lines=summary_lines,
            signed_results=signed_results,
            modifiers=expr.modifiers,
            target_name=target_name,
        )
        await ctx.send(embed=embed)

        # Best-effort cleanup of the invocation message in guilds where the
        # bot has Manage Messages.
        if ctx.guild is not None:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                pass

    @commands.command(name="setcolor")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def set_color(self, ctx: commands.Context, color: str) -> None:
        """Set your preferred embed color."""
        lang = self._lang(ctx)
        try:
            canonical = await self.bot.state.set_user_color(ctx.author.id, color)
        except ValueError:
            options = ", ".join(sorted(colors.CANONICAL_COLORS))
            await ctx.send(t(lang, "color_unknown", options=options))
            return
        await ctx.send(t(lang, "color_set", color=canonical))

    @commands.command(name="getcolor")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def get_color(self, ctx: commands.Context) -> None:
        """Show your preferred embed color."""
        lang = self._lang(ctx)
        name = self.bot.state.get_user_color_name(ctx.author.id)
        await ctx.send(t(lang, "color_current", color=name))


def setup(bot: commands.Bot) -> None:
    bot.add_cog(DiceCog(bot))  # type: ignore[arg-type]
