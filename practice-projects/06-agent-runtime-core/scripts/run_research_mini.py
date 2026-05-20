from __future__ import annotations

"""运行阶段 6 research_mini 最小 Runtime 串联 demo。"""

import json
import sys
import tempfile
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from scenarios.research_mini.scenario import run_research_mini


def render_text_report(payload: dict[str, Any]) -> str:
    lines = [
        "Research Mini Runtime Demo",
        "=" * 26,
        "",
        f"- status: {payload['status']}",
        f"- resumed: {payload['resumed']}",
        f"- checkpoint: {payload['checkpoint_path']}",
        f"- artifacts snapshot: {payload['artifact_snapshot_path']}",
        f"- trace: {payload['trace_path']}",
        f"- artifacts: {payload['artifacts']}",
        f"- skipped_steps: {payload['skipped_steps']}",
        f"- final_review_passed: {payload['final_review_passed']}",
    ]
    if payload.get("blocked_reason"):
        blocked = payload["blocked_reason"]
        lines.extend(
            [
                "",
                "[Blocked]",
                f"- step_id: {blocked['step_id']}",
                f"- reason: {blocked['reason']}",
                f"- suggested_action: {blocked['suggested_action']}",
            ]
        )

    summary = payload["trace_summary"]
    lines.extend(
        [
            "",
            "[Trace summary]",
            f"- event_count: {summary['event_count']}",
            f"- event_type_counts: {summary['event_type_counts']}",
            f"- failed_steps: {summary['failed_steps']}",
            f"- human_required: {summary['human_required']}",
            "",
            "[结论]",
            "- 一个具体场景已经能复用 contract、state、context、memory、artifact、checkpoint 和 trace。",
            "- resume 依赖 checkpoint 和 artifact snapshot，避免下游 step 找不到上游产物。",
            "- blocked 通过工具策略触发，并给出人工处理建议。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = ArgumentParser(description="Run the research_mini minimal runtime demo.")
    parser.add_argument("--topic", default="Agent Runtime Core")
    parser.add_argument("--workdir", default=str(Path(tempfile.gettempdir()) / "agent-runtime-core-research-mini"))
    parser.add_argument("--reset", action="store_true", help="Clear checkpoint, artifact snapshot and trace before running.")
    parser.add_argument("--stop-after", choices=["plan_research", "collect_evidence", "write_report", "review_report"])
    parser.add_argument("--force-blocked", action="store_true", help="Simulate a tool policy block in write_report.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    result = run_research_mini(
        workdir=args.workdir,
        topic=args.topic,
        reset=args.reset,
        stop_after=args.stop_after,
        force_blocked=args.force_blocked,
    )
    payload = result.model_dump(mode="json")
    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text_report(payload))


if __name__ == "__main__":
    main()
