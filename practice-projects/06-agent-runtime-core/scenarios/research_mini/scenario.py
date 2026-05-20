from __future__ import annotations

"""research_mini：阶段 6 的端到端最小 Agent 场景。

场景不调用真实 LLM，而用确定性 step 模拟一个研究型 Agent：
1. 生成研究计划。
2. 整理 EvidenceTable。
3. 消费 EvidenceTable，生成 DraftReport。
4. 消费 DraftReport，生成 ReviewResult。

重点是观察 Runtime Core 如何支撑 context、memory、artifact、checkpoint、
trace、tool policy 和 blocked，而不是评估模型能力。
"""

from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field

from runtime_core.artifact import ArtifactRecord
from scenarios.research_mini.schemas import (
    DEFAULT_RESEARCH_MINI_SCHEMAS,
    DraftReport,
    DraftSection,
    EvidenceItem,
    EvidenceTable,
    ReviewIssue,
    ReviewResult,
)
from runtime_core.task import TaskContract, TaskType
from runtime_core.memory import MemoryRecord
from runtime_core.execution import BlockedReason, MinimalRuntime
from runtime_core.execution import ToolCallRequest, ToolPolicy, ToolPolicyChecker, ToolRiskLevel
from runtime_core.observability import TraceEventType


STEP_PLAN = "plan_research"
STEP_EVIDENCE = "collect_evidence"
STEP_WRITE = "write_report"
STEP_REVIEW = "review_report"


class ResearchMiniRunResult(BaseModel):
    """research_mini 一次运行的摘要。"""

    task_id: str = Field(description="任务 ID。")
    status: str = Field(description="最终任务状态。")
    resumed: bool = Field(description="是否从 checkpoint 恢复。")
    checkpoint_path: str = Field(description="checkpoint 文件路径。")
    artifact_snapshot_path: str = Field(description="artifact 快照路径。")
    trace_path: str = Field(description="trace 文件路径。")
    artifacts: list[str] = Field(default_factory=list, description="本任务产出的 artifact id。")
    skipped_steps: list[str] = Field(default_factory=list, description="本次恢复时跳过的 step。")
    blocked_reason: BlockedReason | None = Field(default=None, description="blocked 说明。")
    trace_summary: dict[str, Any] = Field(default_factory=dict, description="trace 复盘摘要。")
    final_review_passed: bool | None = Field(default=None, description="最终 review 是否通过。")


def create_contract(topic: str) -> TaskContract:
    return TaskContract(
        task_id="research-mini:runtime-core",
        task_type=TaskType.RESEARCH,
        goal=f"围绕主题“{topic}”生成一份短研究报告并完成审查。",
        inputs={"topic": topic},
        expected_outputs=["EvidenceTableV1", "DraftReportV1", "ReviewResultV1"],
        success_criteria=["报告必须引用证据", "审查结果必须通过 schema 校验", "运行过程必须可复盘"],
    )


def default_memories() -> list[MemoryRecord]:
    return [
        MemoryRecord(
            memory_id="memory:report-style",
            content="项目阶段总结偏好使用短段落、明确边界和简短结论。",
            scope="research",
            tags=["writing", "review"],
            confidence=0.9,
            validated=True,
            source="project_memory",
        )
    ]


def run_research_mini(
    *,
    workdir: str | Path,
    topic: str = "Agent Runtime Core",
    reset: bool = False,
    stop_after: str | None = None,
    force_blocked: bool = False,
) -> ResearchMiniRunResult:
    workdir = Path(workdir)
    contract = create_contract(topic)
    runtime = MinimalRuntime(
        contract=contract,
        checkpoint_path=workdir / "checkpoint.json",
        trace_path=workdir / "trace.jsonl",
        artifact_snapshot_path=workdir / "artifacts.json",
        artifact_schemas=DEFAULT_RESEARCH_MINI_SCHEMAS,
        memories=default_memories(),
        reset=reset,
    )
    runtime.start_task()
    skipped_steps: list[str] = []

    for step_id, handler in [
        (STEP_PLAN, _step_plan_research),
        (STEP_EVIDENCE, _step_collect_evidence),
        (STEP_WRITE, _step_write_report),
        (STEP_REVIEW, _step_review_report),
    ]:
        if runtime.skip_step(step_id=step_id, reason="already passed in checkpoint"):
            skipped_steps.append(step_id)
            continue
        blocked = handler(runtime, topic=topic, force_blocked=force_blocked)
        if blocked:
            runtime.finish_task(final_status="blocked", summary=f"Task blocked at {blocked.step_id}: {blocked.reason}")
            return _result(runtime, skipped_steps=skipped_steps, blocked_reason=blocked)
        if stop_after == step_id:
            runtime.state.status = "interrupted"
            runtime.save_checkpoint()
            return _result(runtime, skipped_steps=skipped_steps)

    review = cast(ReviewResult, runtime.consume_artifact(artifact_id="artifact:review-result", schema_name="ReviewResultV1", consumer_step_id="final"))
    runtime.finish_task(final_status="completed", summary="research_mini completed.")
    return _result(runtime, skipped_steps=skipped_steps, final_review_passed=review.passed)


