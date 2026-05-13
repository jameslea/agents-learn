import logging
import os
import time
from contextlib import contextmanager
from typing import Iterator


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
DATE_FORMAT = "%H:%M:%S"


def configure_logging(level: str | None = None) -> None:
    """Configure process-wide logging once."""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        force=False,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


@contextmanager
def timed_block(
    logger: logging.Logger,
    label: str,
    *,
    slow_after: float = 10.0,
    level: int = logging.INFO,
) -> Iterator[None]:
    """Log elapsed time for a block and warn when it is slow."""
    start = time.perf_counter()
    logger.debug("开始: %s", label)
    try:
        yield
    except Exception:
        elapsed = time.perf_counter() - start
        logger.exception("失败: %s，用时 %.2fs", label, elapsed)
        raise
    else:
        elapsed = time.perf_counter() - start
        if elapsed >= slow_after:
            logger.warning("完成但耗时较长: %s，用时 %.2fs", label, elapsed)
        else:
            logger.log(level, "完成: %s，用时 %.2fs", label, elapsed)

