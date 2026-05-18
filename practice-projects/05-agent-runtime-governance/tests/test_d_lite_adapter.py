from __future__ import annotations

import json

from adapters.d_lite_adapter import DLiteTaskAdapter, run_d_lite_task
from runtime.agent_adapter import run_agent_adapter
from runtime.evaluation import RuntimeFinalStatus


def test_d_lite_adapter_uses_common_agent_lifecycle(tmp_path) -> None:
    adapter = DLiteTaskAdapter(
        "task1_broken_import.py",
        max_attempts=3,
        timeout_seconds=5.0,
    )

    evaluation = run_agent_adapter(adapter, trace_dir=tmp_path)

    assert evaluation.status == RuntimeFinalStatus.PASSED
    assert adapter.runtime_result is not None
    assert adapter.runtime_result.code_artifact.final_status == "passed"

    events = _read_trace_events(tmp_path / "task1_broken_import.runtime.jsonl")
    assert [event["event"] for event in events] == [
        "task_started",
        "tool_called",
        "artifact_created",
        "artifact_created",
        "evaluation_run",
        "task_finished",
    ]


def test_d_lite_adapter_runs_one_task(tmp_path) -> None:
    result = run_d_lite_task(
        "task1_broken_import.py",
        max_attempts=3,
        timeout_seconds=5.0,
        trace_dir=tmp_path,
    )

    assert result.evaluation.status == RuntimeFinalStatus.PASSED
    assert result.code_artifact.final_status == "passed"
    assert result.code_artifact.attempts == 1
    assert (tmp_path / "task1_broken_import.runtime.jsonl").exists()


def test_d_lite_adapter_preserves_safety_block(tmp_path) -> None:
    result = run_d_lite_task(
        "task5_dangerous_code.py",
        max_attempts=3,
        timeout_seconds=5.0,
        trace_dir=tmp_path,
    )

    assert result.evaluation.status == RuntimeFinalStatus.BLOCKED
    assert result.evaluation.metrics["safety_blocks"] == 1
    assert result.error_artifacts[0].error_kind == "security_blocked"


def _read_trace_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
