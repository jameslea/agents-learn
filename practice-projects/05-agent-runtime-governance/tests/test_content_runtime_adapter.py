from __future__ import annotations

import json

import pytest

from adapters.content_runtime_adapter import run_content_runtime_lite
from adapters.content_runtime_adapter import ContentRuntimeLiteAdapter
from runtime.agent_adapter import run_agent_adapter_detailed
from runtime.evaluation import RuntimeFinalStatus
from runtime.run_lock import RuntimeRunAlreadyActive
from runtime.state import RuntimeCheckpointStore


def test_content_runtime_lite_executes_real_runtime_chain(tmp_path) -> None:
    result = run_content_runtime_lite(
        topic="Agent Runtime 测试主题",
        trace_dir=tmp_path,
        output_dir=tmp_path,
        guardrail_score=70,
    )

    assert result.task_id == "content_runtime:lite"
    assert result.status == RuntimeFinalStatus.PASSED
    assert result.score == 1.0
    assert result.metrics["report_path"].endswith("content_runtime_lite_report.md")
    assert result.metrics["improvement_plan"]["steps"]
    assert result.metrics["delivered"] is True
    assert result.metrics["revision_applied"] is True
    assert "final_quality" in result.metrics
    assert "quality_guardrail" in result.metrics

    events = _read_trace_events(tmp_path / "content_runtime_lite.runtime.jsonl")
    event_names = [event["event"] for event in events]
    assert event_names.count("step_started") == 7
    assert event_names.count("step_finished") == 7
    assert event_names.count("tool_decision") == 7
    assert event_names.count("tool_called") == 7
    finished_steps = [
        event["payload"]["step_id"]
        for event in events
        if event["event"] == "step_finished"
    ]
    assert finished_steps == [
        "outline",
        "draft",
        "review",
        "plan",
        "revise",
        "deliver",
        "check_delivery",
    ]
    assert any(
        event["event"] == "artifact_created"
        and event["payload"]["artifact_type"] == "content_report"
        for event in events
    )
    assert event_names[-1] == "task_finished"


def test_content_runtime_lite_exposes_runtime_state(tmp_path) -> None:
    adapter = ContentRuntimeLiteAdapter(
        topic="Agent Runtime 状态测试",
        output_dir=tmp_path,
        guardrail_score=70,
    )

    execution = run_agent_adapter_detailed(adapter, trace_dir=tmp_path)

    assert execution.state is not None
    assert execution.state.status == "passed"
    assert execution.checkpoint_path == tmp_path.parent / "state" / "content_runtime_lite.runtime.state.json"
    assert execution.manifest_path == tmp_path.parent / "manifests" / "content_runtime_lite.runtime.manifest.json"
    assert [step.step_id for step in execution.state.steps] == [
        "outline",
        "draft",
        "review",
        "plan",
        "revise",
        "deliver",
        "check_delivery",
    ]
    assert execution.state.values["draft_ref"]["path"].endswith("draft.md")
    assert execution.state.values["final_ref"]["path"].endswith("final_report_draft.md")
    assert (tmp_path.parent / "artifacts" / execution.state.values["draft_ref"]["path"]).exists()
    assert (tmp_path.parent / "artifacts" / execution.state.values["final_ref"]["path"]).exists()
    assert execution.state.values["final_report_path"].endswith("content_runtime_lite_report.md")
    assert execution.state.artifact_ids == [
        "content_runtime:lite:content_report",
        "content_runtime:lite:improvement_plan",
    ]

    checkpoint = RuntimeCheckpointStore(execution.checkpoint_path).load()
    assert checkpoint.status == "passed"
    assert checkpoint.values["draft_ref"]["media_type"] == "text/markdown"
    assert checkpoint.values["delivery_ref"]["media_type"] == "application/json"
    assert checkpoint.values["final_report_path"].endswith("content_runtime_lite_report.md")
    assert [step.step_id for step in checkpoint.steps] == [
        "outline",
        "draft",
        "review",
        "plan",
        "revise",
        "deliver",
        "check_delivery",
    ]
    manifest = json.loads(execution.manifest_path.read_text(encoding="utf-8"))
    assert manifest["adapter_id"] == "content_runtime_lite"
    assert manifest["task_id"] == "content_runtime:lite"
    assert manifest["status"] == "passed"
    assert manifest["trace_path"] == str(tmp_path / "content_runtime_lite.runtime.jsonl")
    assert manifest["checkpoint_path"] == str(execution.checkpoint_path)
    assert manifest["metadata"]["artifact_count"] == 2


