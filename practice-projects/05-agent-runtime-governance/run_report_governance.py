from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scenarios.report_governance.scenario import run_report_governance


PROJECT_DIR = Path(__file__).resolve().parent
TRACE_DIR = PROJECT_DIR / "traces"
REPORT_DIR = PROJECT_DIR / "reports"
DEFAULT_DOCUMENT = PROJECT_DIR / "samples" / "agent_runtime_note.md"


def main() -> None:
    load_dotenv(REPO_ROOT / ".env", override=True)

    parser = argparse.ArgumentParser(description="Run a runtime-native report governance scenario.")
    parser.add_argument("document", nargs="?", default=str(DEFAULT_DOCUMENT), help="Markdown document path.")
    parser.add_argument("--min-score", type=float, default=0.7)
    parser.add_argument(
        "--request-patch",
        action="store_true",
        help="Try to create a proposed improvement patch artifact; this triggers high-risk tool governance.",
    )
    parser.add_argument(
        "--approve-high-risk",
        action="store_true",
        help="Approve the high-risk patch writing tool for this run.",
    )
    parser.add_argument(
        "--llm-review",
        action="store_true",
        help="Enable an auxiliary LLM reviewer. Final pass/fail still uses deterministic rules.",
    )
    args = parser.parse_args()

    result = run_report_governance(
        Path(args.document),
        trace_dir=TRACE_DIR,
        thresholds={"min_score": args.min_score},
        request_patch=args.request_patch,
        approve_high_risk=args.approve_high_risk,
        patch_output_dir=REPORT_DIR,
        llm_review=args.llm_review,
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "report_governance_summary.json"
    report_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"task_id: {result.task_id}")
    print(f"status: {result.status.value}")
    print(f"score: {result.score:.3f}")
    print(f"reason: {result.reason}")
    print(f"issues: {result.metrics['issue_count']} high={result.metrics['high_issue_count']}")
    if result.metrics.get("human_review_required"):
        print(f"human_review: required request_id={result.metrics.get('review_request_id')}")
    if result.metrics.get("patch_path"):
        print(f"patch: {result.metrics['patch_path']}")
    if result.metrics.get("llm_review"):
        review = result.metrics["llm_review"]
        print(
            "llm_review: "
            f"{review['provider']}/{review['model']} verdict={review['verdict']} "
            f"confidence={review['confidence']:.2f} concerns={review['concern_count']}"
        )
    print(f"Trace: {TRACE_DIR / (Path(args.document).stem + '.report_governance.runtime.jsonl')}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
