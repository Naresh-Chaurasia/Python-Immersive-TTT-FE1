"""
Logging configuration for the RAG Knowledge Management system.

Provides a consistent logging setup across all application modules.
Logs are written to both console (stdout) and a rotating log file.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# ── Log Directory ──────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"

# ── Formatter ──────────────────────────────────────────────────
_FORMAT = (
    "[%(asctime)s] %(levelname)-8s | %(name)-18s | %(funcName)-25s | %(message)s"
)
_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FMT)


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger configured for the given *name*.

    The logger writes to:
      - **Console** (stdout)  →  visible when running in a terminal.
      - **Rotating file**     →  ``logs/app.log`` (10 MB per file, 5 backups).

    Usage::

        from app.logger import get_logger
        logger = get_logger(__name__)
        logger.info("…")
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if get_logger is called multiple times.
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ── Console Handler ────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(_formatter)
    logger.addHandler(console_handler)

    # ── Rotating File Handler ──────────────────────────────────
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_formatter)
    logger.addHandler(file_handler)

    return logger