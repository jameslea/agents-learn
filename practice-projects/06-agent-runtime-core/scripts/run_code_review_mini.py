from __future__ import annotations

"""运行 code_review_mini 场景驱动 Runtime Core 试验。"""

import json
import logging
import sys
import tempfile
from argparse import ArgumentParser
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from scenarios.code_review_mini.scenario import run_code_review_mini


DEFAULT_TARGET = PROJECT_DIR / "scenarios" / "code_review_mini" / "sample_target.py"
LOGGER = logging.getLogger("code_review_mini")


def render_text_report(payload: dict[str, Any]) -> str:
    lines = [
        "Code Review Mini Runtime Demo",
        "=" * 29,
        "",
        f"- status: {payload['status']}",
        f"- resumed: {payload['resumed']}",
        f"- checkpoint: {payload['checkpoint_path']}",
        f"- artifacts snapshot: {payload['artifact_snapshot_path']}",
        f"- trace: {payload['trace_path']}",
        f"- artifacts: {payload['artifacts']}",
        f"- skipped_steps: {payload['skipped_steps']}",
        f"- reviewer: {payload['reviewer']}",
        f"- reviewer_provider: {payload['reviewer_provider']}",
        f"- reviewer_model: {payload['reviewer_model']}",
        f"- reviewer_status: {payload['reviewer_status']}",
        f"- reviewer_latency_ms: {payload['reviewer_latency_ms']}",
        f"- reviewer_prompt_chars: {payload['reviewer_prompt_chars']}",
        f"- reviewer_response_chars: {payload['reviewer_response_chars']}",
        f"- finding_count: {payload['finding_count']}",
        f"- risk_level: {payload['risk_level']}",
    ]
    if payload.get("reviewer_failure_reason"):
        lines.append(f"- reviewer_failure_reason: {payload['reviewer_failure_reason']}")
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
        ]
    )
    if payload.get("runtime_friction"):
        lines.extend(["", "[Runtime friction]"])
        lines.extend(f"- {item}" for item in payload["runtime_friction"])
    lines.extend(
        [
            "",
            "[结论]",
            "- 该场景复用了 Runtime Core public API，没有把业务 schema 放入 runtime_core。",
            "- 默认离线 reviewer 用于稳定验证；--llm 可切换到真实 LLM 审查。",
            "- patch step 只产出 PatchSuggestion，不直接修改目标文件。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = ArgumentParser(description="Run the code_review_mini Runtime Core scenario.")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="Target code file to review.")
    parser.add_argument("--workdir", default=str(Path(tempfile.gettempdir()) / "agent-runtime-core-code-review-mini"))
    parser.add_argument("--reset", action="store_true", help="Clear checkpoint, artifact snapshot and trace before running.")
    parser.add_argument("--stop-after", choices=["collect_code_context", "llm_or_rule_review", "propose_patch"])
    parser.add_argument("--force-blocked", action="store_true", help="Simulate a patch writer approval block.")
    parser.add_argument("--llm", action="store_true", help="Use the configured real LLM reviewer.")
    parser.add_argument("--provider", help="Override LLM_PROVIDER for --llm, e.g. minimax/deepseek/openai/custom.")
    parser.add_argument("--model", help="Override provider model for --llm.")
    parser.add_argument("--temperature", type=float, default=0.1, help="LLM reviewer temperature.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    LOGGER.info("start target=%s workdir=%s reset=%s llm=%s", args.target, args.workdir, args.reset, args.llm)
    if args.llm:
        LOGGER.info(
            "llm reviewer requested provider=%s model=%s temperature=%.2f",
            args.provider or "<env>",
            args.model or "<env>",
            args.temperature,
        )

    result = run_code_review_mini(
        workdir=args.workdir,
        target_path=args.target,
        reset=args.reset,
        stop_after=args.stop_after,
        use_llm=args.llm,
        llm_provider=args.provider,
        llm_model=args.model,
        llm_temperature=args.temperature,
        force_blocked=args.force_blocked,
    )
    LOGGER.info(
        "finished status=%s reviewer=%s provider=%s model=%s latency_ms=%d findings=%d",
        result.status,
        result.reviewer,
        result.reviewer_provider,
        result.reviewer_model,
        result.reviewer_latency_ms,
        result.finding_count,
    )
    payload = result.model_dump(mode="json")
    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text_report(payload))


if __name__ == "__main__":
    main()
