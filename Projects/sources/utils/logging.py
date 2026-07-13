"""
Unified logging configuration.
"""

import logging
from datetime import datetime
from pathlib import Path

def setup_logging(level=logging.INFO):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"logs/tc_{datetime.now().strftime('%Y%m%d')}.log")
        ]
    )
    return logging.getLogger(__name__)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
