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
    """Run the bot. SIGINT/SIGTERM trigger ``bot.close()`` (POSIX only).

    Closing the bot causes ``bot.start()`` to return naturally; the recommended
    py-cord pattern. We don't await the bot from outside while also closing it
    (that path was racing aiohttp's session cleanup and emitted
    ``RuntimeError: Session is closed`` on shutdown).
    """
    loop = asyncio.get_running_loop()
    closing = False
    shutdown_task: asyncio.Task[None] | None = None

    async def _shutdown() -> None:
        nonlocal closing
        if closing:
            return
        closing = True
        try:
            async with asyncio.timeout(30):
                await bot.close()
        except TimeoutError:
            logger.warning("bot.close() exceeded 30s timeout")
        except Exception:
            logger.exception("error during bot.close()")

    def _request_stop(signame: str) -> None:
        nonlocal shutdown_task
        logger.info("Received %s — shutting down", signame)
        # Hold a reference so the task isn't garbage-collected mid-flight.
        shutdown_task = loop.create_task(_shutdown(), name="sirrmizan-shutdown")

    for signame in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, signame), _request_stop, signame)
        except (NotImplementedError, AttributeError):
            pass  # not supported on Windows

    await bot.run_lifecycle()


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
            "Verify SIRRMIZAN_TOKEN is correct and the bot has not been regenerated or revoked.",
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
