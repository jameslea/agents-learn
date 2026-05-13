"""Lightweight runtime cost instrumentation."""
import json
import time
from contextlib import contextmanager
from typing import Any, Iterator


def payload_chars(payload: Any) -> int:
    if payload is None:
        return 0
    if isinstance(payload, str):
        return len(payload)
    try:
        return len(json.dumps(payload, ensure_ascii=False, default=str))
    except TypeError:
        return len(str(payload))


@contextmanager
def tracked_call(
    logger,
    operation: str,
    input_payload: Any = None,
    cache_hit: bool | None = None,
) -> Iterator[dict[str, Any]]:
    """Log input/output character counts and elapsed time for one operation."""
    started = time.perf_counter()
    record: dict[str, Any] = {"output_payload": None}
    try:
        yield record
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        output_payload = record.get("output_payload")
        logger.info(
            "成本观测: operation=%s input_chars=%d output_chars=%d elapsed_ms=%d cache_hit=%s",
            operation,
            payload_chars(input_payload),
            payload_chars(output_payload),
            elapsed_ms,
            cache_hit,
        )
