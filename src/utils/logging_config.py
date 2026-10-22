"""
Safe logging configuration for Smart Route AI.
Prevents sensitive API keys from appearing in logs.
"""
import logging
import sys
from typing import Any
from src.config.settings import settings


class RedactingFormatter(logging.Formatter):
    """Filter to ensure known secrets never appear in logs."""
    def __init__(self, fmt: str = None, datefmt: str = None):
        super().__init__(fmt, datefmt)
        self.secrets = [
            settings.CARTO_API_KEY,
            settings.MAP_API_KEY,
            settings.WEATHER_API_KEY,
            settings.TRAFFIC_API_KEY,
        ]
        self.secrets = [s for s in self.secrets if s and len(s) > 4]

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        for s in self.secrets:
            if s in original:
                original = original.replace(s, "[REDACTED_API_KEY]")
        return original


def setup_logger(name: str = "SmartRouteAI") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        fmt = "%(asctime)s | %(levelname)-7s | [%(name)s] %(message)s"
        formatter = RedactingFormatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logger()
