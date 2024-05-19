import sys

from loguru import logger


def set_log_level(level: str = "INFO") -> None:
    logger.remove()
    logger.add(sys.stderr, level=level)


def get_logger() -> logger:
    return logger
