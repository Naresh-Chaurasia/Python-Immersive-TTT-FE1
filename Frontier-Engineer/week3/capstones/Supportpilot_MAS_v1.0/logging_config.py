"""
SupportPilot — centralized logging setup.

One consistent, readable log format for the whole app: `HH:MM:SS LEVEL
module: message`. Level defaults to INFO; set SUPPORTPILOT_LOG_LEVEL=DEBUG
for more detail (e.g. per-lookup and per-query traces).

Logs go to both the console and a supportpilot.log file (next to this
script), so every run is also saved for later review. Set
SUPPORTPILOT_LOG_FILE=0 to disable file logging.

Usage in any module:
    from logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("...")
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(__file__).parent / "supportpilot.log"

_CONFIGURED = False


def configure_logging() -> None:
    """Set up console + file log handlers once. Safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = os.environ.get("SUPPORTPILOT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    datefmt = "%H:%M:%S"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if os.environ.get("SUPPORTPILOT_LOG_FILE", "1") != "0":
        handlers.append(logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8"))
        # Visual separator so each run is easy to spot when scrolling the file
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n----- run started {datetime.now().isoformat(timespec='seconds')} -----\n")

    for h in handlers:
        h.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = handlers  # replace any pre-existing handlers, avoid duplicates
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger, configuring the app's logging on first use."""
    configure_logging()
    return logging.getLogger(name)
