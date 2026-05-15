from __future__ import annotations

import re

from state import ErrorKind, ErrorSummary, RunResult, SafetyIssue


def classify_result(run_result: RunResult, safety_issues: list[SafetyIssue] | None = None) -> ErrorSummary:
    """把底层执行信号压缩为 Agent 可处理的错误摘要。

    这是观察和修复之间的边界：后续修复器不需要理解完整 subprocess 结果。
    """
    safety_issues = safety_issues or []
    if safety_issues:
        issue = safety_issues[0]
        return ErrorSummary(
            kind=ErrorKind.SECURITY_BLOCKED,
            message=issue.message,
            evidence=f"line {issue.line_number}: {issue.kind}",
            line_number=issue.line_number,
        )
    if run_result.timed_out:
        return ErrorSummary(
            kind=ErrorKind.TIMEOUT,
            message="Execution timed out.",
            evidence=f"Command exceeded timeout after {run_result.duration_seconds:.2f}s.",
        )
    if run_result.exit_code == 0:
        return ErrorSummary(kind=ErrorKind.NONE, message="Command succeeded.")

    stderr = run_result.stderr
    line_number = _extract_line_number(stderr)
    if "ModuleNotFoundError" in stderr or "ImportError" in stderr:
        return ErrorSummary(
            kind=ErrorKind.IMPORT_ERROR,
            message=_last_error_line(stderr),
            evidence=_traceback_tail(stderr),
            line_number=line_number,
        )
    if "SyntaxError" in stderr:
        return ErrorSummary(
            kind=ErrorKind.SYNTAX_ERROR,
            message=_last_error_line(stderr),
            evidence=_traceback_tail(stderr),
            line_number=line_number,
        )
    if "AssertionError" in stderr:
        return ErrorSummary(
            kind=ErrorKind.ASSERTION_ERROR,
            message="Assertion failed.",
            evidence=_traceback_tail(stderr),
            line_number=line_number,
        )
    if "ZeroDivisionError" in stderr:
        return ErrorSummary(
            kind=ErrorKind.RUNTIME_ERROR,
            message=_last_error_line(stderr),
            evidence=_traceback_tail(stderr),
            line_number=line_number,
        )
    return ErrorSummary(
        kind=ErrorKind.UNKNOWN,
        message=_last_error_line(stderr) or "Unknown execution failure.",
        evidence=_traceback_tail(stderr),
        line_number=line_number,
    )


def _extract_line_number(stderr: str) -> int | None:
    """从 traceback 中提取最后一个文件行号，通常最接近出错位置。"""
    matches = re.findall(r'File ".*?", line (\d+)', stderr)
    if not matches:
        return None
    return int(matches[-1])


def _last_error_line(stderr: str) -> str:
    """提取 traceback 最后一行，作为面向修复器的短错误消息。"""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _traceback_tail(stderr: str, max_lines: int = 8) -> str:
    """保留 traceback 尾部证据，避免 trace 被长错误刷屏。"""
    lines = [line.rstrip() for line in stderr.splitlines() if line.strip()]
    return "\n".join(lines[-max_lines:])
