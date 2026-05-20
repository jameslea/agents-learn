from __future__ import annotations

from runtime_core.observability import TraceEventType, TraceReader, TraceRecorder, has_sensitive_plaintext


def test_trace_recorder_writes_and_reader_loads_jsonl(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    recorder = TraceRecorder(path)

    recorder.task_started(task_id="task:trace", task_type="research", goal_summary="trace test")
    recorder.record(
        event_type=TraceEventType.STEP_STARTED,
        task_id="task:trace",
        step_id="collect",
        summary="Collect started.",
        data={"input_summary": {"topic": "runtime"}},
    )

    events = TraceReader(path).read_events()

    assert path.exists()
    assert len(events) == 2
    assert events[0].event_id == "trace-0001"
    assert events[1].event_type == TraceEventType.STEP_STARTED


def test_trace_replay_locates_failed_step_and_reason(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    recorder = TraceRecorder(path)
    recorder.record(
        event_type=TraceEventType.STEP_FAILED,
        task_id="task:trace",
        step_id="writer",
        summary="Draft schema validation failed.",
        data={"error_type": "ValidationError", "message": "sections missing"},
        risk="medium",
        recoverable=True,
    )

    summary = TraceReader(path).replay()

    assert summary.event_count == 1
    assert summary.failed_steps[0]["step_id"] == "writer"
    assert summary.failed_steps[0]["data"]["error_type"] == "ValidationError"
    assert summary.risk_events[0]["risk"] == "medium"


def test_trace_replay_tracks_artifact_created_and_consumed(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    recorder = TraceRecorder(path)
    recorder.record(
        event_type=TraceEventType.ARTIFACT_CREATED,
        task_id="task:trace",
        step_id="research",
        summary="Evidence created.",
        data={"artifact_id": "artifact:evidence", "schema_name": "EvidenceTableV1"},
    )
    recorder.record(
        event_type=TraceEventType.ARTIFACT_CONSUMED,
        task_id="task:trace",
        step_id="writer",
        summary="Evidence consumed.",
        data={"artifact_id": "artifact:evidence", "consumer_step_id": "writer"},
    )

    summary = TraceReader(path).replay()

    assert [item["event_type"] for item in summary.artifact_flow] == ["artifact_created", "artifact_consumed"]
    assert summary.artifact_flow[0]["data"]["artifact_id"] == "artifact:evidence"
    assert summary.artifact_flow[1]["step_id"] == "writer"


def test_trace_redacts_sensitive_fields_and_inline_tokens(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    recorder = TraceRecorder(path)
    recorder.record(
        event_type=TraceEventType.TOOL_CALLED,
        task_id="task:trace",
        step_id="tool",
        summary="Call external tool token=plain-token password=plain-password",
        data={
            "api_key": "plain-api-key",
            "nested": {"secret": "plain-secret", "safe": "visible"},
        },
        risk="high",
    )

    events = TraceReader(path).read_events()

    assert has_sensitive_plaintext(
        events,
        ["plain-token", "plain-password", "plain-api-key", "plain-secret"],
    ) is False
    assert events[0].data["api_key"] == "[REDACTED]"
    assert events[0].data["nested"]["secret"] == "[REDACTED]"
    assert events[0].data["nested"]["safe"] == "visible"


def test_human_required_is_replayable(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    recorder = TraceRecorder(path)
    recorder.record(
        event_type=TraceEventType.HUMAN_REQUIRED,
        task_id="task:trace",
        step_id="deploy",
        summary="Approval required before high risk tool call.",
        data={"reason": "high risk action"},
        risk="high",
        recoverable=True,
    )

    summary = TraceReader(path).replay()

    assert summary.human_required[0]["step_id"] == "deploy"
    assert summary.human_required[0]["risk"] == "high"
