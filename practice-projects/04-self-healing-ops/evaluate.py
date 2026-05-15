from __future__ import annotations

import argparse
from pathlib import Path

from self_heal_loop import CHALLENGE_DIR, run_self_heal
from state import ErrorKind


DEFAULT_TASKS = [
    "task1_broken_import.py",
    "task2_syntax_error.py",
    "task3_infinite_loop.py",
    "task4_bad_fix_regression.py",
    "task5_dangerous_code.py",
]


def main() -> None:
    """批量运行 challenge tasks，并输出最小评估摘要。"""
    parser = argparse.ArgumentParser(description="Evaluate D-lite self-healing challenge tasks.")
    parser.add_argument("tasks", nargs="*", help="Optional challenge task filenames.")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    task_names = args.tasks or DEFAULT_TASKS
    states = [
        run_self_heal(CHALLENGE_DIR / task_name, max_attempts=args.max_attempts, timeout_seconds=args.timeout)
        for task_name in task_names
    ]

    passed = sum(1 for state in states if state.final_status == "passed")
    # 安全拦截有两种位置：初次验证直接拦截，或修复轮次中被分类为 security_blocked。
    safety_blocks = sum(
        1
        for state in states
        for attempt in state.attempts
        if attempt.error.kind == ErrorKind.SECURITY_BLOCKED
    )
    initial_safety_blocks = sum(
        1 for state in states if state.final_status == "failed" and "Safety check failed" in state.final_reason
    )
    timeouts = sum(
        1
        for state in states
        for attempt in state.attempts
        if attempt.error.kind == ErrorKind.TIMEOUT
    )
    attempts = [len(state.attempts) for state in states if state.attempts]
    avg_attempts = sum(attempts) / len(attempts) if attempts else 0.0

    print(_markdown_table(states))
    print()
    print(f"Tasks: {len(states)}")
    print(f"Passed: {passed}")
    print(f"Success rate: {passed / len(states):.0%}")
    print(f"Average attempts for repaired tasks: {avg_attempts:.2f}")
    print(f"Timeout classifications: {timeouts}")
    print(f"Safety blocks: {safety_blocks + initial_safety_blocks}")
    print(f"Trace directory: {Path(__file__).resolve().parent / 'traces'}")


def _markdown_table(states) -> str:
    """生成便于复制进 README/报告的 Markdown 表格。"""
    headers = ["task", "status", "attempts", "reason"]
    rows = [
        [
            state.task_name,
            state.final_status,
            str(len(state.attempts)),
            state.final_reason,
        ]
        for state in states
    ]
    widths = [
        max(len(row[index]) for row in [headers, *rows])
        for index in range(len(headers))
    ]
    lines = [
        "| " + " | ".join(headers[index].ljust(widths[index]) for index in range(len(headers))) + " |",
        "| " + " | ".join("-" * widths[index] for index in range(len(headers))) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[index].ljust(widths[index]) for index in range(len(headers))) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
