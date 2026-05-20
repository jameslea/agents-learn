from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from runtime_core.observability.trace.event import TraceEvent, TraceEventType
from runtime_core.observability.trace.replay import TraceReplaySummary, _event_brief


class TraceReader:
    """JSONL Trace 读取与复盘。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def read_events(self) -> list[TraceEvent]:
        """读取 trace 文件中的全部事件。"""
        if not self.path.exists():
            return []
        events: list[TraceEvent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                events.append(TraceEvent.model_validate_json(line))
        return events

    def replay(self) -> TraceReplaySummary:
        """根据事件生成一个复盘摘要。"""
        events = self.read_events()
        task_id = events[0].task_id if events else ""
        counts = Counter(event.event_type.value for event in events)
        failed_steps: list[dict[str, Any]] = []
        artifact_flow: list[dict[str, Any]] = []
        risk_events: list[dict[str, Any]] = []
        human_required: list[dict[str, Any]] = []

        for event in events:
            if event.event_type == TraceEventType.STEP_FAILED:
                failed_steps.append(_event_brief(event))
            if event.event_type in {TraceEventType.ARTIFACT_CREATED, TraceEventType.ARTIFACT_CONSUMED}:
                artifact_flow.append(_event_brief(event))
            if event.risk in {"medium", "high"}:
                risk_events.append(_event_brief(event))
            if event.event_type == TraceEventType.HUMAN_REQUIRED:
                human_required.append(_event_brief(event))

        return TraceReplaySummary(
            task_id=task_id,
            event_count=len(events),
            event_type_counts=dict(counts),
            failed_steps=failed_steps,
            artifact_flow=artifact_flow,
            risk_events=risk_events,
            human_required=human_required,
        )
