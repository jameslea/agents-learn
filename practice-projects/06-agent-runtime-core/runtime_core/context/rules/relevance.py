from __future__ import annotations

from datetime import datetime, timezone


def _normalize_tags(tags: list[str]) -> list[str]:
    return sorted({tag.strip().lower() for tag in tags if tag.strip()})


def _is_expired(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    try:
        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires < datetime.now(timezone.utc)


def score_by_tags(candidate_tags: list[str], step_tags: list[str]) -> float:
    candidate = set(_normalize_tags(candidate_tags))
    current = set(step_tags)
    if not candidate or not current:
        return 0.0
    overlap = candidate & current
    if not overlap:
        return 0.0
    return min(1.0, 0.5 + len(overlap) / max(len(current), 1))
