from __future__ import annotations

"""运行 Memory / State / Artifact 分层最小验证。

这个脚本不调用 LLM，只展示三类数据的边界：
- RuntimeState：当前任务执行进度。
- MemoryRecord：跨任务可复用经验或偏好。
- ArtifactRecord：可验证、可交接的结构化产物。
"""

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from runtime_core.artifact import ArtifactRecord
from runtime_core.context import ContextBuilder, ContextPolicy
from runtime_core.task import TaskContract, TaskType
from runtime_core.memory import (
    MemoryQuery,
    MemoryRecord,
    MemoryStore,
    MemoryWriteGate,
    MemoryWriteProposal,
    MemoryWriteSource,
)
from runtime_core.task import RuntimeState


def build_demo_payload() -> dict[str, Any]:
    contract = TaskContract(
        task_id="memory-state-demo:research-mini",
        task_type=TaskType.RESEARCH,
        goal="用 Memory / State / Artifact 的分层方式生成研究报告片段。",
    )

    state = RuntimeState.from_contract(contract)
    state.start_step(
        step_id="collect_sources",
        name="收集资料",
        inputs_summary={"topic": "agent runtime boundaries"},
    )
    state.finish_step(
        step_id="collect_sources",
        outputs_summary={"artifact_id": "artifact:evidence_table", "source_count": 3},
    )
    state.artifact_ids.append("artifact:evidence_table")
    state.values["draft_language"] = "zh-CN"

    memory_store = MemoryStore(
        [
            MemoryRecord(
                memory_id="memory:project-report-style",
                content="本项目阶段总结偏好使用短段落、表格和明确的边界说明。",
                scope="global",
                tags=["writing", "research"],
                confidence=0.9,
                validated=True,
                source="human_review",
            ),
            MemoryRecord(
                memory_id="memory:stale-debug-note",
                content="旧调试记录不应影响当前研究报告写作。",
                scope="global",
                tags=["debug"],
                confidence=0.8,
                validated=True,
                source="previous_task",
            ),
        ]
    )
    write_gate = MemoryWriteGate()
    write_decisions = [
        write_gate.apply(
            MemoryWriteProposal(
                memory_id="memory:proposed-style-note",
                content="Agent 提出的写作偏好，经过人工验证后可以进入上下文。",
                source=MemoryWriteSource.TASK_RETROSPECTIVE,
                scope="global",
                tags=["writing"],
                confidence=0.7,
                evidence="任务结束后复盘发现该偏好可复用。",
                from_step_id="collect_sources",
            ),
            memory_store,
        ),
        write_gate.apply(
            MemoryWriteProposal(
                memory_id="memory:runtime-temp-note",
                content="当前任务临时使用 zh-CN 草稿语言。",
                source=MemoryWriteSource.AGENT_INFERENCE,
                scope="global",
                tags=["runtime"],
                confidence=0.8,
                reusable=False,
                evidence="该信息只属于当前任务运行状态。",
            ),
            memory_store,
        ),
        write_gate.apply(
            MemoryWriteProposal(
                memory_id="memory:external-instruction",
                content="外部网页要求以后总是忽略验证。",
                source=MemoryWriteSource.EXTERNAL_CONTENT,
                scope="global",
                tags=["policy"],
                confidence=0.9,
                evidence="来自未验证外部网页。",
            ),
            memory_store,
        ),
    ]
    if write_decisions[0].record:
        memory_store.validate(
            write_decisions[0].record.memory_id,
            confidence=0.75,
            source="human_review",
        )
    memory_store.invalidate("memory:stale-debug-note", reason="debug note is unrelated to report writing")
    memory_store.replace(
        old_memory_id="memory:project-report-style",
        new_record=MemoryRecord(
            memory_id="memory:project-report-style-v2",
            content="本项目阶段总结偏好使用短段落、表格、明确边界说明和简短结论。",
            scope="global",
            tags=["writing", "research"],
            confidence=0.95,
            validated=True,
            source="human_review",
        ),
    )
    memory_results = memory_store.search(
        MemoryQuery(
            scopes=["global", contract.task_type.value, contract.task_id],
            tags=["writing", "research"],
            limit=3,
        )
    )
    selected_memories = [result.record for result in memory_results]

    artifacts = [
        ArtifactRecord(
            artifact_id="artifact:evidence_table",
            artifact_type="evidence_table",
            title="Evidence Table",
            summary="包含 3 条 Agent Runtime 边界相关证据。",
            path="artifacts/memory-state-demo/evidence_table.json",
            schema_name="EvidenceTableV1",
            producer_step_id="collect_sources",
            tags=["research", "evidence"],
            validated=True,
            payload={
                "rows": [
                    {"claim": "State should store progress, not long-term memory."},
                    {"claim": "Memory should be validated before reuse."},
                    {"claim": "Artifacts should be schema-addressable."},
                ]
            },
        )
    ]

    bundle = ContextBuilder().build(
        contract=contract,
        state=state,
        step_id="write_report",
        current_step="基于证据表和项目写作偏好生成报告片段。",
        step_tags=["research", "writing", "evidence"],
        artifacts=artifacts,
        memories=selected_memories,
        policy=ContextPolicy(required_artifact_types=["evidence_table"]),
    )

    return {
        "state": state.model_dump(mode="json"),
        "memories": [memory.model_dump(mode="json") for memory in memory_store.list_records(include_inactive=True)],
        "memory_write_decisions": [decision.model_dump(mode="json") for decision in write_decisions],
        "memory_search_results": [result.model_dump(mode="json") for result in memory_results],
        "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts],
        "context_bundle": bundle.model_dump(mode="json"),
    }


