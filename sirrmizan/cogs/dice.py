"""Dice rolling commands (prefix + slash)."""

from __future__ import annotations

import logging
import re
import secrets
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .. import colors
from ..dice_parser import DiceParseError, ParsedExpression, parse, parse_roll_input
from ..translations import t
from ._base import BaseCog

if TYPE_CHECKING:
    from ..bot import SirrMizan

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("sirrmizan.audit")

_RNG = secrets.SystemRandom()

_HIGH_ROLL_THRESHOLD = 999
_LOOKS_LIKE_DICE_ATTEMPT = re.compile(r"^[+-]?\d")


class DiceCog(BaseCog):
    def _author_color(self, user_id: int) -> discord.Color:
        return discord.Color(self.bot.state.get_user_color_hex(user_id))

    def _roll_dice(self, expr: ParsedExpression) -> tuple[int, list[tuple[str, list[int]]]]:
        """Roll ``expr`` and return (total, [(label, signed_results), ...])."""
        dice_total = 0
        terms: list[tuple[str, list[int]]] = []
        for part in expr.dice:
            results = [_RNG.randint(1, part.faces) for _ in range(part.rolls)]
            signed = [part.sign * r for r in results]
            dice_total += sum(signed)
            sign_prefix = "" if part.sign > 0 else "-"
            label = f"{sign_prefix}{part.rolls}d{part.faces}"
            terms.append((label, signed))
        return dice_total + expr.modifier_total, terms

    @staticmethod
    def _format_dice_term(label: str, signed_results: list[int]) -> str:
        """Render one dice term: bold individual values, sum if more than one."""
        if len(signed_results) == 1:
            return f"`{label}` → **{abs(signed_results[0])}**"
        # Multiple dice in one term: show each result and the sum.
        rendered = " + ".join(f"**{abs(r)}**" for r in signed_results).replace(" + -", " - ")
        term_total = abs(sum(signed_results))
        return f"`{label}` → {rendered} = **{term_total}**"

    @staticmethod
    def _format_modifiers(modifiers: tuple[int, ...]) -> str:
        if not modifiers:
            return ""
        return "  ".join(f"{m:+d}" for m in modifiers)

    def _build_embed(
        self,
        author: discord.abc.User,
        *,
        total: int,
        expression_str: str,
        terms: list[tuple[str, list[int]]],
        modifiers: tuple[int, ...],
        target_name: str | None,
        lang: str,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=f"🎲 {total}",
            color=self._author_color(author.id),
        )

        # Description: original expression + optional target.
        desc_parts = [f"`{expression_str}`"] if expression_str else []
        if target_name:
            desc_parts.append(f"{t(lang, 'embed_for')} **{target_name}**")
        if desc_parts:
            embed.description = " ".join(desc_parts)

        # Skip the breakdown for a plain "1d20" — the title already shows it.
        single_die_no_mod = len(terms) == 1 and len(terms[0][1]) == 1 and not modifiers
        if terms and not single_die_no_mod:
            lines = [self._format_dice_term(label, signed) for label, signed in terms]
            embed.add_field(
                name=t(lang, "embed_dice"),
                value="\n".join(lines),
                inline=False,
            )

        if modifiers:
            embed.add_field(
                name=t(lang, "embed_modifiers"),
                value=self._format_modifiers(modifiers),
                inline=False,
            )

        # Footer: author + their avatar.
        avatar_url: str | None = None
        guild_avatar = getattr(author, "guild_avatar", None)
        if guild_avatar is not None:
            avatar_url = guild_avatar.url
        elif getattr(author, "avatar", None) is not None:
            avatar_url = author.avatar.url
        embed.set_footer(
            text=f"{t(lang, 'embed_rolled_by')} {author.display_name}",
            icon_url=avatar_url,
        )
        return embed

    @staticmethod
    def _build_compact(
        *,
        total: int,
        expression_str: str,
        terms: list[tuple[str, list[int]]],
        modifiers: tuple[int, ...],
        target_name: str | None,
        lang: str,
    ) -> str:
        """Render the result as a single message line (no embed)."""
        head = f"🎲 **{total}**"
        if expression_str:
            head += f" — `{expression_str}`"
        if target_name:
            head += f" {t(lang, 'embed_for')} **{target_name}**"

        # Per-term breakdown in parentheses.
        breakdown_parts: list[str] = []
        for label, signed in terms:
            if len(signed) == 1:
                breakdown_parts.append(f"{label}={abs(signed[0])}")
            else:
                joined = "+".join(str(abs(r)) for r in signed)
                breakdown_parts.append(f"{label}={joined}")
        for m in modifiers:
            breakdown_parts.append(f"{m:+d}")

        if breakdown_parts:
            return f"{head}  ({', '.join(breakdown_parts)})"
        return head

    async def _resolve_roll(
        self,
        raw: str,
        *,
        lang: str,
        prefix: str,
        guild_id: int | None,
    ) -> tuple[ParsedExpression | None, str, str | None, str | None]:
        """Resolve a roll input into a parsed expression and target.

        Returns ``(expr, expression_str, target, error_message)``. If
        ``error_message`` is non-None, the caller should send it to the user
        and abort. Otherwise ``expr`` is guaranteed to be a non-empty
        ``ParsedExpression``.
        """
        default_roll = self.bot.state.get_server_default_roll(guild_id)
        raw = (raw or "").strip()

        if not raw:
            if default_roll is None:
                return None, "", None, t(lang, "defaultroll_missing", prefix=prefix)
            raw = default_roll

        if len(raw) > 100:
            return None, "", None, t(lang, "roll_input_too_long")

        expr, expression_str, target_name = parse_roll_input(raw)

        if expr is None:
            looks_like_dice = bool(target_name and _LOOKS_LIKE_DICE_ATTEMPT.match(target_name))
            if default_roll is not None and target_name is not None and not looks_like_dice:
                try:
                    expr = parse(default_roll)
                    expression_str = default_roll
                except DiceParseError as exc:
                    return None, "", None, t(lang, "roll_invalid", error=str(exc))
            else:
                try:
                    parse(raw)
                except DiceParseError as exc:
                    return None, "", None, t(lang, "roll_invalid", error=str(exc))
                return None, "", None, t(lang, "roll_invalid", error="no dice or modifier")

        if expr.is_empty:
            return None, "", None, t(lang, "roll_invalid", error="no dice or modifier")
        return expr, expression_str, target_name, None

    async def _send_result(
        self,
        *,
        author: discord.abc.User,
        send_text,
        send_embed,
        compact: bool,
        total: int,
        expression_str: str,
        terms: list[tuple[str, list[int]]],
        modifiers: tuple[int, ...],
        target_name: str | None,
        lang: str,
    ) -> None:
        if compact:
            await send_text(
                self._build_compact(
                    total=total,
                    expression_str=expression_str,
                    terms=terms,
                    modifiers=modifiers,
                    target_name=target_name,
                    lang=lang,
                )
            )
        else:
            await send_embed(
                self._build_embed(
                    author,
                    total=total,
                    expression_str=expression_str,
                    terms=terms,
                    modifiers=modifiers,
                    target_name=target_name,
                    lang=lang,
                )
            )

    @commands.command(name="roll", aliases=["r"])
    @commands.cooldown(1, 1, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def roll(self, ctx: commands.Context, *, args: str | None = None) -> None:
        """Roll dice. Example: ``!roll 2d6+3 Goblin``."""
        lang = self._lang(ctx)
        prefix = self._prefix(ctx)
        guild_id = ctx.guild.id if ctx.guild else None

        expr, expression_str, target_name, error = await self._resolve_roll(
            args or "", lang=lang, prefix=prefix, guild_id=guild_id
        )
        if error is not None:
            await ctx.send(error)
            return
        assert expr is not None  # narrowed by error check

        total, terms = self._roll_dice(expr)
        await self.bot.state.increment_dice_rolls(ctx.author.id)

        if total > _HIGH_ROLL_THRESHOLD:
            audit_logger.info(
                "high_roll user=%s guild=%s total=%d expression=%r",
                ctx.author.id,
                guild_id,
                total,
                expression_str,
            )

        compact = self.bot.state.get_user_compact(ctx.author.id)
        await self._send_result(
            author=ctx.author,
            send_text=lambda content: ctx.send(content=content),
            send_embed=lambda embed: ctx.send(embed=embed),
            compact=compact,
            total=total,
            expression_str=expression_str,
            terms=terms,
            modifiers=expr.modifiers,
            target_name=target_name,
            lang=lang,
        )

        # Try to delete the invocation message; ignore if no permission.
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
        await self.bot.state.save()
        await ctx.send(t(lang, "color_set", color=canonical))

    @commands.command(name="getcolor")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def get_color(self, ctx: commands.Context) -> None:
        """Show your preferred embed color."""
        lang = self._lang(ctx)
        name = self.bot.state.get_user_color_name(ctx.author.id)
        await ctx.send(t(lang, "color_current", color=name))

    @commands.command(name="setrollshort")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def set_roll_short(self, ctx: commands.Context, mode: str | None = None) -> None:
        """Toggle compact roll output for yourself.

        Usage: ``!setrollshort on`` / ``!setrollshort off``. Without an
        argument, prints the current state.
        """
        lang = self._lang(ctx)
        prefix = self._prefix(ctx)

        if mode is None:
            current = self.bot.state.get_user_compact(ctx.author.id)
            status = t(lang, "status_on") if current else t(lang, "status_off")
            await ctx.send(t(lang, "rollshort_status", status=status))
            return

        normalized = mode.strip().lower()
        if normalized in {"on", "true", "1", "yes", "oui"}:
            await self.bot.state.set_user_compact(ctx.author.id, True)
            await self.bot.state.save()
            await ctx.send(t(lang, "rollshort_on"))
        elif normalized in {"off", "false", "0", "no", "non"}:
            await self.bot.state.set_user_compact(ctx.author.id, False)
            await self.bot.state.save()
            await ctx.send(t(lang, "rollshort_off"))
        else:
            await ctx.send(t(lang, "rollshort_invalid", prefix=prefix))

    @discord.slash_command(name="roll", description="Roll dice with an expression like 2d6+3")
    async def roll_slash(
        self,
        ctx: discord.ApplicationContext,
        expression: discord.Option(  # type: ignore[valid-type]
            str,
            description="Dice expression (e.g. 1d20+5). Leave empty for the server default.",
            required=False,
            default=None,
        ),
        target: discord.Option(  # type: ignore[valid-type]
            str,
            description="Optional target name shown on the result.",
            required=False,
            default=None,
        ),
    ) -> None:
        if not await self._slash_cooldown(ctx, "roll", 1.0):
            return
        lang = self.bot.state.get_server_language(ctx.guild_id if ctx.guild_id else None)
        prefix = self.bot.config.default_prefix
        guild_id = ctx.guild_id

        # Combine the two arguments into a single raw string. parse_roll_input
        # is forgiving about both formats.
        raw = (expression or "").strip()
        if target:
            raw = f"{raw} {target}".strip() if raw else target

        expr, expression_str, target_name, error = await self._resolve_roll(
            raw, lang=lang, prefix=prefix, guild_id=guild_id
        )
        if error is not None:
            await ctx.respond(error, ephemeral=True)
            return
        assert expr is not None

        # If the user supplied target as a separate option AND parse_roll_input
        # also pulled one from the expression, the explicit option wins.
        if target:
            target_name = target

        total, terms = self._roll_dice(expr)
        await self.bot.state.increment_dice_rolls(ctx.author.id)

        if total > _HIGH_ROLL_THRESHOLD:
            audit_logger.info(
                "high_roll user=%s guild=%s total=%d expression=%r",
                ctx.author.id,
                guild_id,
                total,
                expression_str,
            )

        compact = self.bot.state.get_user_compact(ctx.author.id)
        if compact:
            await ctx.respond(
                self._build_compact(
                    total=total,
                    expression_str=expression_str,
                    terms=terms,
                    modifiers=expr.modifiers,
                    target_name=target_name,
                    lang=lang,
                )
            )
        else:
            await ctx.respond(
                embed=self._build_embed(
                    ctx.author,
                    total=total,
                    expression_str=expression_str,
                    terms=terms,
                    modifiers=expr.modifiers,
                    target_name=target_name,
                    lang=lang,
                )
            )

    @discord.slash_command(name="setcolor", description="Set your preferred embed color")
    async def set_color_slash(
        self,
        ctx: discord.ApplicationContext,
        color: discord.Option(  # type: ignore[valid-type]
            str,
            description="Color name",
            choices=sorted(colors.CANONICAL_COLORS),
        ),
    ) -> None:
        if not await self._slash_cooldown(ctx, "setcolor"):
            return
        lang = self.bot.state.get_server_language(ctx.guild_id if ctx.guild_id else None)
        try:
            canonical = await self.bot.state.set_user_color(ctx.author.id, color)
        except ValueError:
            options = ", ".join(sorted(colors.CANONICAL_COLORS))
            await ctx.respond(t(lang, "color_unknown", options=options), ephemeral=True)
            return
        await self.bot.state.save()
        await ctx.respond(t(lang, "color_set", color=canonical), ephemeral=True)

    @discord.slash_command(name="getcolor", description="Show your preferred embed color")
    async def get_color_slash(self, ctx: discord.ApplicationContext) -> None:
        if not await self._slash_cooldown(ctx, "getcolor"):
            return
        lang = self.bot.state.get_server_language(ctx.guild_id if ctx.guild_id else None)
        name = self.bot.state.get_user_color_name(ctx.author.id)
        await ctx.respond(t(lang, "color_current", color=name), ephemeral=True)

    @discord.slash_command(
        name="setrollshort",
        description="Toggle compact roll output for yourself",
    )
    async def set_roll_short_slash(
        self,
        ctx: discord.ApplicationContext,
        enabled: discord.Option(  # type: ignore[valid-type]
            bool, description="Enable compact output"
        ),
    ) -> None:
        if not await self._slash_cooldown(ctx, "setrollshort"):
            return
        lang = self.bot.state.get_server_language(ctx.guild_id if ctx.guild_id else None)
        await self.bot.state.set_user_compact(ctx.author.id, enabled)
        await self.bot.state.save()
        key = "rollshort_on" if enabled else "rollshort_off"
        await ctx.respond(t(lang, key), ephemeral=True)


def setup(bot: SirrMizan) -> None:
    bot.add_cog(DiceCog(bot))