def _step_plan_research(runtime: MinimalRuntime, *, topic: str, force_blocked: bool) -> BlockedReason | None:
    del force_blocked
    context = runtime.build_context(
        step_id=STEP_PLAN,
        current_step="规划研究问题和证据收集方向。",
        step_tags=["research", "planning"],
    )
    runtime.start_step(
        step_id=STEP_PLAN,
        name="Plan research",
        inputs_summary={"topic": topic, "context_items": len(context.items)},
    )
    runtime.state.values["research_plan"] = {
        "questions": ["Runtime Core 需要哪些公共能力？", "哪些能力应由场景代码负责？"],
        "evidence_targets": ["context", "artifact", "trace"],
    }
    runtime.pass_step(
        step_id=STEP_PLAN,
        outputs_summary={"question_count": 2, "evidence_targets": ["context", "artifact", "trace"]},
    )
    return None


def _step_collect_evidence(runtime: MinimalRuntime, *, topic: str, force_blocked: bool) -> BlockedReason | None:
    del force_blocked
    context = runtime.build_context(
        step_id=STEP_EVIDENCE,
        current_step="整理证据表。",
        step_tags=["research", "evidence"],
    )
    runtime.start_step(
        step_id=STEP_EVIDENCE,
        name="Collect evidence",
        inputs_summary={"topic": topic, "context_items": len(context.items)},
    )
    evidence = EvidenceTable(
        topic=topic,
        rows=[
            EvidenceItem(
                evidence_id="ev-runtime-001",
                claim="Runtime Core should provide context, state, artifact, trace and checkpoint support.",
                source="docs/agent-core-capabilities-validation-plan.md",
                confidence=0.9,
            ),
            EvidenceItem(
                evidence_id="ev-runtime-002",
                claim="Scenario code should own business steps while Runtime provides common guardrails.",
                source="practice-projects/06-agent-runtime-core/docs/06-minimal-runtime.md",
                confidence=0.85,
            ),
        ],
    )
    runtime.save_artifact(
        ArtifactRecord(
            artifact_id="artifact:evidence-table",
            artifact_type="evidence_table",
            title="Runtime Core Evidence Table",
            summary="Two evidence rows about runtime boundaries.",
            path="artifacts/research-mini/evidence_table.json",
            schema_name="EvidenceTableV1",
            producer_step_id=STEP_EVIDENCE,
            tags=["research", "evidence", "writing"],
            payload=evidence.model_dump(mode="json"),
        )
    )
    runtime.pass_step(
        step_id=STEP_EVIDENCE,
        outputs_summary={"artifact_id": "artifact:evidence-table", "row_count": len(evidence.rows)},
    )
    return None


