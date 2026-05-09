"""Entry point: ``python -m sirrmizan``."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys

import discord

from .bot import SirrMizan
from .config import ConfigError, load_config
from .logging_setup import configure_logging
from .state import State

logger = logging.getLogger(__name__)


async def _run_with_signals(bot: SirrMizan) -> None:
    """Install POSIX signal handlers so SIGTERM/SIGINT trigger a clean
    shutdown that flushes state. On Windows ``loop.add_signal_handler`` is
    not supported and we rely on Ctrl-C → KeyboardInterrupt instead.
    """
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _request_stop(signame: str) -> None:
        logger.info("Received %s — shutting down", signame)
        stop.set()

    for signame in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(
                getattr(signal, signame), _request_stop, signame
            )
        except (NotImplementedError, AttributeError):
            # Windows or non-main thread — Python's default handlers cover us.
            pass

    bot_task = asyncio.create_task(bot.run_lifecycle(), name="sirrmizan-main")
    stop_task = asyncio.create_task(stop.wait(), name="sirrmizan-stop-signal")

    try:
        done, pending = await asyncio.wait(
            {bot_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if stop_task in done and not bot_task.done():
            await bot.close()
            try:
                async with asyncio.timeout(30):
                    try:
                        await bot_task
                    except asyncio.CancelledError:
                        pass
            except TimeoutError:
                logger.warning("bot did not exit within 30s; forcing")
        # Surface any exception raised by the bot lifecycle.
        if bot_task.done():
            bot_task.result()
    finally:
        for task in (bot_task, stop_task):
            if not task.done():
                task.cancel()


def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    configure_logging(config.log_dir, config.log_level)
    logger.info("Starting SirrMizan")

    state = State(config.data_dir)
    state.load()

    bot = SirrMizan(config=config, state=state)

    try:
        asyncio.run(_run_with_signals(bot))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except discord.LoginFailure as exc:
        print(f"Discord login failed: {exc}", file=sys.stderr)
        print(
            "Verify SIRRMIZAN_TOKEN is correct and the bot has not been "
            "regenerated or revoked.",
            file=sys.stderr,
        )
        return 3
    except discord.PrivilegedIntentsRequired as exc:
        print(f"Privileged intents missing: {exc}", file=sys.stderr)
        print(
            "Enable 'MESSAGE CONTENT INTENT' for the bot in the Discord "
            "Developer Portal: Bot → Privileged Gateway Intents.",
            file=sys.stderr,
        )
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
