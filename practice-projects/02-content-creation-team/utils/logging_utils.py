import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
DATE_FORMAT = "%H:%M:%S"
PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = PROJECT_DIR / "logs"


def configure_logging(level: str | None = None) -> None:
    """Configure process-wide logging once."""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if os.getenv("CONTENT_TEAM_LOG_TO_FILE", "1").lower() not in {"0", "false", "no"}:
        log_dir = Path(os.getenv("CONTENT_TEAM_LOG_DIR", str(DEFAULT_LOG_DIR)))
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(log_dir / f"run_{timestamp}.log", encoding="utf-8")
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=handlers,
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
