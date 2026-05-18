from __future__ import annotations

from pathlib import Path

from runtime.artifacts import CodeRepairArtifact
from runtime.contracts import TaskContract, TaskType
from runtime.evaluation import EvaluationResult, EvaluationSummary, RuntimeFinalStatus


def test_d_lite_contract_has_runtime_boundaries() -> None:
    contract = TaskContract.for_d_lite_task(Path("task1_broken_import.py"))

    assert contract.task_type == TaskType.SELF_HEAL
    assert contract.budget.max_attempts == 3
    assert "CodeRepairArtifact" in contract.expected_outputs
    assert "d_lite.verify_python_file" in contract.allowed_tools


def test_code_repair_artifact_is_structured() -> None:
    artifact = CodeRepairArtifact(
        artifact_id="a1",
        task_id="t1",
        task_name="task.py",
        final_status="passed",
        final_reason="verified",
        attempts=1,
        changed=True,
        repair_summaries=["fixed import"],
    )

    data = artifact.model_dump(mode="json")
    assert data["artifact_type"] == "code_repair"
    assert data["repair_summaries"] == ["fixed import"]


def test_evaluation_summary_counts_blocked_as_effective_success() -> None:
    results = [
        EvaluationResult(
            task_id="t1",
            task_name="task1.py",
            status=RuntimeFinalStatus.PASSED,
            score=1.0,
            attempts=1,
            reason="verified",
        ),
        EvaluationResult(
            task_id="t2",
            task_name="task2.py",
            status=RuntimeFinalStatus.BLOCKED,
            score=1.0,
            attempts=0,
            reason="blocked",
        ),
    ]

    summary = EvaluationSummary.from_results(results)

    assert summary.total == 2
    assert summary.effective_success_rate == 1.0
    assert summary.repair_success_rate == 0.5

