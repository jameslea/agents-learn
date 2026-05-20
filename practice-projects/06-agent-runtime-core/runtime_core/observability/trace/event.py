from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class TraceEventType(str, Enum):
    """Trace 事件类型。"""

    TASK_STARTED = "task_started"
    TASK_FINISHED = "task_finished"
    STEP_STARTED = "step_started"
    STEP_PASSED = "step_passed"
    STEP_FAILED = "step_failed"
    ARTIFACT_CREATED = "artifact_created"
    ARTIFACT_CONSUMED = "artifact_consumed"
    TOOL_CALLED = "tool_called"
    HUMAN_REQUIRED = "human_required"

class TraceEvent(BaseModel):
    """一条可复盘的 runtime 事件。

    `summary` 保存人类可读摘要；`data` 保存结构化摘要字段。两者都不应包含
    完整上下文、完整 artifact payload 或密钥。
    """

    event_id: str = Field(description="事件 ID，通常由 recorder 生成。")
    event_type: TraceEventType = Field(description="事件类型。")
    task_id: str = Field(description="任务 ID。")
    step_id: str = Field(default="", description="关联 step id，可为空。")
    timestamp: str = Field(default_factory=utc_now, description="事件时间，UTC ISO 格式。")
    summary: str = Field(default="", description="事件摘要。")
    data: dict[str, Any] = Field(default_factory=dict, description="结构化摘要数据。")
    risk: str = Field(default="low", description="风险等级，例如 low、medium、high。")
    recoverable: bool = Field(default=True, description="失败或阻塞是否可恢复。")
