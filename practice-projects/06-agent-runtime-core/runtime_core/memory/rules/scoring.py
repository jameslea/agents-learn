from __future__ import annotations

from runtime_core.memory.record import MemoryRecord


def _normalize_tags(tags: list[str]) -> set[str]:
    return {tag.strip().lower() for tag in tags if tag.strip()}

def _score_memory(record: MemoryRecord, *, query_tags: set[str]) -> float:
    if not query_tags:
        return record.confidence
    record_tags = _normalize_tags(record.tags)
    overlap = record_tags & query_tags
    if not overlap:
        return 0.0
    tag_score = len(overlap) / max(len(query_tags), 1)
    return round(min(1.0, 0.5 * record.confidence + 0.5 * tag_score), 4)
