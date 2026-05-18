from __future__ import annotations

"""跨项目观测 CLI。

这个命令默认评估 A/B/C 已经产出的 artifact，也可以选择实际执行 D-lite
challenge tasks。它刻意使用 observability 命名，因为默认 A/B/C 路径并不会
重新运行原始 Agent workflow。
"""

import argparse
import json
from pathlib import Path

from adapters.content_team_adapter import run_content_team_report
from adapters.d_lite_adapter import DEFAULT_D_LITE_TASKS, run_d_lite_task
from adapters.rag_adapter import run_rag_readiness
from adapters.research_adapter import run_research_report
from runtime.evaluation import EvaluationResult, EvaluationSummary


PROJECT_DIR = Path(__file__).resolve().parent
TRACE_DIR = PROJECT_DIR / "traces"
REPORT_DIR = PROJECT_DIR / "reports"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Observe existing project artifacts and optionally run D-lite."
    )
    parser.add_argument(
        "--projects",
        nargs="*",
        choices=["rag", "content", "research", "d-lite"],
        default=["rag", "content", "research"],
        help="Projects to observe. A/B/C observe existing artifacts; D-lite runs challenge tasks.",
    )
    parser.add_argument(
        "--run-d-lite",
        action="store_true",
        help="Run all D-lite challenge tasks in addition to observing A/B/C artifacts.",
    )
    parser.add_argument(
        "--include-d-lite",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    projects = set(args.projects)
    if args.run_d_lite or args.include_d_lite:
        projects.add("d-lite")

    results: list[EvaluationResult] = []
    if "rag" in projects:
        results.append(run_rag_readiness(trace_dir=TRACE_DIR))
    if "content" in projects:
        results.append(run_content_team_report(trace_dir=TRACE_DIR))
    if "research" in projects:
        results.append(run_research_report(trace_dir=TRACE_DIR))
    if "d-lite" in projects:
        results.extend(
            run_d_lite_task(
                task_name,
                max_attempts=args.max_attempts,
                timeout_seconds=args.timeout,
                trace_dir=TRACE_DIR,
            ).evaluation
            for task_name in DEFAULT_D_LITE_TASKS
        )

    summary = EvaluationSummary.from_results(results)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "cross_project_observability_summary.json"
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
    print(f"Average attempts: {summary.average_attempts:.2f}")
    print(f"Trace directory: {TRACE_DIR}")
    print(f"Report: {report_path}")


def _markdown_table(summary: EvaluationSummary) -> str:
    headers = ["task_id", "status", "score", "reason"]
    rows = [
        [
            result.task_id,
            result.status.value,
            f"{result.score:.3f}",
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
