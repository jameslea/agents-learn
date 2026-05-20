from __future__ import annotations

"""code_review_mini：真实 LLM 场景驱动 Runtime Core 试验。

该场景用于观察非 research 类 Agent 如何复用 Runtime Core：
1. 读取目标代码并保存 CodeSnapshot artifact。
2. 使用确定性审查器或真实 LLM 生成 ReviewReport artifact。
3. 根据审查发现生成 PatchSuggestion artifact，但不直接修改文件。

场景重点不是做完整代码审查产品，而是记录 Runtime Core public API 在具体
Agent 场景中的使用摩擦。
"""

from pathlib import Path
import time
from typing import Any, Protocol, cast

from pydantic import BaseModel, Field

from runtime_core.artifact import ArtifactRecord
from runtime_core.execution import BlockedReason, MinimalRuntime
from runtime_core.execution import ToolCallRequest, ToolPolicy, ToolPolicyChecker, ToolRiskLevel
from runtime_core.memory import MemoryRecord
from runtime_core.observability import TraceEventType
from runtime_core.task import TaskContract, TaskType
from scenarios.code_review_mini.llm_reviewer import CodeReviewLLMResult, deterministic_review
from scenarios.code_review_mini.schemas import (
    DEFAULT_CODE_REVIEW_MINI_SCHEMAS,
    CodeSnapshot,
    PatchSuggestion,
    ReviewReport,
)


STEP_COLLECT = "collect_code_context"
STEP_REVIEW = "llm_or_rule_review"
STEP_PATCH = "propose_patch"


class CodeReviewer(Protocol):
    """可替换的代码审查器协议。测试中可注入 fake reviewer。"""

    def review(self, *, file_path: str, code: str, context_summary: str) -> CodeReviewLLMResult:
        ...


class CodeReviewMiniRunResult(BaseModel):
    """code_review_mini 一次运行摘要。"""

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
    finding_count: int = Field(default=0, description="审查发现数量。")
    risk_level: str = Field(default="", description="最终风险等级。")
    reviewer: str = Field(default="", description="审查器来源。")
    reviewer_provider: str = Field(default="", description="LLM provider 或 deterministic。")
    reviewer_model: str = Field(default="", description="LLM model 或规则审查器名称。")
    reviewer_status: str = Field(default="", description="审查器调用状态。")
    reviewer_latency_ms: int = Field(default=0, ge=0, description="审查器耗时，毫秒。")
    reviewer_prompt_chars: int = Field(default=0, ge=0, description="发送给审查器的 prompt 字符数。")
    reviewer_response_chars: int = Field(default=0, ge=0, description="审查器响应字符数。")
    reviewer_failure_reason: str = Field(default="", description="审查器失败原因。")
    runtime_friction: list[str] = Field(default_factory=list, description="本场景观察到的 Runtime Core 使用摩擦。")


def create_contract(target_path: str) -> TaskContract:
    return TaskContract(
        task_id=f"code-review-mini:{Path(target_path).name}",
        task_type=TaskType.CODE_REVIEW,
        goal=f"审查文件 {target_path}，输出结构化发现和补丁建议。",
        inputs={"target_path": target_path},
        expected_outputs=["CodeSnapshotV1", "ReviewReportV1", "PatchSuggestionV1"],
        success_criteria=["审查发现必须结构化", "不直接修改文件", "运行过程必须可复盘"],
    )


def default_memories() -> list[MemoryRecord]:
    return [
        MemoryRecord(
            memory_id="memory:code-review-policy",
            content="代码审查场景中，命令执行、文件写入和补丁应用必须默认要求人工确认。",
            scope="code_review",
            tags=["review", "tool_policy", "patch"],
            confidence=0.9,
            validated=True,
            source="project_memory",
        )
    ]