def _step_write_report(runtime: MinimalRuntime, *, topic: str, force_blocked: bool) -> BlockedReason | None:
    context = runtime.build_context(
        step_id=STEP_WRITE,
        current_step="基于证据表生成短报告。",
        step_tags=["writing", "evidence"],
        required_artifact_types=["evidence_table"],
    )
    runtime.start_step(
        step_id=STEP_WRITE,
        name="Write report",
        inputs_summary={"topic": topic, "context_ready": context.ready, "context_items": len(context.items)},
    )
    decision = ToolPolicyChecker(
        [
            ToolPolicy(
                tool_name="markdown_writer",
                risk_level=ToolRiskLevel.MEDIUM,
                read_only=True,
                requires_approval=False,
            )
        ]
    ).check(
        ToolCallRequest(
            tool_name="markdown_writer",
            step_id=STEP_WRITE,
            mutating=force_blocked,
        )
    )
    runtime.trace_recorder.record(
        event_type=TraceEventType.TOOL_CALLED,
        task_id=runtime.contract.task_id,
        step_id=STEP_WRITE,
        summary="Check markdown writer policy.",
        data={"tool_name": "markdown_writer", "allowed": decision.allowed, "reason": decision.reason},
        risk=decision.risk_level.value,
    )
    if not decision.allowed:
        return runtime.block(
            step_id=STEP_WRITE,
            reason=decision.reason,
            suggested_action="确认是否允许该工具执行写入型操作，或改用只读预览模式。",
        )

    evidence = cast(EvidenceTable, runtime.consume_artifact(artifact_id="artifact:evidence-table", schema_name="EvidenceTableV1", consumer_step_id=STEP_WRITE))
    draft = DraftReport(
        title=f"{topic} runtime note",
        evidence_artifact_id="artifact:evidence-table",
        sections=[
            DraftSection(
                heading="Runtime boundary",
                content="Runtime Core should keep common support capabilities separate from scenario business logic.",
                evidence_refs=[row.evidence_id for row in evidence.rows],
            )
        ],
    )
    runtime.save_artifact(
        ArtifactRecord(
            artifact_id="artifact:draft-report",
            artifact_type="draft_report",
            title="Runtime Core Draft Report",
            summary="Short report generated from EvidenceTable.",
            path="artifacts/research-mini/draft_report.json",
            schema_name="DraftReportV1",
            producer_step_id=STEP_WRITE,
            tags=["writing", "review"],
            payload=draft.model_dump(mode="json"),
            metadata={"consumed_artifact_ids": ["artifact:evidence-table"]},
        )
    )
    runtime.pass_step(step_id=STEP_WRITE, outputs_summary={"artifact_id": "artifact:draft-report", "section_count": len(draft.sections)})
    return None


def _step_review_report(runtime: MinimalRuntime, *, topic: str, force_blocked: bool) -> BlockedReason | None:
    del topic, force_blocked
    context = runtime.build_context(
        step_id=STEP_REVIEW,
        current_step="审查报告是否引用证据并通过结构化输出。",
        step_tags=["review", "writing"],
        required_artifact_types=["draft_report"],
    )
    runtime.start_step(
        step_id=STEP_REVIEW,
        name="Review report",
        inputs_summary={"context_ready": context.ready, "context_items": len(context.items)},
    )
    draft = cast(DraftReport, runtime.consume_artifact(artifact_id="artifact:draft-report", schema_name="DraftReportV1", consumer_step_id=STEP_REVIEW))
    has_refs = all(section.evidence_refs for section in draft.sections)
    review = ReviewResult(
        score=88 if has_refs else 55,
        issues=[] if has_refs else [ReviewIssue(severity="high", message="Missing evidence references.")],
        required_changes=[] if has_refs else ["Add evidence refs to every section."],
        passed=has_refs,
    )
    runtime.save_artifact(
        ArtifactRecord(
            artifact_id="artifact:review-result",
            artifact_type="review_result",
            title="Runtime Core Review Result",
            summary=f"Review passed={review.passed}, score={review.score}.",
            path="artifacts/research-mini/review_result.json",
            schema_name="ReviewResultV1",
            producer_step_id=STEP_REVIEW,
            tags=["review"],
            payload=review.model_dump(mode="json"),
            metadata={"consumed_artifact_ids": ["artifact:draft-report"]},
        )
    )
    runtime.pass_step(step_id=STEP_REVIEW, outputs_summary={"artifact_id": "artifact:review-result", "passed": review.passed})
    return None


def _result(
    runtime: MinimalRuntime,
    *,
    skipped_steps: list[str],
    blocked_reason: BlockedReason | None = None,
    final_review_passed: bool | None = None,
) -> ResearchMiniRunResult:
    return ResearchMiniRunResult(
        task_id=runtime.contract.task_id,
        status=runtime.state.status,
        resumed=runtime.resumed,
        checkpoint_path=str(runtime.checkpoint_store.path),
        artifact_snapshot_path=str(runtime.artifact_snapshot_path),
        trace_path=str(runtime.trace_recorder.path),
        artifacts=list(runtime.state.artifact_ids),
        skipped_steps=skipped_steps,
        blocked_reason=blocked_reason,
        trace_summary=runtime.trace_summary().model_dump(mode="json"),
        final_review_passed=final_review_passed,
    )