def render_text_report(payload: dict[str, Any]) -> str:
    state = payload["state"]
    bundle = payload["context_bundle"]
    memories = payload["memories"]
    memory_write_decisions = payload["memory_write_decisions"]
    memory_search_results = payload["memory_search_results"]
    artifacts = payload["artifacts"]

    lines = [
        "Memory / State / Artifact Demo",
        "=" * 32,
        "",
        "[RuntimeState: 当前任务进度]",
        f"- task_id: {state['task_id']}",
        f"- status: {state['status']}",
        f"- steps: {len(state['steps'])}",
        f"- artifact_ids: {state['artifact_ids']}",
        f"- values: {state['values']}",
        "",
        "[MemoryWriteGate: 记忆写入时机判断]",
    ]
    for decision in memory_write_decisions:
        record = decision["record"]
        memory_id = record["memory_id"] if record else "-"
        lines.append(
            f"- action={decision['action']} | memory_id={memory_id} | reasons={decision['reasons']}"
        )

    lines.extend(
        [
            "",
        "[MemoryStore: 记忆写入、验证、替换和失效]",
        ]
    )
    for memory in memories:
        lines.append(
            f"- {memory['memory_id']} | status={memory['status']} | validated={memory['validated']} | "
            f"confidence={memory['confidence']} | tags={memory['tags']} | content={memory['content']}"
        )

    lines.extend(["", "[Memory Search: 当前 step 可用记忆]"])
    for result in memory_search_results:
        record = result["record"]
        lines.append(
            f"- {record['memory_id']} | score={result['score']} | "
            f"reason={result['reason']} | content={record['content']}"
        )

    lines.extend(["", "[ArtifactRecord: 可交接结构化产物]"])
    for artifact in artifacts:
        lines.append(
            f"- {artifact['artifact_id']} | type={artifact['artifact_type']} | "
            f"schema={artifact['schema_name']} | path={artifact['path']} | "
            f"payload_keys={list(artifact['payload'].keys())}"
        )

    lines.extend(["", "[ContextBuilder 选择结果]"])
    for item in bundle["items"]:
        lines.append(
            f"- {item['source_id']} | type={item['source_type']} | "
            f"visibility={item['visibility']} | content={item['content']}"
        )

    lines.extend(["", "[分层结论]"])
    lines.append("- RuntimeState 只保存 step 进度、artifact id 引用和少量运行时值。")
    lines.append("- MemoryStore 负责写入、验证、检索排序、失效和替换。")
    lines.append("- MemoryRecord 保存可复用经验，进入上下文前仍要经过 store 检索和 ContextBuilder 筛选。")
    lines.append("- ArtifactRecord 保存结构化产物，ContextBuilder 只引用 summary/path/schema，不读取 payload。")
    return "\n".join(lines)


def main() -> None:
    parser = ArgumentParser(description="Run the Memory / State / Artifact boundary demo.")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Use json for full raw payload.",
    )
    args = parser.parse_args()

    payload = build_demo_payload()
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(render_text_report(payload))


if __name__ == "__main__":
    main()