def run_code_review_mini(
    *,
    workdir: str | Path,
    target_path: str | Path,
    reset: bool = False,
    stop_after: str | None = None,
    use_llm: bool = False,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    llm_temperature: float = 0.1,
    reviewer: CodeReviewer | None = None,
    force_blocked: bool = False,
) -> CodeReviewMiniRunResult:
    workdir = Path(workdir)
    target = Path(target_path)
    contract = create_contract(str(target))
    runtime = MinimalRuntime(
        contract=contract,
        checkpoint_path=workdir / "checkpoint.json",
        trace_path=workdir / "trace.jsonl",
        artifact_snapshot_path=workdir / "artifacts.json",
        artifact_schemas=DEFAULT_CODE_REVIEW_MINI_SCHEMAS,
        memories=default_memories(),
        reset=reset,
    )
    runtime.start_task()
    skipped_steps: list[str] = []
    runtime_friction: list[str] = []

    for step_id, handler in [
        (STEP_COLLECT, _step_collect_code_context),
        (STEP_REVIEW, _step_review_code),
        (STEP_PATCH, _step_propose_patch),
    ]:
        if runtime.skip_step(step_id=step_id, reason="already passed in checkpoint"):
            skipped_steps.append(step_id)
            continue
        blocked = handler(
            runtime,
            target=target,
            use_llm=use_llm,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            reviewer=reviewer,
            force_blocked=force_blocked,
            runtime_friction=runtime_friction,
        )
        if blocked:
            runtime.finish_task(final_status="blocked", summary=f"Task blocked at {blocked.step_id}: {blocked.reason}")
            return _result(runtime, skipped_steps=skipped_steps, blocked_reason=blocked, runtime_friction=runtime_friction)
        if stop_after == step_id:
            runtime.state.status = "interrupted"
            runtime.save_checkpoint()
            return _result(runtime, skipped_steps=skipped_steps, runtime_friction=runtime_friction)

    runtime.finish_task(final_status="completed", summary="code_review_mini completed.")
    return _result(runtime, skipped_steps=skipped_steps, runtime_friction=runtime_friction)


def _step_collect_code_context(
    runtime: MinimalRuntime,
    *,
    target: Path,
    use_llm: bool,
    llm_provider: str | None,
    llm_model: str | None,
    llm_temperature: float,
    reviewer: CodeReviewer | None,
    force_blocked: bool,
    runtime_friction: list[str],
) -> BlockedReason | None:
    del use_llm, llm_provider, llm_model, llm_temperature, reviewer, force_blocked
    context = runtime.build_context(
        step_id=STEP_COLLECT,
        current_step="读取目标代码并构造 CodeSnapshot artifact。",
        step_tags=["code", "review", "read"],
    )
    runtime.start_step(
        step_id=STEP_COLLECT,
        name="Collect code context",
        inputs_summary={"target_path": str(target), "context_items": len(context.items)},
    )
    if not target.exists() or not target.is_file():
        return runtime.block(
            step_id=STEP_COLLECT,
            reason=f"Target file does not exist: {target}",
            suggested_action="提供一个存在的代码文件路径后重新运行。",
        )

    decision = ToolPolicyChecker(
        [ToolPolicy(tool_name="file_read", risk_level=ToolRiskLevel.LOW, read_only=True, requires_approval=False)]
    ).check(ToolCallRequest(tool_name="file_read", step_id=STEP_COLLECT, mutating=False))
    runtime.trace_recorder.record(
        event_type=TraceEventType.TOOL_CALLED,
        task_id=runtime.contract.task_id,
        step_id=STEP_COLLECT,
        summary="Check file read policy.",
        data={"tool_name": "file_read", "allowed": decision.allowed, "reason": decision.reason},
        risk=decision.risk_level.value,
    )
    if not decision.allowed:
        return runtime.block(step_id=STEP_COLLECT, reason=decision.reason, suggested_action="调整 file_read 工具策略后重试。")

    code = target.read_text(encoding="utf-8")
    snapshot = CodeSnapshot(
        file_path=str(target),
        language=_guess_language(target),
        content=code,
        line_count=len(code.splitlines()),
    )
    runtime.save_artifact(
        ArtifactRecord(
            artifact_id="artifact:code-snapshot",
            artifact_type="code_snapshot",
            title="Code Snapshot",
            summary=f"{snapshot.language} file with {snapshot.line_count} lines.",
            path=str(target),
            schema_name="CodeSnapshotV1",
            producer_step_id=STEP_COLLECT,
            tags=["code", "review"],
            payload=snapshot.model_dump(mode="json"),
        )
    )
    runtime.pass_step(
        step_id=STEP_COLLECT,
        outputs_summary={"artifact_id": "artifact:code-snapshot", "line_count": snapshot.line_count},
    )
    return None


