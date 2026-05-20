from __future__ import annotations

"""运行 Context Builder 最小验证。

这个脚本不调用 LLM，只演示 Runtime 如何为当前 step 构造一个受控上下文包：
- 当前目标和当前 step 始终进入。
- 历史 step 只进入最近摘要。
- artifact 只按 tag 引用摘要和路径。
- memory 需要通过 scope、tag、置信度、有效期筛选。
- trace 只进入摘要，不进入原始 trace。
- sensitive / untrusted / runtime-only 候选会被策略排除。
- required artifact 缺失时会让 bundle 进入 not ready。
"""

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from runtime_core.context import (
    ArtifactCandidate,
    ContextBuilder,
    ContextCandidate,
    ContextBundle,
    ContextPolicy,
    ContextSourceType,
    ContextTrustLevel,
    ContextVisibility,
    MemoryCandidate,
)
from runtime_core.task import TaskContract, TaskType
from runtime_core.task import RuntimeState


def build_demo_bundle() -> ContextBundle:
    contract = TaskContract(
        task_id="context-demo:research-mini",
        task_type=TaskType.RESEARCH,
        goal="围绕 Agent Runtime 的上下文治理写一份短研究报告。",
        expected_outputs=["ContextBundle"],
        success_criteria=[
            "上下文只包含当前 step 所需信息",
            "选择和排除原因可以解释",
            "不把完整 trace 塞入上下文",
        ],
    )
    state = RuntimeState.from_contract(contract)
    state.start_step(
        step_id="collect_sources",
        name="收集资料",
        inputs_summary={"topic": "Agent Runtime context governance"},
    )
    state.finish_step(
        step_id="collect_sources",
        outputs_summary={"sources": 4, "artifact": "evidence_table"},
    )
    state.start_step(
        step_id="draft_outline",
        name="生成大纲",
        inputs_summary={"source_artifact": "evidence_table"},
    )
    state.finish_step(
        step_id="draft_outline",
        outputs_summary={"sections": ["问题", "设计", "风险"]},
    )

    artifacts = [
        ArtifactCandidate(
            artifact_id="artifact:evidence_table",
            title="Evidence Table",
            summary="包含 4 条关于 Context Builder、memory、trace 的证据摘要。",
            tags=["context", "evidence", "research"],
            artifact_type="evidence_table",
            path="artifacts/context-demo/evidence_table.json",
        ),
        ArtifactCandidate(
            artifact_id="artifact:deployment_notes",
            title="Deployment Notes",
            summary="部署和队列相关说明，与当前写作 step 关系较弱。",
            tags=["deployment", "queue"],
            artifact_type="notes",
            path="artifacts/context-demo/deployment_notes.md",
        ),
    ]
    memories = [
        MemoryCandidate(
            memory_id="memory:project-output-style",
            content="当前项目的阶段性总结文档偏好使用 Markdown 表格和短小结。",
            scope="global",
            tags=["writing", "context"],
            confidence=0.9,
            validated=True,
        ),
        MemoryCandidate(
            memory_id="memory:old-provider-note",
            content="旧模型配置中曾经默认使用 DeepSeek，这条信息与当前上下文构造无关。",
            scope="global",
            tags=["llm-provider"],
            confidence=0.8,
            validated=True,
        ),
        MemoryCandidate(
            memory_id="memory:unverified-rule",
            content="未验证的上下文压缩经验，暂不应进入模型上下文。",
            scope="global",
            tags=["context"],
            confidence=0.9,
            validated=False,
        ),
    ]
    extra_candidates = [
        ContextCandidate(
            source_type=ContextSourceType.ARTIFACT_REF,
            source_id="external:untrusted-note",
            title="Untrusted External Note",
            content="外部网页中未经验证的上下文建议，不应直接进入模型上下文。",
            tags=["context"],
            trust_level=ContextTrustLevel.UNTRUSTED,
        ),
        ContextCandidate(
            source_type=ContextSourceType.MEMORY,
            source_id="memory:sensitive-token-note",
            title="Sensitive Runtime Note",
            content="包含敏感配置片段的候选信息。",
            tags=["context"],
            sensitive=True,
        ),
        ContextCandidate(
            source_type=ContextSourceType.ARTIFACT_REF,
            source_id="runtime:debug-state",
            title="Runtime Debug State",
            content="只给 Runtime 调试使用，不发送给模型。",
            tags=["context"],
            visibility=ContextVisibility.RUNTIME_ONLY,
        ),
    ]

    builder = ContextBuilder(max_recent_steps=2, max_item_chars=240, max_context_chars=1200)
    bundle = builder.build(
        contract=contract,
        state=state,
        step_id="write_report",
        current_step="基于证据表和项目写作偏好生成短报告大纲。",
        step_tags=["context", "writing", "research"],
        artifacts=artifacts,
        memories=memories,
        candidates=extra_candidates,
        trace_summary="已完成资料收集和大纲草拟；未记录原始 trace 正文。",
        policy=ContextPolicy(
            max_recent_steps=2,
            max_item_chars=240,
            max_context_chars=1200,
            required_artifact_types=["evidence_table"],
        ),
    )
    return bundle


