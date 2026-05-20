from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime_core.observability.trace.event import TraceEvent, TraceEventType
from runtime_core.observability.trace.rules.redaction import _redact_value


class TraceRecorder:
    """JSONL Trace 写入器。"""

    def __init__(self, path: str | Path, *, reset: bool = False) -> None:
        self.path = Path(path)
        self._next_index = 1
        if reset and self.path.exists():
            self.path.unlink()
        if self.path.exists():
            self._next_index = sum(1 for _ in self.path.open("r", encoding="utf-8")) + 1

    def record(
        self,
        *,
        event_type: TraceEventType,
        task_id: str,
        step_id: str = "",
        summary: str = "",
        data: dict[str, Any] | None = None,
        risk: str = "low",
        recoverable: bool = True,
    ) -> TraceEvent:
        """记录一条事件，并写入 JSONL。"""
        event = TraceEvent(
            event_id=f"trace-{self._next_index:04d}",
            event_type=event_type,
            task_id=task_id,
            step_id=step_id,
            summary=_redact_value(summary),
            data=_redact_value(data or {}),
            risk=risk,
            recoverable=recoverable,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")
        self._next_index += 1
        return event

    def task_started(self, *, task_id: str, task_type: str, goal_summary: str) -> TraceEvent:
        return self.record(
            event_type=TraceEventType.TASK_STARTED,
            task_id=task_id,
            summary=f"Task started: {goal_summary}",
            data={"task_type": task_type, "goal_summary": goal_summary},
        )

    def task_finished(self, *, task_id: str, final_status: str, summary: str = "") -> TraceEvent:
        return self.record(
            event_type=TraceEventType.TASK_FINISHED,
            task_id=task_id,
            summary=summary or f"Task finished with status {final_status}",
            data={"final_status": final_status},
        )
