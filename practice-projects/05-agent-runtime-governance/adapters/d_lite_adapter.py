from __future__ import annotations

"""D-lite 自愈项目的 Runtime adapter。

本模块的职责是把已有 D-lite 自愈循环接入统一 Agent Runtime，
而不是重写 D-lite 的修复、安全检查和验证逻辑。

主要类与关系：
- DLiteTaskAdapter：标准 AgentAdapter 实现，负责创建 TaskContract、调用自愈循环、
  并把结果转成 Runtime artifacts 和 EvaluationResult。
- DLiteRuntimeResult：兼容旧调用方的结果容器，保留 state、code artifact、error artifacts
  和 evaluation，方便 CLI 与测试继续读取细节。
- run_d_lite_task：兼容性入口。外部仍按原方式调用，但内部已经走通用
  run_agent_adapter_detailed 生命周期。

典型关系：
DLiteTaskAdapter.describe_contract() -> TaskContract.for_d_lite_task(...)
DLiteTaskAdapter.run(...) -> run_self_heal(...) -> CodeRepairArtifact / ErrorSummaryArtifact
run_d_lite_task(...) -> run_agent_adapter_detailed(...) -> DLiteRuntimeResult
"""

import sys
from pathlib import Path

from runtime.agent_adapter import AdapterRunContext, AgentRunResult, run_agent_adapter_detailed
from runtime.artifacts import CodeRepairArtifact, ErrorSummaryArtifact
from runtime.contracts import TaskContract
from runtime.evaluation import EvaluationResult, RuntimeFinalStatus
from runtime.trace import TraceEventType


PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_DIR.parents[1]
D_LITE_DIR = REPO_ROOT / "practice-projects" / "04-self-healing-ops"
D_LITE_CHALLENGE_DIR = D_LITE_DIR / "challenge_tasks"

if str(D_LITE_DIR) not in sys.path:
    sys.path.insert(0, str(D_LITE_DIR))

from self_heal_loop import run_self_heal  # noqa: E402
from state import ErrorKind, FinalStatus, SelfHealState  # noqa: E402


DEFAULT_D_LITE_TASKS = [
    "task1_broken_import.py",
    "task2_syntax_error.py",
    "task3_infinite_loop.py",
    "task4_bad_fix_regression.py",
    "task5_dangerous_code.py",
    "task6_missing_edge_case.py",
    "task7_key_error.py",
    "task8_empty_average.py",
]


class DLiteRuntimeResult:
    """Container returned by the D-lite runtime adapter."""

    def __init__(
        self,
        *,
        contract: TaskContract,
        state: SelfHealState,
        code_artifact: CodeRepairArtifact,
        error_artifacts: list[ErrorSummaryArtifact],
        evaluation: EvaluationResult,
    ):
        self.contract = contract
        self.state = state
        self.code_artifact = code_artifact
        self.error_artifacts = error_artifacts
        self.evaluation = evaluation


class DLiteTaskAdapter:
    """Adapter that exposes one D-lite self-healing task to Runtime."""

    adapter_id = "d_lite_adapter"

    def __init__(
        self,
        task_name: str,
        *,
        max_attempts: int = 3,
        timeout_seconds: float = 5.0,
    ):
        self.task_path = _resolve_task_path(task_name)
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds
        self.trace_name = f"{self.task_path.stem}.runtime.jsonl"
        self.runtime_result: DLiteRuntimeResult | None = None

    def describe_contract(self) -> TaskContract:
        return TaskContract.for_d_lite_task(
            self.task_path,
            max_attempts=self.max_attempts,
            timeout_seconds=self.timeout_seconds,
        )

    def run(self, context: AdapterRunContext) -> AgentRunResult:
        context.record_tool_call(
            "d_lite.run_self_heal",
            {
                "task_path": str(self.task_path),
                "max_attempts": self.max_attempts,
                "timeout_seconds": self.timeout_seconds,
            },
        )
        state = run_self_heal(
            self.task_path,
            max_attempts=self.max_attempts,
            timeout_seconds=self.timeout_seconds,
        )
        code_artifact = _code_repair_artifact(context.contract, state)
        error_artifacts = _error_artifacts(context.contract, state)
        evaluation = _evaluation_result(context.contract, state)

        if evaluation.status == RuntimeFinalStatus.BLOCKED:
            context.trace.record(
                TraceEventType.GUARDRAIL_BLOCKED,
                {
                    "task_id": context.contract.task_id,
                    "reason": state.final_reason,
                    "safety_blocks": evaluation.metrics.get("safety_blocks", 0),
                },
            )

        self.runtime_result = DLiteRuntimeResult(
            contract=context.contract,
            state=state,
            code_artifact=code_artifact,
            error_artifacts=error_artifacts,
            evaluation=evaluation,
        )
        return AgentRunResult(
            evaluation=evaluation,
            artifacts=[code_artifact, *error_artifacts],
        )


