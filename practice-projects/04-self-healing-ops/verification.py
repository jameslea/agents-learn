from __future__ import annotations

from pathlib import Path

from ast_checker import check_file
from error_classifier import classify_result
from executor import run_python_file
from state import VerificationResult


def verify_python_file(path: Path, timeout_seconds: float = 5.0) -> VerificationResult:
    """验证一个 Python 文件是否安全且能成功执行。

    验证顺序很重要：先做静态安全检查，再运行代码。危险代码不会进入执行阶段。
    """
    safety_issues = check_file(path)
    if safety_issues:
        issue = safety_issues[0]
        return VerificationResult(
            passed=False,
            reason=f"Safety check failed: {issue.message}",
            safety_issues=safety_issues,
        )

    # 退出码为 0 且未超时，才认为任务通过。stdout 文本本身不作为成功依据。
    run_result = run_python_file(path, timeout_seconds=timeout_seconds)
    error = classify_result(run_result)
    if run_result.exit_code == 0 and not run_result.timed_out:
        return VerificationResult(
            passed=True,
            reason="Command exited with 0 and safety checks passed.",
            run_result=run_result,
        )
    return VerificationResult(
        passed=False,
        reason=f"{error.kind.value}: {error.message}",
        run_result=run_result,
    )
