"""Bot subclass and lifecycle orchestration."""
from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from .config import Config
from .state import State
from .translations import t

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("pi_bot.audit")

_EXTENSIONS: tuple[str, ...] = (
    "pi_bot.cogs.dice",
    "pi_bot.cogs.settings",
    "pi_bot.cogs.help",
)


class PiBot(commands.Bot):
    """Bot subclass holding shared ``State`` and ``Config``."""

    def __init__(self, config: Config, state: State) -> None:
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.guilds = True

        super().__init__(
            command_prefix=self._resolve_prefix,
            intents=intents,
            help_command=None,
        )
        self.config = config
        self.state = state
        self._save_task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # Prefix resolution
    # ------------------------------------------------------------------
    def _resolve_prefix(
        self, _bot: commands.Bot, message: discord.Message
    ) -> str:
        if message.guild is None:
            return self.config.default_prefix
        return self.state.get_server_prefix(
            message.guild.id, self.config.default_prefix
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def setup_hook(self) -> None:
        for extension in _EXTENSIONS:
            try:
                self.load_extension(extension)
            except Exception:
                logger.exception("Failed to load extension %s", extension)
                raise
            logger.info("Loaded extension %s", extension)

        self._save_task = asyncio.create_task(self._save_loop(), name="pi-bot-saver")

    async def on_ready(self) -> None:
        user = self.user
        logger.info(
            "Connected as %s (id=%s)",
            user,
            user.id if user is not None else "?",
        )

    async def on_command_error(
        self, ctx: commands.Context, error: Exception
    ) -> None:
        lang = self.state.get_server_language(ctx.guild.id if ctx.guild else None)
        prefix = (ctx.clean_prefix or self.config.default_prefix).strip()

        if isinstance(error, commands.CommandNotFound):
            return  # Silent — common case, avoid spam.
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(t(lang, "missing_permission"))
            return
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(t(lang, "guild_only"))
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                t(lang, "missing_argument", name=error.param.name, prefix=prefix)
            )
            return
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(t(lang, "command_cooldown", seconds=error.retry_after))
            return
        if isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send(t(lang, "command_cooldown", seconds=1.0))
            return
        if isinstance(error, commands.UserInputError):
            await ctx.send(f"❌ {error}")
            return

        logger.exception(
            "Unhandled command error in %s", ctx.command, exc_info=error
        )
        await ctx.send(t(lang, "unexpected_error"))

    async def close(self) -> None:
        if self._save_task is not None:
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
            self._save_task = None
        try:
            await self.state.save()
        except Exception:
            logger.exception("Final save failed")
        await super().close()

    # ------------------------------------------------------------------
    # Periodic saver
    # ------------------------------------------------------------------
    async def _save_loop(self) -> None:
        interval = self.config.save_interval
        while True:
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                return
            if self.state.is_dirty:
                try:
                    await self.state.save()
                except Exception:
                    logger.exception("Periodic save failed")

    # ------------------------------------------------------------------
    # Entry point used by ``__main__``
    # ------------------------------------------------------------------
    async def run_lifecycle(self) -> None:
        try:
            await self.start(self.config.token)
        finally:
            if not self.is_closed():
                await self.close()