def _step_review_code(
    runtime: MinimalRuntime,
    *,
    target: Path,
    use_llm: bool,
    llm_provider: str | None,
    llm_model: str | None,
    llm_temperature: float,
    reviewer: CodeReviewer | None,
    force_blocked: bool,
    runtime_friction: list[str],
) -> BlockedReason | None:
    del target, force_blocked
    context = runtime.build_context(
        step_id=STEP_REVIEW,
        current_step="审查 CodeSnapshot，输出 ReviewReport artifact。",
        step_tags=["code", "review"],
        required_artifact_types=["code_snapshot"],
    )
    runtime.start_step(
        step_id=STEP_REVIEW,
        name="Review code",
        inputs_summary={"context_ready": context.ready, "context_items": len(context.items), "use_llm": use_llm},
    )
    if not context.ready:
        return runtime.block(
            step_id=STEP_REVIEW,
            reason=f"Context is not ready: {context.missing_required}",
            suggested_action="检查上游 CodeSnapshot artifact 是否生成。",
        )

    snapshot = cast(CodeSnapshot, runtime.consume_artifact(artifact_id="artifact:code-snapshot", schema_name="CodeSnapshotV1", consumer_step_id=STEP_REVIEW))
    context_summary = "; ".join(item.title for item in context.items[:6])
    start = time.perf_counter()
    if reviewer:
        try:
            llm_result = reviewer.review(file_path=snapshot.file_path, code=snapshot.content, context_summary=context_summary)
        except Exception as exc:
            return _block_reviewer_failure(runtime, error=exc)
        report = llm_result.report
        metrics = _reviewer_metrics(llm_result)
        runtime_friction.append("LLM reviewer 需要场景侧包装，Runtime Core 当前没有通用 LLM step adapter。")
    elif use_llm:
        from scenarios.code_review_mini.llm_reviewer import CodeReviewLLMReviewer

        try:
            llm_result = CodeReviewLLMReviewer(
                provider=llm_provider,
                model_name=llm_model,
                temperature=llm_temperature,
            ).review(
                file_path=snapshot.file_path,
                code=snapshot.content,
                context_summary=context_summary,
            )
        except Exception as exc:
            return _block_reviewer_failure(runtime, error=exc)
        report = llm_result.report
        metrics = _reviewer_metrics(llm_result)
        runtime_friction.append("真实 LLM 输出必须由场景 schema 做强校验，不能直接交给 Runtime Core。")
    else:
        report = deterministic_review(file_path=snapshot.file_path, code=snapshot.content)
        metrics = {
            "provider": "deterministic",
            "model": "rule-reviewer",
            "status": "success",
            "failure_reason": "",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "prompt_chars": 0,
            "response_chars": 0,
        }

    runtime.state.values["reviewer_metrics"] = metrics

    runtime.trace_recorder.record(
        event_type=TraceEventType.TOOL_CALLED,
        task_id=runtime.contract.task_id,
        step_id=STEP_REVIEW,
        summary="Run code reviewer.",
        data={
            "tool_name": "code_reviewer",
            **metrics,
            "finding_count": len(report.findings),
        },
        risk="medium" if use_llm or reviewer else "low",
        recoverable=metrics["status"] != "success",
    )
    runtime.save_artifact(
        ArtifactRecord(
            artifact_id="artifact:review-report",
            artifact_type="review_report",
            title="Code Review Report",
            summary=f"{report.risk_level} risk; findings={len(report.findings)}.",
            path="artifacts/code-review-mini/review_report.json",
            schema_name="ReviewReportV1",
            producer_step_id=STEP_REVIEW,
            tags=["code", "review", "patch"],
            payload=report.model_dump(mode="json"),
        )
    )
    runtime.pass_step(
        step_id=STEP_REVIEW,
        outputs_summary={"artifact_id": "artifact:review-report", "finding_count": len(report.findings), "risk_level": report.risk_level},
    )
    return None


def _step_propose_patch(
    runtime: MinimalRuntime,
    *,
    target: Path,
    use_llm: bool,
    llm_provider: str | None,
    llm_model: str | None,
    llm_temperature: float,
    reviewer: CodeReviewer | None,
    force_blocked: bool,
    runtime_friction: list[str],
) -> BlockedReason | None:
    del use_llm, llm_provider, llm_model, llm_temperature, reviewer
    context = runtime.build_context(
        step_id=STEP_PATCH,
        current_step="根据 ReviewReport 生成 PatchSuggestion artifact，但不直接修改文件。",
        step_tags=["patch", "review"],
        required_artifact_types=["review_report"],
    )
    runtime.start_step(
        step_id=STEP_PATCH,
        name="Propose patch",
        inputs_summary={"context_ready": context.ready, "context_items": len(context.items)},
    )
    if not context.ready:
        return runtime.block(
            step_id=STEP_PATCH,
            reason=f"Context is not ready: {context.missing_required}",
            suggested_action="检查上游 ReviewReport artifact 是否生成。",
        )

    tool_name = "patch_writer" if force_blocked else "patch_suggester"
    decision = ToolPolicyChecker(
        [
            ToolPolicy(tool_name="patch_suggester", risk_level=ToolRiskLevel.MEDIUM, read_only=True, requires_approval=False),
            ToolPolicy(tool_name="patch_writer", risk_level=ToolRiskLevel.HIGH, read_only=False, requires_approval=True),
        ]
    ).check(ToolCallRequest(tool_name=tool_name, step_id=STEP_PATCH, mutating=force_blocked, approved=False))
    runtime.trace_recorder.record(
        event_type=TraceEventType.TOOL_CALLED,
        task_id=runtime.contract.task_id,
        step_id=STEP_PATCH,
        summary="Check patch writer policy.",
        data={"tool_name": tool_name, "allowed": decision.allowed, "reason": decision.reason},
        risk=decision.risk_level.value,
    )
    if not decision.allowed:
        return runtime.block(
            step_id=STEP_PATCH,
            reason=decision.reason,
            suggested_action="人工确认是否允许生成或应用补丁；当前 demo 默认只输出建议。",
        )

    report = cast(ReviewReport, runtime.consume_artifact(artifact_id="artifact:review-report", schema_name="ReviewReportV1", consumer_step_id=STEP_PATCH))
    patch = PatchSuggestion(
        file_path=str(target),
        finding_refs=[finding.finding_id for finding in report.findings],
        summary="根据审查发现生成补丁建议；demo 不直接写文件。",
        suggested_changes=[finding.recommendation for finding in report.findings if finding.recommendation],
        requires_human_approval=True,
    )
    runtime.save_artifact(
        ArtifactRecord(
            artifact_id="artifact:patch-suggestion",
            artifact_type="patch_suggestion",
            title="Patch Suggestion",
            summary=f"{len(patch.suggested_changes)} suggested changes; human approval required.",
            path="artifacts/code-review-mini/patch_suggestion.json",
            schema_name="PatchSuggestionV1",
            producer_step_id=STEP_PATCH,
            tags=["patch", "review"],
            payload=patch.model_dump(mode="json"),
        )
    )
    runtime.pass_step(
        step_id=STEP_PATCH,
        outputs_summary={"artifact_id": "artifact:patch-suggestion", "suggested_change_count": len(patch.suggested_changes)},
    )
    runtime_friction.append("ToolPolicyChecker 可以表达审批要求，但当前场景仍需自行决定 blocked 还是只输出建议。")
    return None