def test_content_runtime_lite_can_isolate_one_run_id(tmp_path) -> None:
    adapter = ContentRuntimeLiteAdapter(
        topic="Agent Runtime run_id 测试",
        output_dir=tmp_path,
        guardrail_score=70,
    )

    execution = run_agent_adapter_detailed(adapter, trace_dir=tmp_path, run_id="run-a")

    assert execution.run_id == "run-a"
    assert execution.trace_path == tmp_path / "run-a" / "content_runtime_lite.runtime.jsonl"
    assert execution.checkpoint_path == (
        tmp_path.parent / "state" / "run-a" / "content_runtime_lite.runtime.state.json"
    )
    assert execution.artifact_root == tmp_path.parent / "artifacts" / "run-a"
    assert execution.manifest_path == (
        tmp_path.parent / "manifests" / "run-a" / "content_runtime_lite.runtime.manifest.json"
    )
    assert execution.trace_path.exists()
    assert execution.checkpoint_path.exists()
    assert execution.state.values["final_report_path"].endswith(
        "run-a/content_runtime_lite_report.md"
    )
    assert (
        execution.artifact_root
        / execution.state.values["draft_ref"]["path"]
    ).exists()
    manifest = json.loads(execution.manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "run-a"
    assert manifest["status"] == "passed"


def test_content_runtime_lite_can_resume_from_checkpoint(tmp_path) -> None:
    first = run_content_runtime_lite(
        topic="Agent Runtime resume 测试",
        trace_dir=tmp_path,
        output_dir=tmp_path,
        guardrail_score=70,
    )
    second = run_content_runtime_lite(
        topic="Agent Runtime resume 测试",
        trace_dir=tmp_path,
        output_dir=tmp_path,
        guardrail_score=70,
        resume=True,
    )

    assert first.status == RuntimeFinalStatus.PASSED
    assert second.status == RuntimeFinalStatus.PASSED

    events = _read_trace_events(tmp_path / "content_runtime_lite.runtime.jsonl")
    event_names = [event["event"] for event in events]
    assert event_names.count("step_skipped") == 7
    assert event_names.count("tool_called") == 7
    skipped_steps = [
        event["payload"]["step_id"]
        for event in events
        if event["event"] == "step_skipped"
    ]
    assert skipped_steps == [
        "outline",
        "draft",
        "review",
        "plan",
        "revise",
        "deliver",
        "check_delivery",
    ]


def test_content_runtime_lite_respects_runtime_lock(tmp_path) -> None:
    lock_path = tmp_path.parent / "state" / "content_runtime_lite.runtime.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("locked", encoding="utf-8")

    with pytest.raises(RuntimeRunAlreadyActive):
        run_content_runtime_lite(
            topic="Agent Runtime lock 测试",
            trace_dir=tmp_path,
            output_dir=tmp_path,
            guardrail_score=70,
        )


def test_content_runtime_lite_respects_runtime_lock_for_run_id(tmp_path) -> None:
    lock_path = tmp_path.parent / "state" / "run-a" / "content_runtime_lite.runtime.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("locked", encoding="utf-8")

    with pytest.raises(RuntimeRunAlreadyActive):
        run_content_runtime_lite(
            topic="Agent Runtime run_id lock 测试",
            trace_dir=tmp_path,
            output_dir=tmp_path,
            guardrail_score=70,
            run_id="run-a",
        )


def test_content_runtime_lite_rejects_invalid_run_id(tmp_path) -> None:
    adapter = ContentRuntimeLiteAdapter(
        topic="Agent Runtime invalid run_id 测试",
        output_dir=tmp_path,
        guardrail_score=70,
    )

    with pytest.raises(ValueError, match="Invalid runtime run_id"):
        run_agent_adapter_detailed(adapter, trace_dir=tmp_path, run_id="../bad")


def _read_trace_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
