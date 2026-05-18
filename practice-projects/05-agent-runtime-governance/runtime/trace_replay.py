from __future__ import annotations

"""Trace 回放与摘要。

RuntimeTraceRecorder 只负责把事件写成 JSONL；本模块负责反向读取这些事件，
生成机器可读摘要和人类可读时间线。这样 trace 既可以作为自动评估输入，
也可以作为调试 Agent 行为的复盘材料。

主要类与关系：
- TraceEntry：JSONL 中的一行事件，包含 timestamp、event 和 payload。
- TraceReplaySummary：对一次 trace 的聚合摘要，回答任务终态、调用了哪些工具、
  生成了哪些 artifact、是否触发阻塞或人工介入等问题。

典型关系：
RuntimeTraceRecorder -> trace.jsonl
trace.jsonl -> load_trace(...) -> list[TraceEntry]
list[TraceEntry] -> summarize_trace(...) / render_timeline(...)
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TraceEntry(BaseModel):
    """One parsed JSONL trace event."""

    timestamp: str
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TraceReplaySummary(BaseModel):
    """Machine-readable summary for one replayed trace."""

    trace_path: str
    task_id: str | None = None
    task_name: str | None = None
    final_status: str | None = None
    final_score: float | None = None
    event_count: int
    event_counts: dict[str, int] = Field(default_factory=dict)
    tools_called: list[str] = Field(default_factory=list)
    tool_decisions: dict[str, int] = Field(default_factory=dict)
    steps: list[str] = Field(default_factory=list)
    artifacts_created: dict[str, int] = Field(default_factory=dict)
    blocked_count: int = 0
    human_review_requested: int = 0
    human_review_decided: int = 0
    duration_seconds: float | None = None
    final_reason: str = ""


def load_trace(trace_path: Path) -> list[TraceEntry]:
    """Load a JSONL runtime trace with line-numbered validation errors."""
    entries: list[TraceEntry] = []
    for line_number, line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            entries.append(TraceEntry.model_validate(data))
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"Invalid trace entry at {trace_path}:{line_number}: {error}") from error
    return entries


def summarize_trace(trace_path: Path) -> TraceReplaySummary:
    """Create a compact machine-readable summary for one trace file."""
    entries = load_trace(trace_path)
    event_counts = Counter(entry.event for entry in entries)
    tool_decisions = Counter()
    tools_called: list[str] = []
    steps: list[str] = []
    artifacts = Counter()
    task_id: str | None = None
    task_name: str | None = None
    final_status: str | None = None
    final_score: float | None = None
    final_reason = ""

    for entry in entries:
        payload = entry.payload
        if entry.event == "task_started":
            task_id = payload.get("task_id", task_id)
        elif entry.event == "tool_decision":
            tool_decisions[payload.get("decision", "unknown")] += 1
        elif entry.event == "step_finished":
            steps.append(str(payload.get("step_id", "unknown")))
        elif entry.event == "tool_called":
            tools_called.append(str(payload.get("tool_name", "unknown")))
        elif entry.event == "artifact_created":
            artifacts[payload.get("artifact_type", "unknown")] += 1
        elif entry.event == "task_finished":
            task_id = payload.get("task_id", task_id)
            task_name = payload.get("task_name", task_name)
            final_status = payload.get("status", final_status)
            final_score = payload.get("score", final_score)
            final_reason = payload.get("reason", final_reason)

    return TraceReplaySummary(
        trace_path=str(trace_path),
        task_id=task_id,
        task_name=task_name,
        final_status=final_status,
        final_score=final_score,
        event_count=len(entries),
        event_counts=dict(event_counts),
        tools_called=tools_called,
        tool_decisions=dict(tool_decisions),
        steps=steps,
        artifacts_created=dict(artifacts),
        blocked_count=event_counts["guardrail_blocked"],
        human_review_requested=event_counts["human_review_requested"],
        human_review_decided=event_counts["human_review_decided"],
        duration_seconds=_duration_seconds(entries),
        final_reason=final_reason,
    )


def render_timeline(trace_path: Path) -> str:
    """Render one trace as a short human-readable execution timeline."""
    entries = load_trace(trace_path)
    summary = summarize_trace(trace_path)
    lines = [
        f"Trace: {trace_path}",
        f"Task: {summary.task_id or '-'}",
        f"Status: {summary.final_status or '-'} score={_format_score(summary.final_score)}",
        f"Events: {summary.event_count} duration={_format_duration(summary.duration_seconds)}",
        "",
        "| # | time | event | detail |",
        "|---|------|-------|--------|",
    ]
    for index, entry in enumerate(entries, start=1):
        lines.append(
            f"| {index} | {_short_time(entry.timestamp)} | {entry.event} | {_event_detail(entry)} |"
        )
    if summary.final_reason:
        lines.extend(["", f"Final reason: {summary.final_reason}"])
    return "\n".join(lines)


def _duration_seconds(entries: list[TraceEntry]) -> float | None:
    if len(entries) < 2:
        return None
    start = _parse_timestamp(entries[0].timestamp)
    end = _parse_timestamp(entries[-1].timestamp)
    if not start or not end:
        return None
    return round((end - start).total_seconds(), 3)


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _short_time(value: str) -> str:
    parsed = _parse_timestamp(value)
    if not parsed:
        return value
    return parsed.strftime("%H:%M:%S.%f")[:-3]


def _event_detail(entry: TraceEntry) -> str:
    payload = entry.payload
    if entry.event == "task_started":
        return f"{payload.get('task_type', '-')}: {payload.get('goal', '-')}"
    if entry.event == "step_started":
        return f"{payload.get('step_id', '-')} started: {payload.get('name', '-')}"
    if entry.event == "step_finished":
        return f"{payload.get('step_id', '-')} finished: {payload.get('name', '-')}"
    if entry.event == "step_failed":
        return f"{payload.get('step_id', '-')} failed: {payload.get('error', '-')}"
    if entry.event == "step_skipped":
        return f"{payload.get('step_id', '-')} skipped: {payload.get('reason', '-')}"
    if entry.event == "tool_decision":
        return (
            f"{payload.get('tool_name', '-')} -> {payload.get('decision', '-')}; "
            f"{payload.get('reason', '-')}"
        )
    if entry.event == "tool_called":
        return f"{payload.get('tool_name', '-')} risk={payload.get('risk_level', '-')}"
    if entry.event == "artifact_created":
        return f"{payload.get('artifact_type', '-')} {payload.get('artifact_id', '-')}"
    if entry.event == "human_review_requested":
        return f"{payload.get('tool_name', '-')} needs approval"
    if entry.event == "human_review_decided":
        return f"{payload.get('request_id', '-')} -> {payload.get('decision', '-')}"
    if entry.event == "evaluation_run":
        return (
            f"{payload.get('status', '-')} score={_format_score(payload.get('score'))}; "
            f"{payload.get('reason', '-')}"
        )
    if entry.event == "guardrail_blocked":
        return f"{payload.get('tool_name', '-')} blocked; {payload.get('reason', '-')}"
    if entry.event == "task_finished":
        return (
            f"{payload.get('status', '-')} score={_format_score(payload.get('score'))}; "
            f"{payload.get('reason', '-')}"
        )
    return _compact_payload(payload)


def _compact_payload(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= 120 else f"{text[:117]}..."


def _format_score(score: float | int | None) -> str:
    if score is None:
        return "-"
    return f"{float(score):.3f}"


def _format_duration(duration: float | None) -> str:
    if duration is None:
        return "-"
    return f"{duration:.3f}s"
