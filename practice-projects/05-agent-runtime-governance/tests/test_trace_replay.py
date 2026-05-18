from __future__ import annotations

import json

import pytest

from runtime.trace import RuntimeTraceRecorder, TraceEventType
from runtime.trace_replay import load_trace, render_timeline, summarize_trace


def test_trace_recorder_overwrites_same_path_by_default(tmp_path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    first = RuntimeTraceRecorder(trace_path)
    first.record(TraceEventType.TASK_STARTED, {"task_id": "old"})

    second = RuntimeTraceRecorder(trace_path)
    second.record(TraceEventType.TASK_STARTED, {"task_id": "new"})

    entries = load_trace(trace_path)
    assert len(entries) == 1
    assert entries[0].payload["task_id"] == "new"


def test_trace_replay_summarizes_runtime_events(tmp_path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    recorder = RuntimeTraceRecorder(trace_path)
    recorder.record(
        TraceEventType.TASK_STARTED,
        {
            "task_id": "t1",
            "task_type": "document_governance",
            "goal": "Check report quality.",
        },
    )
    recorder.record(
        TraceEventType.TOOL_DECISION,
        {
            "tool_name": "report.write_improvement_patch",
            "decision": "needs_human",
            "reason": "Tool requires human approval before execution.",
        },
    )
    recorder.record(
        TraceEventType.HUMAN_REVIEW_REQUESTED,
        {
            "tool_name": "report.write_improvement_patch",
            "reason": "approval required",
        },
    )
    recorder.record(
        TraceEventType.ARTIFACT_CREATED,
        {
            "artifact_type": "human_review_request",
            "artifact_id": "a1",
        },
    )
    recorder.record(
        TraceEventType.TASK_FINISHED,
        {
            "task_id": "t1",
            "task_name": "report.md",
            "status": "needs_human",
            "score": 0.82,
            "reason": "Needs approval.",
        },
    )

    summary = summarize_trace(trace_path)
    timeline = render_timeline(trace_path)

    assert summary.task_id == "t1"
    assert summary.final_status == "needs_human"
    assert summary.final_score == 0.82
    assert summary.tool_decisions == {"needs_human": 1}
    assert summary.artifacts_created == {"human_review_request": 1}
    assert summary.human_review_requested == 1
    assert "report.write_improvement_patch -> needs_human" in timeline
    assert "Final reason: Needs approval." in timeline


def test_trace_replay_reports_invalid_json_line(tmp_path) -> None:
    trace_path = tmp_path / "broken.jsonl"
    trace_path.write_text(
        json.dumps({"timestamp": "2026-01-01T00:00:00+00:00", "event": "task_started", "payload": {}})
        + "\nnot-json\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="broken.jsonl:2"):
        load_trace(trace_path)
