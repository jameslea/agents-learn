from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from runtime_core.task import RuntimeState


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class CheckpointRecord(BaseModel):
    """一次 checkpoint 快照。"""

    task_id: str = Field(description="任务 ID。")
    saved_at: str = Field(default_factory=utc_now, description="保存时间，UTC ISO 格式。")
    state: RuntimeState = Field(description="可恢复的 RuntimeState。")
