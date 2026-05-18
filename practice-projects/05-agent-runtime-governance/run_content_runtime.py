from __future__ import annotations

"""Run B-runtime-lite as a deliverable-oriented Runtime execution scenario."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from adapters.content_runtime_adapter import DEFAULT_TOPIC, run_content_runtime_lite


PROJECT_DIR = Path(__file__).resolve().parent
TRACE_DIR = PROJECT_DIR / "traces"
REPORT_DIR = PROJECT_DIR / "reports"


def _new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the minimal content report delivery adapter.")
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument("--guardrail-score", type=int, default=70)
    parser.add_argument("--resume", action="store_true", help="Resume from the latest RuntimeState checkpoint.")
    parser.add_argument(
        "--run-id",
        nargs="?",
        const="auto",
        help=(
            "Isolate trace/state/artifacts under one run id. "
            "Use '--run-id' for an auto timestamp or '--run-id NAME' for a named run."
        ),
    )
    parser.add_argument("--passing-score", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    guardrail_score = args.passing_score if args.passing_score is not None else args.guardrail_score
    run_id = _new_run_id() if args.run_id == "auto" else args.run_id

    result = run_content_runtime_lite(
        topic=args.topic,
        trace_dir=TRACE_DIR,
        output_dir=REPORT_DIR,
        guardrail_score=guardrail_score,
        resume=args.resume,
        run_id=run_id,
    )
    summary_dir = REPORT_DIR / run_id if run_id else REPORT_DIR
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "content_runtime_lite_summary.json"
    summary_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"task_id: {result.task_id}")
    print(f"status: {result.status.value}")
    print(f"delivery_score: {result.score:.3f}")
    print(f"reason: {result.reason}")
    print(f"report: {result.metrics['report_path']}")
    guardrail = result.metrics["quality_guardrail"]
    print(
        "quality_guardrail: "
        f"score={guardrail['score']} threshold={guardrail['threshold']} passed={guardrail['passed']}"
    )
    print(f"revision_applied: {result.metrics['revision_applied']}")
    print(f"resume: {args.resume}")
    print(f"run_id: {run_id or '(default)'}")
    trace_path = TRACE_DIR / "content_runtime_lite.runtime.jsonl"
    if run_id:
        trace_path = TRACE_DIR / run_id / "content_runtime_lite.runtime.jsonl"
    print(f"Trace: {trace_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
