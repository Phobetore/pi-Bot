"""Backward-compatible entry point.

Prefer ``python -m pi_bot``. This wrapper exists so existing deployment
scripts that invoke ``python main.py`` keep working.
"""
from __future__ import annotations

import sys

from pi_bot.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
