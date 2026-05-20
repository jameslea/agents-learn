from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from runtime_core.observability.trace.event import TraceEvent


class TraceReplaySummary(BaseModel):
    """从 trace 中得到的复盘摘要。"""

    task_id: str = Field(description="任务 ID。")
    event_count: int = Field(description="事件总数。")
    event_type_counts: dict[str, int] = Field(default_factory=dict, description="按事件类型统计。")
    failed_steps: list[dict[str, Any]] = Field(default_factory=list, description="失败 step 摘要。")
    artifact_flow: list[dict[str, Any]] = Field(default_factory=list, description="artifact 生成和消费关系。")
    risk_events: list[dict[str, Any]] = Field(default_factory=list, description="medium/high 风险事件。")
    human_required: list[dict[str, Any]] = Field(default_factory=list, description="需要人工介入的事件。")

def _event_brief(event: TraceEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "step_id": event.step_id,
        "summary": event.summary,
        "data": event.data,
        "risk": event.risk,
        "recoverable": event.recoverable,
    }
