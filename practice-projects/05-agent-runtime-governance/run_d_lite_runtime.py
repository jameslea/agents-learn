from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapters.d_lite_adapter import DEFAULT_D_LITE_TASKS, run_d_lite_task
from runtime.evaluation import EvaluationSummary


PROJECT_DIR = Path(__file__).resolve().parent
TRACE_DIR = PROJECT_DIR / "traces"
REPORT_DIR = PROJECT_DIR / "reports"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run D-lite through Agent Runtime & Governance Lab.")
    parser.add_argument("tasks", nargs="*", help="Optional D-lite challenge task filenames.")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    task_names = args.tasks or DEFAULT_D_LITE_TASKS
    results = [
        run_d_lite_task(
            task_name,
            max_attempts=args.max_attempts,
            timeout_seconds=args.timeout,
            trace_dir=TRACE_DIR,
        )
        for task_name in task_names
    ]
    summary = EvaluationSummary.from_results([result.evaluation for result in results])
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "d_lite_summary.json"
    report_path.write_text(
        json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(_markdown_table(summary))
    print()
    print(f"Tasks: {summary.total}")
    print(f"Passed: {summary.passed}")
    print(f"Blocked: {summary.blocked}")
    print(f"Failed: {summary.failed}")
    print(f"Effective success rate: {summary.effective_success_rate:.0%}")
    print(f"Repair success rate: {summary.repair_success_rate:.0%}")
    print(f"Average attempts: {summary.average_attempts:.2f}")
    print(f"Trace directory: {TRACE_DIR}")
    print(f"Report: {report_path}")


def _markdown_table(summary: EvaluationSummary) -> str:
    headers = ["task", "status", "attempts", "score", "reason"]
    rows = [
        [
            result.task_name,
            result.status.value,
            str(result.attempts),
            f"{result.score:.1f}",
            result.reason,
        ]
        for result in summary.results
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