def _result(
    runtime: MinimalRuntime,
    *,
    skipped_steps: list[str],
    blocked_reason: BlockedReason | None = None,
    runtime_friction: list[str] | None = None,
) -> CodeReviewMiniRunResult:
    finding_count = 0
    risk_level = ""
    reviewer = ""
    reviewer_metrics = dict(runtime.state.values.get("reviewer_metrics", {}))
    if "artifact:review-report" in runtime.state.artifact_ids:
        try:
            report = cast(ReviewReport, runtime.consume_artifact(artifact_id="artifact:review-report", schema_name="ReviewReportV1", consumer_step_id="final"))
            finding_count = len(report.findings)
            risk_level = report.risk_level
            reviewer = report.reviewer
        except Exception:
            pass

    return CodeReviewMiniRunResult(
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
        finding_count=finding_count,
        risk_level=risk_level,
        reviewer=reviewer,
        reviewer_provider=str(reviewer_metrics.get("provider", "")),
        reviewer_model=str(reviewer_metrics.get("model", "")),
        reviewer_status=str(reviewer_metrics.get("status", "")),
        reviewer_latency_ms=int(reviewer_metrics.get("latency_ms", 0) or 0),
        reviewer_prompt_chars=int(reviewer_metrics.get("prompt_chars", 0) or 0),
        reviewer_response_chars=int(reviewer_metrics.get("response_chars", 0) or 0),
        reviewer_failure_reason=str(reviewer_metrics.get("failure_reason", "")),
        runtime_friction=runtime_friction or [],
    )


def _guess_language(path: Path) -> str:
    if path.suffix == ".py":
        return "python"
    return path.suffix.lstrip(".") or "text"


def _reviewer_metrics(result: CodeReviewLLMResult) -> dict[str, Any]:
    return {
        "provider": result.provider,
        "model": result.model,
        "status": result.status,
        "failure_reason": result.failure_reason,
        "latency_ms": result.latency_ms,
        "prompt_chars": result.prompt_chars,
        "response_chars": result.response_chars,
    }


def _block_reviewer_failure(runtime: MinimalRuntime, *, error: Exception) -> BlockedReason:
    reason = f"code reviewer failed: {type(error).__name__}: {error}"
    runtime.state.values["reviewer_metrics"] = {
        "provider": "unknown",
        "model": "unknown",
        "status": "failed",
        "failure_reason": reason,
        "latency_ms": 0,
        "prompt_chars": 0,
        "response_chars": 0,
    }
    runtime.trace_recorder.record(
        event_type=TraceEventType.TOOL_CALLED,
        task_id=runtime.contract.task_id,
        step_id=STEP_REVIEW,
        summary="Code reviewer failed.",
        data={"tool_name": "code_reviewer", **runtime.state.values["reviewer_metrics"]},
        risk="medium",
        recoverable=True,
    )
    return runtime.block(
        step_id=STEP_REVIEW,
        reason=reason,
        suggested_action="检查 LLM provider 配置、网络、模型 JSON 输出格式，或改用离线 reviewer。",
    )
