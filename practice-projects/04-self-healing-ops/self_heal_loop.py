from __future__ import annotations

import argparse
from pathlib import Path

from agent import RepairAgent
from error_classifier import classify_result
from executor import prepare_workspace
from state import RepairAttempt, SelfHealState, VerificationResult
from trace_recorder import TraceRecorder
from verification import verify_python_file


PROJECT_DIR = Path(__file__).resolve().parent
CHALLENGE_DIR = PROJECT_DIR / "challenge_tasks"
WORKSPACE_ROOT = PROJECT_DIR / "workspaces"
TRACE_DIR = PROJECT_DIR / "traces"


def run_self_heal(
    source_path: Path,
    max_attempts: int = 3,
    timeout_seconds: float = 5.0,
    trace_dir: Path = TRACE_DIR,
) -> SelfHealState:
    """运行一个最小自愈闭环。

    这里刻意保持线性流程：验证失败后才修复，修复后必须再次验证。
    这样便于观察 Agent 是否真的通过客观信号修好代码。
    """
    workspace_path, target_path = prepare_workspace(source_path, WORKSPACE_ROOT)
    state = SelfHealState(
        task_name=source_path.name,
        source_path=source_path,
        workspace_path=workspace_path,
        target_path=target_path,
        max_attempts=max_attempts,
    )
    trace = TraceRecorder(trace_dir / f"{source_path.stem}.jsonl")
    agent = RepairAgent()
    trace.record("task_started", state)

    # 第 0 轮只验证，不修复。这样 trace 能清楚保留原始失败信号。
    initial = verify_python_file(target_path, timeout_seconds=timeout_seconds)
    trace.record("verification", {"attempt": 0, "result": initial.model_dump(mode="json")})
    if initial.passed:
        state.final_status = "passed"
        state.final_reason = "Initial verification passed."
        trace.record("task_finished", state)
        return state

    current_verification: VerificationResult = initial
    for attempt_number in range(1, max_attempts + 1):
        # 把执行结果压缩为 ErrorSummary，避免 RepairAgent 直接依赖冗长 traceback。
        error = _error_from_verification(current_verification)
        changed, repair_summary = agent.repair(target_path, error)
        trace.record(
            "repair",
            {
                "attempt": attempt_number,
                "error": error.model_dump(mode="json"),
                "changed": changed,
                "repair_summary": repair_summary,
            },
        )

        # 修复是否有效只看再次执行结果，不能相信修复器自己的描述。
        current_verification = verify_python_file(target_path, timeout_seconds=timeout_seconds)
        attempt = RepairAttempt(
            attempt=attempt_number,
            error=error,
            repair_summary=repair_summary,
            changed=changed,
            verification=current_verification,
        )
        state.attempts.append(attempt)
        trace.record("verification", {"attempt": attempt_number, "result": current_verification.model_dump(mode="json")})
        if current_verification.passed:
            state.final_status = "passed"
            state.final_reason = f"Verification passed after attempt {attempt_number}."
            trace.record("task_finished", state)
            return state
        if not changed:
            state.final_status = "failed"
            state.final_reason = f"No repair rule could handle attempt {attempt_number}: {error.message}"
            trace.record("task_finished", state)
            return state

    final_error = _error_from_verification(current_verification)
    state.final_status = "failed"
    state.final_reason = f"Max attempts reached. Last error: {final_error.kind.value}: {final_error.message}"
    trace.record("task_finished", state)
    return state


def _error_from_verification(verification: VerificationResult):
    """从验证结果提取修复器可消费的错误摘要。"""
    if verification.safety_issues:
        return classify_result(verification.run_result or _empty_run_result(), verification.safety_issues)
    if verification.run_result:
        return classify_result(verification.run_result)
    return classify_result(_empty_run_result(), verification.safety_issues)


def _empty_run_result():
    """给只有安全问题、没有执行结果的场景提供分类兜底。"""
    from state import RunResult

    return RunResult(command=[], exit_code=1, stderr="No run result available.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the D-lite self-healing loop for one challenge task.")
    parser.add_argument("task", help="Challenge task filename, e.g. task1_broken_import.py")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    source_path = Path(args.task)
    if not source_path.is_absolute():
        source_path = CHALLENGE_DIR / source_path
    state = run_self_heal(source_path, max_attempts=args.max_attempts, timeout_seconds=args.timeout)
    print(f"{state.task_name}: {state.final_status} - {state.final_reason}")
    for attempt in state.attempts:
        print(
            f"  attempt {attempt.attempt}: {attempt.error.kind.value}; "
            f"changed={attempt.changed}; passed={attempt.verification.passed}; {attempt.repair_summary}"
        )


if __name__ == "__main__":
    main()
