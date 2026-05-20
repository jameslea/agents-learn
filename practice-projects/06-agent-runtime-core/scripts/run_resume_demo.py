from __future__ import annotations

"""运行 Checkpoint / Resume 最小验证。

第一次运行：
- 执行 collect。
- 执行 summarize。
- 在 summarize 后模拟中断并保存 checkpoint。

第二次运行：
- 从 checkpoint 恢复。
- 跳过 collect 和 summarize。
- 继续执行 review。
"""

import json
import sys
import tempfile
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from runtime_core.observability import FileCheckpointStore
from runtime_core.task import TaskContract, TaskType
from runtime_core.task import RuntimeState
from runtime_core.execution import StepDefinition, StepRunner


def _steps() -> list[StepDefinition]:
    return [
        StepDefinition(
            step_id="collect",
            name="Collect sources",
            handler=lambda state: {"artifact_id": "artifact:sources", "source_count": 3},
        ),
        StepDefinition(
            step_id="summarize",
            name="Summarize evidence",
            handler=lambda state: {"artifact_id": "artifact:summary", "summary_count": 2},
        ),
        StepDefinition(
            step_id="review",
            name="Review output",
            handler=lambda state: {"review_passed": True},
        ),
    ]


def run_demo() -> dict[str, Any]:
    checkpoint_path = Path(tempfile.gettempdir()) / "agent-runtime-core-resume-demo" / "checkpoint.json"
    store = FileCheckpointStore(checkpoint_path)
    store.clear()

    contract = TaskContract(
        task_id="resume-demo:research-mini",
        task_type=TaskType.RESEARCH,
        goal="验证 checkpoint / resume 可以跳过已完成 step。",
    )
    first_state = RuntimeState.from_contract(contract)
    runner = StepRunner(store)

    first_report = runner.run(
        state=first_state,
        steps=_steps(),
        stop_after_step_id="summarize",
    )

    loaded = store.load()
    resumed_state = loaded.state
    second_report = runner.run(state=resumed_state, steps=_steps())

    return {
        "checkpoint_path": str(checkpoint_path),
        "first_report": first_report.model_dump(mode="json"),
        "second_report": second_report.model_dump(mode="json"),
        "final_state": resumed_state.model_dump(mode="json"),
    }


def render_text_report(payload: dict[str, Any]) -> str:
    final_state = payload["final_state"]
    first_report = payload["first_report"]
    second_report = payload["second_report"]
    lines = [
        "Checkpoint / Resume Demo",
        "=" * 26,
        "",
        f"[Checkpoint] {payload['checkpoint_path']}",
        "",
        "[First run: simulate interruption]",
        f"- completed_steps: {first_report['completed_steps']}",
        f"- skipped_steps: {first_report['skipped_steps']}",
        f"- interrupted: {first_report['interrupted']}",
        f"- final_status: {first_report['final_status']}",
        "",
        "[Second run: resume from checkpoint]",
        f"- completed_steps: {second_report['completed_steps']}",
        f"- skipped_steps: {second_report['skipped_steps']}",
        f"- interrupted: {second_report['interrupted']}",
        f"- final_status: {second_report['final_status']}",
        "",
        "[Final state steps]",
    ]
    for step in final_state["steps"]:
        lines.append(
            f"- {step['step_id']} | status={step['status']} | "
            f"name={step['name']} | outputs={step['outputs_summary']}"
        )
    lines.extend(
        [
            "",
            "[结论]",
            "- 已完成 step 不会重复执行。",
            "- 恢复时会记录 skipped step，方便观察恢复过程。",
            "- checkpoint 保存的是 RuntimeState，而不是 memory 或 artifact payload。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = ArgumentParser(description="Run the Checkpoint / Resume demo.")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Use json for full raw payload.",
    )
    args = parser.parse_args()

    payload = run_demo()
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(render_text_report(payload))


if __name__ == "__main__":
    main()
