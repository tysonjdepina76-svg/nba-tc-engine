"""logging.py — Centralized logging for TC Sports App."""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("/home/workspace/tc-sports-app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

_LOGGERS: dict[str, logging.Logger] = {}


def setup_logging(name: str = "tc", level: int = logging.INFO) -> logging.Logger:
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FMT))
        logger.addHandler(stream_handler)

        today = datetime.now().strftime("%Y-%m-%d")
        file_handler = logging.FileHandler(LOG_DIR / f"{name}_{today}.log")
        file_handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FMT))
        logger.addHandler(file_handler)

    _LOGGERS[name] = logger
    return logger
