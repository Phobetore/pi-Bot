"""Entry point: ``python -m sirrmizan``."""
from __future__ import annotations

import asyncio
import logging
import sys

import discord

from .bot import SirrMizan
from .config import ConfigError, load_config
from .logging_setup import configure_logging
from .state import State

logger = logging.getLogger(__name__)


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
        asyncio.run(bot.run_lifecycle())
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