def run_d_lite_task(
    task_name: str,
    *,
    max_attempts: int = 3,
    timeout_seconds: float = 5.0,
    trace_dir: Path,
) -> DLiteRuntimeResult:
    """Run one D-lite task through the runtime wrapper."""
    adapter = DLiteTaskAdapter(
        task_name,
        max_attempts=max_attempts,
        timeout_seconds=timeout_seconds,
    )
    run_agent_adapter_detailed(adapter, trace_dir=trace_dir)
    if adapter.runtime_result is None:
        raise RuntimeError("D-lite adapter did not produce a runtime result.")
    return adapter.runtime_result


def _resolve_task_path(task_name: str) -> Path:
    task_path = Path(task_name)
    if not task_path.is_absolute():
        task_path = D_LITE_CHALLENGE_DIR / task_name
    if not task_path.exists():
        raise FileNotFoundError(f"D-lite challenge task not found: {task_path}")
    return task_path


def _code_repair_artifact(contract: TaskContract, state: SelfHealState) -> CodeRepairArtifact:
    return CodeRepairArtifact(
        artifact_id=f"{contract.task_id}:code_repair",
        task_id=contract.task_id,
        source="d_lite_adapter",
        task_name=state.task_name,
        final_status=state.final_status.value,
        final_reason=state.final_reason,
        attempts=len(state.attempts),
        changed=any(attempt.changed for attempt in state.attempts),
        repair_summaries=[attempt.repair_summary for attempt in state.attempts],
        workspace_path=str(state.workspace_path),
        target_path=str(state.target_path),
    )


def _error_artifacts(contract: TaskContract, state: SelfHealState) -> list[ErrorSummaryArtifact]:
    artifacts: list[ErrorSummaryArtifact] = []
    for attempt in state.attempts:
        artifacts.append(
            ErrorSummaryArtifact(
                artifact_id=f"{contract.task_id}:error:{attempt.attempt}",
                task_id=contract.task_id,
                source="d_lite_adapter",
                error_kind=attempt.error.kind.value,
                message=attempt.error.message,
                evidence=attempt.error.evidence,
                line_number=attempt.error.line_number,
                attempt=attempt.attempt,
            )
        )
    if state.final_status == FinalStatus.BLOCKED and not artifacts:
        artifacts.append(
            ErrorSummaryArtifact(
                artifact_id=f"{contract.task_id}:error:blocked",
                task_id=contract.task_id,
                source="d_lite_adapter",
                error_kind=ErrorKind.SECURITY_BLOCKED.value,
                message=state.final_reason,
                evidence=state.final_reason,
            )
        )
    return artifacts


def _evaluation_result(contract: TaskContract, state: SelfHealState) -> EvaluationResult:
    status = _map_status(state.final_status)
    safety_blocks = sum(
        1
        for attempt in state.attempts
        if attempt.error.kind == ErrorKind.SECURITY_BLOCKED
    )
    if state.final_status == FinalStatus.BLOCKED:
        safety_blocks += 1
    timeouts = sum(1 for attempt in state.attempts if attempt.error.kind == ErrorKind.TIMEOUT)
    changed_attempts = sum(1 for attempt in state.attempts if attempt.changed)
    score = 1.0 if status in {RuntimeFinalStatus.PASSED, RuntimeFinalStatus.BLOCKED} else 0.0
    return EvaluationResult(
        task_id=contract.task_id,
        task_name=state.task_name,
        status=status,
        score=score,
        attempts=len(state.attempts),
        reason=state.final_reason,
        metrics={
            "changed_attempts": changed_attempts,
            "safety_blocks": safety_blocks,
            "timeouts": timeouts,
            "source_path": str(state.source_path),
            "target_path": str(state.target_path),
        },
    )


def _map_status(status: FinalStatus) -> RuntimeFinalStatus:
    if status == FinalStatus.PASSED:
        return RuntimeFinalStatus.PASSED
    if status == FinalStatus.BLOCKED:
        return RuntimeFinalStatus.BLOCKED
    return RuntimeFinalStatus.FAILED