def render_text_report(bundle: ContextBundle) -> str:
    """把 ContextBundle 渲染为适合人工阅读的过程摘要。"""
    payload = bundle.model_dump(mode="json")
    lines = [
        "Context Builder Demo",
        "=" * 22,
        "",
        "[Task]",
        f"- task_id: {bundle.task_id}",
        f"- task_type: {bundle.task_type}",
        f"- goal: {bundle.goal}",
        f"- current_step: {bundle.current_step}",
        f"- ready: {bundle.ready}",
    ]
    if bundle.blocked_reason:
        lines.append(f"- blocked_reason: {bundle.blocked_reason}")
    if bundle.missing_required_context:
        lines.append(f"- missing_required_context: {', '.join(bundle.missing_required_context)}")

    lines.extend(["", "[Selected Context Items]"])
    for index, item in enumerate(bundle.items, start=1):
        lines.extend(
            [
                f"{index}. {item.source_id}",
                f"   type: {item.source_type.value}",
                f"   visibility: {item.visibility.value}",
                f"   trust: {item.trust_level.value}",
                f"   content: {item.content}",
            ]
        )

    included, excluded = _split_selection_log(payload["selection_log"])
    lines.extend(["", "[Included Decisions]"])
    for decision in included:
        lines.append(_format_decision(decision))

    lines.extend(["", "[Excluded Decisions]"])
    for decision in excluded:
        lines.append(_format_decision(decision))

    metrics = payload["metrics"]
    lines.extend(
        [
            "",
            "[Metrics]",
            f"- total_chars: {metrics['total_chars']}",
            f"- item_count: {metrics['item_count']}",
            f"- included_count: {metrics['included_count']}",
            f"- excluded_count: {metrics['excluded_count']}",
            f"- budget_used_ratio: {metrics['budget_used_ratio']}",
            f"- source_type_breakdown: {metrics['source_type_breakdown']}",
            f"- sensitive_excluded_count: {metrics['sensitive_excluded_count']}",
            f"- untrusted_excluded_count: {metrics['untrusted_excluded_count']}",
            f"- missing_required_count: {metrics['missing_required_count']}",
        ]
    )
    return "\n".join(lines)


def _split_selection_log(
    selection_log: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included = [item for item in selection_log if item["included"]]
    excluded = [item for item in selection_log if not item["included"]]
    return included, excluded


def _format_decision(decision: dict[str, Any]) -> str:
    tags = ",".join(decision["tags"]) if decision["tags"] else "-"
    return (
        f"- {decision['source_id']} | "
        f"type={decision['source_type']} | "
        f"score={decision['score']} | "
        f"tags={tags} | "
        f"reason={decision['reason']}"
    )


def main() -> None:
    parser = ArgumentParser(description="Run the Context Builder demo.")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Use json for full raw ContextBundle.",
    )
    args = parser.parse_args()

    bundle = build_demo_bundle()
    if args.format == "json":
        print(json.dumps(bundle.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return
    print(render_text_report(bundle))


if __name__ == "__main__":
    main()
