"""Bot subclass and lifecycle orchestration."""
from __future__ import annotations

import asyncio
import logging
import pkgutil

import discord
from discord.ext import commands

from . import cogs as _cogs_pkg
from .config import Config
from .state import State
from .translations import t

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("sirrmizan.audit")


def _discover_extensions() -> tuple[str, ...]:
    """Return all public cog module dotted-paths under ``sirrmizan.cogs``.

    Modules whose name starts with ``_`` (e.g. ``_base``) are excluded.
    """
    return tuple(
        f"{_cogs_pkg.__name__}.{module.name}"
        for module in pkgutil.iter_modules(_cogs_pkg.__path__)
        if not module.name.startswith("_")
    )


class SirrMizan(commands.Bot):
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
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.config = config
        self.state = state
        self._save_task: asyncio.Task[None] | None = None

        # Load every cog right at construction time. This works across
        # py-cord versions because ``load_extension`` is synchronous and
        # ``add_cog`` does not require a running event loop. Doing it here
        # avoids relying on ``setup_hook``, which behaves differently across
        # forks and versions.
        for extension in _discover_extensions():
            try:
                self.load_extension(extension)
            except Exception:
                logger.exception("Failed to load extension %s", extension)
                raise
            logger.info("Loaded extension %s", extension)

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
    async def on_ready(self) -> None:
        user = self.user
        logger.info(
            "Connected as %s (id=%s)",
            user,
            user.id if user is not None else "?",
        )
        # ``on_ready`` may fire more than once on reconnect; guard against
        # spawning duplicate save tasks.
        if self._save_task is None or self._save_task.done():
            self._save_task = asyncio.create_task(
                self._save_loop(), name="sirrmizan-saver"
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
            # The exception text may echo user input; truncate and rely on the
            # bot's global allowed_mentions=None to neutralize stray pings.
            text = discord.utils.escape_mentions(str(error))[:200]
            await ctx.send(f"❌ {text}")
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
