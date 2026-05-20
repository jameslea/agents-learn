from __future__ import annotations

"""运行 Trace 与复盘最小验证。

demo 会生成一个 JSONL trace：
- task started
- research step started / passed
- artifact created
- writer step started
- artifact consumed
- tool called
- writer step failed
- human required
- task finished

失败事件中故意带一个 secret 字段，用于验证 trace 脱敏。
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

from scenarios.research_mini.schemas import DEFAULT_RESEARCH_MINI_SCHEMAS, EvidenceItem, EvidenceTable
from runtime_core.artifact import ArtifactStore
from runtime_core.observability import TraceEventType, TraceReader, TraceRecorder


def run_demo() -> dict[str, Any]:
    trace_path = Path(tempfile.gettempdir()) / "agent-runtime-core-trace-demo" / "trace.jsonl"
    recorder = TraceRecorder(trace_path, reset=True)
    store = ArtifactStore(schemas=DEFAULT_RESEARCH_MINI_SCHEMAS)
    task_id = "trace-demo:research-mini"

    recorder.task_started(
        task_id=task_id,
        task_type="research",
        goal_summary="验证 trace 可以复盘 step、artifact、工具和失败原因。",
    )
    recorder.record(
        event_type=TraceEventType.STEP_STARTED,
        task_id=task_id,
        step_id="research",
        summary="Research step started.",
        data={"input_summary": {"topic": "Agent Runtime Core trace"}},
    )

    evidence = EvidenceTable(
        topic="Agent Runtime Core trace",
        rows=[
            EvidenceItem(
                evidence_id="ev-trace-001",
                claim="Trace should record artifact references instead of full payloads.",
                source="practice-projects/06-agent-runtime-core/docs/05-trace-replay.md",
                confidence=0.88,
            )
        ],
    )
    artifact = store.save_model(
        artifact_id="artifact:trace-evidence",
        artifact_type="evidence_table",
        title="Trace Evidence",
        summary="One evidence row about trace artifact references.",
        schema_name="EvidenceTableV1",
        model=evidence,
        producer_step_id="research",
        tags=["trace", "evidence"],
        path="artifacts/trace-demo/evidence_table.json",
    )
    recorder.record(
        event_type=TraceEventType.ARTIFACT_CREATED,
        task_id=task_id,
        step_id="research",
        summary="Evidence artifact created.",
        data={
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "schema_name": artifact.schema_name,
            "path": artifact.path,
        },
    )
    recorder.record(
        event_type=TraceEventType.STEP_PASSED,
        task_id=task_id,
        step_id="research",
        summary="Research step passed.",
        data={"output_summary": {"artifact_id": artifact.artifact_id, "row_count": len(evidence.rows)}},
    )

    recorder.record(
        event_type=TraceEventType.STEP_STARTED,
        task_id=task_id,
        step_id="writer",
        summary="Writer step started.",
        data={"input_summary": {"source_artifact_id": artifact.artifact_id}},
    )
    recorder.record(
        event_type=TraceEventType.ARTIFACT_CONSUMED,
        task_id=task_id,
        step_id="writer",
        summary="Writer consumed evidence artifact.",
        data={
            "artifact_id": artifact.artifact_id,
            "schema_name": "EvidenceTableV1",
            "consumer_step_id": "writer",
        },
    )
    recorder.record(
        event_type=TraceEventType.TOOL_CALLED,
        task_id=task_id,
        step_id="writer",
        summary="Render markdown preview.",
        data={
            "tool_name": "markdown_renderer",
            "args_summary": {"format": "markdown", "api_key": "sk-demo-secret"},
        },
        risk="medium",
    )
    recorder.record(
        event_type=TraceEventType.STEP_FAILED,
        task_id=task_id,
        step_id="writer",
        summary="Writer failed because required section was missing. token=trace-secret-token",
        data={
            "error_type": "ValidationError",
            "message": "DraftReport.sections is empty.",
            "secret": "trace-secret-value",
            "recoverable": True,
        },
        risk="medium",
        recoverable=True,
    )
    recorder.record(
        event_type=TraceEventType.HUMAN_REQUIRED,
        task_id=task_id,
        step_id="writer",
        summary="Human review required before retrying writer step.",
        data={"reason": "draft schema validation failed", "pending_action": "补充报告章节后重试"},
        risk="high",
    )
    recorder.task_finished(
        task_id=task_id,
        final_status="failed",
        summary="Task stopped after writer failure.",
    )

    reader = TraceReader(trace_path)
    return {
        "trace_path": str(trace_path),
        "events": [event.model_dump(mode="json") for event in reader.read_events()],
        "summary": reader.replay().model_dump(mode="json"),
    }


def render_text_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "Trace / Replay Demo",
        "=" * 19,
        "",
        f"[Trace file] {payload['trace_path']}",
        "",
        "[Replay summary]",
        f"- task_id: {summary['task_id']}",
        f"- event_count: {summary['event_count']}",
        f"- event_type_counts: {summary['event_type_counts']}",
        "",
        "[Failed steps]",
    ]
    for item in summary["failed_steps"]:
        lines.append(f"- {item['step_id']} | {item['summary']} | recoverable={item['recoverable']}")

    lines.extend(["", "[Artifact flow]"])
    for item in summary["artifact_flow"]:
        lines.append(f"- {item['event_type']} | step={item['step_id']} | data={item['data']}")

    lines.extend(["", "[Risk / human events]"])
    for item in summary["risk_events"]:
        lines.append(f"- {item['event_type']} | risk={item['risk']} | step={item['step_id']} | {item['summary']}")

    lines.extend(
        [
            "",
            "[结论]",
            "- trace 可以定位失败 step 和原因。",
            "- trace 记录 artifact 引用和 schema，不记录完整 payload。",
            "- trace 写入前会对 token、api_key、secret 等字段做基础脱敏。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = ArgumentParser(description="Run the Trace / Replay demo.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    payload = run_demo()
    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text_report(payload))


if __name__ == "__main__":
    main()
