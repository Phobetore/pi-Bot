"""Entry point: ``python -m pi_bot``."""
from __future__ import annotations

import asyncio
import logging
import sys

from .bot import PiBot
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
    logger.info("Starting pi-Bot")

    state = State(config.data_dir)
    state.load()

    bot = PiBot(config=config, state=state)

    try:
        asyncio.run(bot.run_lifecycle())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
