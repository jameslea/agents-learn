from __future__ import annotations

import re
from time import perf_counter
from pathlib import Path
from typing import Any

from runtime.artifacts import (
    DocumentQualityArtifact,
    EvaluationArtifact,
    HumanDecision,
    HumanReviewDecisionArtifact,
    HumanReviewRequestArtifact,
    ImprovementPlanArtifact,
    IssueArtifact,
    IssueSeverity,
    LLMReviewArtifact,
)
from runtime.contracts import Budget, HumanReviewPolicy, RiskLevel, TaskContract, TaskType
from runtime.evaluation import EvaluationResult, RuntimeFinalStatus
from runtime.manifest import RuntimeRunManifest, RuntimeRunManifestStore
from runtime.state import utc_now
from runtime.tools import GovernedToolRunner, ToolNeedsHumanReview, ToolPolicy, ToolRegistry, ToolSpec
from runtime.trace import RuntimeTraceRecorder, TraceEventType
from scenarios.report_governance.llm_reviewer import LLMReviewResult, ReportLLMReviewer


DEFAULT_THRESHOLDS = {
    "min_chars": 2500,
    "min_headings": 5,
    "min_references": 5,
    "min_lists": 5,
    "max_thin_sections": 2,
    "min_score": 0.7,
}


def run_report_governance(
    document_path: Path,
    *,
    trace_dir: Path,
    thresholds: dict[str, int | float] | None = None,
    request_patch: bool = False,
    approve_high_risk: bool = False,
    patch_output_dir: Path | None = None,
    llm_review: bool = False,
    reviewer: Any | None = None,
) -> EvaluationResult:
    """Run a standalone runtime-native report governance task."""
    active_thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    contract = _contract(document_path, active_thresholds, request_patch=request_patch, llm_review=llm_review)
    trace_path = trace_dir / f"{document_path.stem}.report_governance.runtime.jsonl"
    trace = RuntimeTraceRecorder(trace_path)
    manifest_store = RuntimeRunManifestStore(
        trace_dir.parent / "manifests" / f"{document_path.stem}.report_governance.runtime.manifest.json"
    )
    manifest = RuntimeRunManifest(
        adapter_id="report_governance",
        task_id=contract.task_id,
        trace_path=str(trace_path),
        checkpoint_path="",
        artifact_root=str((trace_dir.parent / "reports").resolve()),
        metadata={"request_patch": request_patch, "llm_review": llm_review},
    )
    manifest_store.save(manifest)
    trace.record(TraceEventType.TASK_STARTED, contract)

    registry = _registry(reviewer=reviewer)
    safe_patch_output_dir = patch_output_dir or trace_dir.parent / "reports"
    policy = ToolPolicy.from_contract(
        contract,
        allowed_read_dirs=[str(document_path.resolve().parent)],
        allowed_write_dirs=[str(safe_patch_output_dir.resolve())],
        allow_network=llm_review,
    )
    if approve_high_risk:
        policy.allow_high_risk = True
        policy.approved_tools = ["report.write_improvement_patch"]
    runner = GovernedToolRunner(
        registry=registry,
        policy=policy,
        trace=trace,
        task_id=contract.task_id,
    )

    metrics = runner.call("report.read_and_measure", document_path=str(document_path))
    issues = runner.call("report.detect_issues", metrics=metrics, thresholds=active_thresholds)
    plan = runner.call("report.create_improvement_plan", issues=issues)
    patch_result: dict[str, Any] | None = None
    llm_review_result: dict[str, Any] | None = None

    quality_artifact = DocumentQualityArtifact(
        artifact_id=f"{contract.task_id}:quality",
        task_id=contract.task_id,
        source="report_governance",
        document_path=str(document_path),
        chars=metrics["chars"],
        headings=metrics["headings"],
        lists=metrics["lists"],
        tables=metrics["tables"],
        references=metrics["references"],
        evidence_boundary_mentions=metrics["evidence_boundary_mentions"],
        avg_section_chars=metrics["avg_section_chars"],
        thin_sections=metrics["thin_sections"],
        metrics=metrics,
    )
    issue_artifacts = [
        IssueArtifact(
            artifact_id=f"{contract.task_id}:issue:{issue['issue_id']}",
            task_id=contract.task_id,
            source="report_governance",
            issue_id=issue["issue_id"],
            severity=IssueSeverity(issue["severity"]),
            category=issue["category"],
            message=issue["message"],
            evidence=issue["evidence"],
            recommendation=issue["recommendation"],
        )
        for issue in issues
    ]
    plan_artifact = ImprovementPlanArtifact(
        artifact_id=f"{contract.task_id}:plan",
        task_id=contract.task_id,
        source="report_governance",
        plan_id=f"{document_path.stem}:plan",
        summary=plan["summary"],
        steps=plan["steps"],
        issue_ids=plan["issue_ids"],
    )

    trace.record(TraceEventType.ARTIFACT_CREATED, quality_artifact)
    for artifact in issue_artifacts:
        trace.record(TraceEventType.ARTIFACT_CREATED, artifact)
    trace.record(TraceEventType.ARTIFACT_CREATED, plan_artifact)

    if llm_review:
        llm_review_result = runner.call(
            "report.llm_review",
            document_path=str(document_path),
            metrics=metrics,
            issues=issues,
        )
        llm_review_artifact = LLMReviewArtifact(
            artifact_id=f"{contract.task_id}:llm_review",
            task_id=contract.task_id,
            source="report_governance",
            reviewer_id=f"{document_path.stem}:llm_review",
            provider=llm_review_result["provider"],
            model=llm_review_result["model"],
            verdict=llm_review_result["verdict"],
            confidence=llm_review_result["confidence"],
            strengths=llm_review_result["strengths"],
            concerns=llm_review_result["concerns"],
            suggested_actions=llm_review_result["suggested_actions"],
            latency_ms=llm_review_result["latency_ms"],
            status=llm_review_result["status"],
            failure_reason=llm_review_result.get("failure_reason", ""),
            raw_text=llm_review_result.get("raw_text", ""),
        )
        trace.record(TraceEventType.ARTIFACT_CREATED, llm_review_artifact)

    if request_patch:
        output_dir = safe_patch_output_dir
        request_id = f"{contract.task_id}:review:write_patch"
        if approve_high_risk:
            decision_artifact = HumanReviewDecisionArtifact(
                artifact_id=f"{contract.task_id}:human_decision:write_patch",
                task_id=contract.task_id,
                source="report_governance",
                request_id=request_id,
                decision=HumanDecision.APPROVED,
                rationale="CLI approved high-risk patch artifact writing.",
            )
            trace.record(TraceEventType.HUMAN_REVIEW_DECIDED, decision_artifact)
            trace.record(TraceEventType.ARTIFACT_CREATED, decision_artifact)
        try:
            patch_result = runner.call(
                "report.write_improvement_patch",
                document_path=str(document_path),
                plan=plan,
                output_dir=str(output_dir),
            )
        except ToolNeedsHumanReview as error:
            review_artifact = HumanReviewRequestArtifact(
                artifact_id=f"{contract.task_id}:human_review:write_patch",
                task_id=contract.task_id,
                source="report_governance",
                request_id=request_id,
                tool_name=error.decision.tool_name,
                reason=error.decision.reason,
                requested_action="Write an improvement patch artifact to the report output directory.",
                risk_level=error.decision.risk_level,
                inputs_summary=error.decision.inputs_summary,
            )
            trace.record(TraceEventType.ARTIFACT_CREATED, review_artifact)
            result = _needs_human_result(
                contract,
                metrics,
                issues,
                active_thresholds,
                review_artifact,
                llm_review_result=llm_review_result,
            )
            eval_artifact = _evaluation_artifact(contract, result)
            trace.record(TraceEventType.EVALUATION_RUN, eval_artifact)
            trace.record(TraceEventType.TASK_FINISHED, result)
            _finish_manifest(manifest_store, manifest, result, artifact_count=3 + len(issue_artifacts))
            return result

    result = _evaluate(
        contract,
        metrics,
        issues,
        active_thresholds,
        patch_result=patch_result,
        llm_review_result=llm_review_result,
    )
    eval_artifact = EvaluationArtifact(
        artifact_id=f"{contract.task_id}:evaluation",
        task_id=contract.task_id,
        source="report_governance",
        status=result.status.value,
        score=result.score,
        metrics=result.metrics,
        reason=result.reason,
    )

    trace.record(TraceEventType.EVALUATION_RUN, eval_artifact)
    trace.record(TraceEventType.TASK_FINISHED, result)
    artifact_count = 2 + len(issue_artifacts)
    if llm_review_result:
        artifact_count += 1
    if patch_result:
        artifact_count += 1
    _finish_manifest(manifest_store, manifest, result, artifact_count=artifact_count)
    return result


def _contract(
    document_path: Path,
    thresholds: dict[str, int | float],
    *,
    request_patch: bool = False,
    llm_review: bool = False,
) -> TaskContract:
    allowed_tools = [
        "report.read_and_measure",
        "report.detect_issues",
        "report.create_improvement_plan",
    ]
    expected_outputs = [
        "DocumentQualityArtifact",
        "IssueArtifact",
        "ImprovementPlanArtifact",
        "EvaluationResult",
    ]
    if request_patch:
        allowed_tools.append("report.write_improvement_patch")
        expected_outputs.extend(["ToolDecisionArtifact", "HumanReviewRequestArtifact"])
    if llm_review:
        allowed_tools.append("report.llm_review")
        expected_outputs.append("LLMReviewArtifact")

    return TaskContract(
        task_id=f"report_governance:{document_path.stem}",
        task_type=TaskType.DOCUMENT_GOVERNANCE,
        goal=f"Analyze markdown report quality and produce actionable governance artifacts for {document_path.name}.",
        inputs={"document_path": str(document_path), "thresholds": thresholds},
        expected_outputs=expected_outputs,
        success_criteria=[
            f"quality score >= {thresholds['min_score']}",
            "no high-severity issues",
            "improvement plan is generated",
        ],
        risk_level=RiskLevel.MEDIUM if request_patch else RiskLevel.LOW,
        allowed_tools=allowed_tools,
        budget=Budget(
            max_attempts=1,
            timeout_seconds=15.0 if llm_review else 5.0,
            max_tool_calls=_max_tool_calls(request_patch=request_patch, llm_review=llm_review),
        ),
        human_review_policy=HumanReviewPolicy.ON_HIGH_RISK if request_patch else HumanReviewPolicy.NEVER,
    )


def _max_tool_calls(*, request_patch: bool, llm_review: bool) -> int:
    calls = 3
    if request_patch:
        calls += 1
    if llm_review:
        calls += 1
    return calls


def _registry(reviewer: Any | None = None) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="report.read_and_measure",
            description="Read a markdown report and calculate deterministic quality metrics.",
            risk_level=RiskLevel.LOW,
            input_schema="{document_path: str}",
            output_schema="dict[str, metric]",
            max_calls=1,
            read_path_args=["document_path"],
        ),
        _read_and_measure,
    )
    registry.register(
        ToolSpec(
            name="report.detect_issues",
            description="Convert quality metrics into structured governance issues.",
            risk_level=RiskLevel.LOW,
            input_schema="{metrics: dict, thresholds: dict}",
            output_schema="list[issue]",
            max_calls=1,
        ),
        _detect_issues,
    )
    registry.register(
        ToolSpec(
            name="report.create_improvement_plan",
            description="Create an ordered improvement plan from issue artifacts.",
            risk_level=RiskLevel.LOW,
            input_schema="{issues: list}",
            output_schema="dict",
            max_calls=1,
        ),
        _create_improvement_plan,
    )
    registry.register(
        ToolSpec(
            name="report.write_improvement_patch",
            description="Write a proposed markdown improvement patch artifact.",
            risk_level=RiskLevel.HIGH,
            input_schema="{document_path: str, plan: dict, output_dir: str}",
            output_schema="dict",
            approval_required=True,
            max_calls=1,
            write_path_args=["output_dir"],
        ),
        _write_improvement_patch,
    )
    registry.register(
        ToolSpec(
            name="report.llm_review",
            description="Ask an LLM reviewer for auxiliary report quality feedback.",
            risk_level=RiskLevel.MEDIUM,
            input_schema="{document_path: str, metrics: dict, issues: list}",
            output_schema="dict",
            max_calls=1,
            read_path_args=["document_path"],
            requires_network=True,
        ),
        _build_llm_review_handler(reviewer),
    )
    return registry


def _read_and_measure(document_path: str) -> dict[str, Any]:
    path = Path(document_path)
    markdown = path.read_text(encoding="utf-8")
    body = markdown.split("## 参考资料", 1)[0]
    section_lengths = _section_lengths(body)
    urls = re.findall(r"https?://[^\s)>\]]+", markdown)
    return {
        "document_path": str(path),
        "chars": len(markdown),
        "headings": len(re.findall(r"^#{1,6}\s+", markdown, flags=re.MULTILINE)),
        "lists": len(re.findall(r"^\s*[-*]\s+", markdown, flags=re.MULTILINE)),
        "tables": _table_count(markdown),
        "references": len(urls),
        "evidence_boundary_mentions": markdown.count("证据边界") + markdown.count("局限") + markdown.count("不确定"),
        "avg_section_chars": round(sum(section_lengths) / len(section_lengths), 1) if section_lengths else 0.0,
        "thin_sections": sum(1 for length in section_lengths if length < 180),
        "urls": urls,
    }


def _detect_issues(metrics: dict[str, Any], thresholds: dict[str, int | float]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    _append_if(
        issues,
        metrics["chars"] < thresholds["min_chars"],
        "high",
        "coverage",
        f"文档长度 {metrics['chars']} 低于最低要求 {thresholds['min_chars']}。",
        "全文字符数不足",
        "补充背景、分析过程、证据解释和结论边界。",
    )
    _append_if(
        issues,
        metrics["headings"] < thresholds["min_headings"],
        "medium",
        "structure",
        f"标题数量 {metrics['headings']} 低于最低要求 {thresholds['min_headings']}。",
        "章节层次不足",
        "拆出背景、方法、发现、风险、建议和参考资料等稳定章节。",
    )
    _append_if(
        issues,
        metrics["references"] < thresholds["min_references"],
        "high",
        "evidence",
        f"引用数量 {metrics['references']} 低于最低要求 {thresholds['min_references']}。",
        "外部证据不足",
        "补充一手来源、官方文档、论文或可验证数据链接。",
    )
    _append_if(
        issues,
        metrics["lists"] < thresholds["min_lists"],
        "low",
        "readability",
        f"列表数量 {metrics['lists']} 低于建议值 {thresholds['min_lists']}。",
        "扫描性不足",
        "将关键发现、风险和行动项整理成列表。",
    )
    _append_if(
        issues,
        metrics["thin_sections"] > thresholds["max_thin_sections"],
        "medium",
        "depth",
        f"薄弱章节数量 {metrics['thin_sections']} 高于上限 {thresholds['max_thin_sections']}。",
        "部分章节只有标题或短段落",
        "合并空洞章节，或为每节补充论据、例子和明确结论。",
    )
    _append_if(
        issues,
        metrics["evidence_boundary_mentions"] == 0,
        "medium",
        "governance",
        "文档没有明确说明证据边界、局限或不确定性。",
        "缺少证据边界声明",
        "增加局限性、适用范围和未验证假设说明。",
    )
    return [{**issue, "issue_id": f"I{index + 1:02d}"} for index, issue in enumerate(issues)]


def _create_improvement_plan(issues: list[dict[str, str]]) -> dict[str, Any]:
    sorted_issues = sorted(issues, key=lambda item: {"high": 0, "medium": 1, "low": 2}[item["severity"]])
    steps = [
        f"[{issue['severity']}] {issue['recommendation']}"
        for issue in sorted_issues
    ]
    if not steps:
        steps = ["当前文档满足最小治理阈值；后续可增加人工审阅和事实核查。"]
    return {
        "summary": f"发现 {len(issues)} 个治理问题，已按严重程度生成改进顺序。",
        "steps": steps,
        "issue_ids": [issue["issue_id"] for issue in sorted_issues],
    }


def _evaluate(
    contract: TaskContract,
    metrics: dict[str, Any],
    issues: list[dict[str, str]],
    thresholds: dict[str, int | float],
    *,
    patch_result: dict[str, Any] | None = None,
    llm_review_result: dict[str, Any] | None = None,
) -> EvaluationResult:
    high_issues = [issue for issue in issues if issue["severity"] == "high"]
    score = _score(metrics, issues, thresholds)
    passed = score >= thresholds["min_score"] and not high_issues
    return EvaluationResult(
        task_id=contract.task_id,
        task_name=Path(metrics["document_path"]).name,
        status=RuntimeFinalStatus.PASSED if passed else RuntimeFinalStatus.FAILED,
        score=score,
        attempts=1,
        reason=(
            f"Document governance score {score:.3f}; issues={len(issues)}, high={len(high_issues)}."
        ),
        metrics={
            **metrics,
            "issue_count": len(issues),
            "high_issue_count": len(high_issues),
            "thresholds": thresholds,
            "patch_path": patch_result["patch_path"] if patch_result else None,
            "human_review_required": False,
            "llm_review": _llm_review_metrics(llm_review_result),
        },
    )


def _needs_human_result(
    contract: TaskContract,
    metrics: dict[str, Any],
    issues: list[dict[str, str]],
    thresholds: dict[str, int | float],
    review_artifact: HumanReviewRequestArtifact,
    *,
    llm_review_result: dict[str, Any] | None = None,
) -> EvaluationResult:
    score = _score(metrics, issues, thresholds)
    return EvaluationResult(
        task_id=contract.task_id,
        task_name=Path(metrics["document_path"]).name,
        status=RuntimeFinalStatus.NEEDS_HUMAN,
        score=score,
        attempts=1,
        reason=f"Report governance needs human review before high-risk tool execution: {review_artifact.tool_name}.",
        metrics={
            **metrics,
            "issue_count": len(issues),
            "high_issue_count": sum(1 for issue in issues if issue["severity"] == "high"),
            "thresholds": thresholds,
            "human_review_required": True,
            "review_request_id": review_artifact.request_id,
            "blocked_tool": review_artifact.tool_name,
            "patch_path": None,
            "llm_review": _llm_review_metrics(llm_review_result),
        },
    )


def _evaluation_artifact(contract: TaskContract, result: EvaluationResult) -> EvaluationArtifact:
    return EvaluationArtifact(
        artifact_id=f"{contract.task_id}:evaluation",
        task_id=contract.task_id,
        source="report_governance",
        status=result.status.value,
        score=result.score,
        metrics=result.metrics,
        reason=result.reason,
    )


def _write_improvement_patch(document_path: str, plan: dict[str, Any], output_dir: str) -> dict[str, Any]:
    source_path = Path(document_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    patch_path = output_path / f"{source_path.stem}.improvement_patch.md"
    lines = [
        f"# {source_path.name} 改进补丁建议",
        "",
        "该文件由 Runtime 高风险写入工具生成，仅作为建议产物，不会修改原始文档。",
        "",
        f"## 摘要",
        "",
        str(plan["summary"]),
        "",
        "## 建议步骤",
        "",
    ]
    lines.extend(f"- {step}" for step in plan["steps"])
    patch_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "patch_path": str(patch_path),
        "summary": plan["summary"],
        "step_count": len(plan["steps"]),
    }


def _build_llm_review_handler(reviewer: Any | None):
    def _llm_review(document_path: str, metrics: dict[str, Any], issues: list[dict[str, str]]) -> dict[str, Any]:
        path = Path(document_path)
        markdown = path.read_text(encoding="utf-8")
        active_reviewer = reviewer or ReportLLMReviewer()
        started = perf_counter()
        try:
            result = active_reviewer.review(markdown=markdown, metrics=metrics, issues=issues)
        except Exception as error:
            latency_ms = round((perf_counter() - started) * 1000, 3)
            return {
                "provider": getattr(active_reviewer, "provider", "injected"),
                "model": getattr(active_reviewer, "model", "injected"),
                "verdict": "caution",
                "confidence": 0.0,
                "strengths": [],
                "concerns": [f"LLM reviewer failed: {error}"],
                "suggested_actions": ["保留确定性评估结果，并在需要时重试 LLM reviewer。"],
                "latency_ms": latency_ms,
                "status": "failed",
                "failure_reason": str(error),
                "raw_text": "",
            }
        latency_ms = round((perf_counter() - started) * 1000, 3)
        if isinstance(result, LLMReviewResult):
            review = result
        elif isinstance(result, dict):
            review = LLMReviewResult.model_validate(result)
        else:
            review = LLMReviewResult.model_validate(result.model_dump())
        return {
            "provider": getattr(active_reviewer, "provider", "injected"),
            "model": getattr(active_reviewer, "model", "injected"),
            "verdict": review.verdict,
            "confidence": review.confidence,
            "strengths": review.strengths,
            "concerns": review.concerns,
            "suggested_actions": review.suggested_actions,
            "latency_ms": latency_ms,
            "status": "success",
            "failure_reason": "",
            "raw_text": review.raw_text,
        }

    return _llm_review


def _llm_review_metrics(llm_review_result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not llm_review_result:
        return None
    return {
        "provider": llm_review_result["provider"],
        "model": llm_review_result["model"],
        "verdict": llm_review_result["verdict"],
        "confidence": llm_review_result["confidence"],
        "concern_count": len(llm_review_result["concerns"]),
        "suggested_action_count": len(llm_review_result["suggested_actions"]),
        "latency_ms": llm_review_result["latency_ms"],
        "status": llm_review_result["status"],
        "failure_reason": llm_review_result.get("failure_reason", ""),
    }


def _finish_manifest(
    manifest_store: RuntimeRunManifestStore,
    manifest: RuntimeRunManifest,
    result: EvaluationResult,
    *,
    artifact_count: int,
) -> None:
    manifest.status = result.status.value
    manifest.finished_at = utc_now()
    manifest.metadata.update(
        {
            "score": result.score,
            "reason": result.reason,
            "artifact_count": artifact_count,
        }
    )
    manifest_store.save(manifest)


def _score(metrics: dict[str, Any], issues: list[dict[str, str]], thresholds: dict[str, int | float]) -> float:
    base = 0.0
    base += min(0.25, 0.25 * metrics["chars"] / thresholds["min_chars"])
    base += min(0.20, 0.20 * metrics["headings"] / thresholds["min_headings"])
    base += min(0.20, 0.20 * metrics["references"] / thresholds["min_references"])
    base += min(0.15, 0.15 * metrics["lists"] / thresholds["min_lists"])
    base += 0.10 if metrics["evidence_boundary_mentions"] > 0 else 0.0
    base += 0.10 if metrics["thin_sections"] <= thresholds["max_thin_sections"] else 0.0
    penalty = sum({"high": 0.12, "medium": 0.06, "low": 0.02}[issue["severity"]] for issue in issues)
    return round(max(0.0, min(1.0, base - penalty)), 3)


def _append_if(
    issues: list[dict[str, str]],
    condition: bool,
    severity: str,
    category: str,
    message: str,
    evidence: str,
    recommendation: str,
) -> None:
    if condition:
        issues.append(
            {
                "severity": severity,
                "category": category,
                "message": message,
                "evidence": evidence,
                "recommendation": recommendation,
            }
        )


def _section_lengths(markdown: str) -> list[int]:
    sections: list[int] = []
    current: list[str] = []
    for line in markdown.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            if current:
                sections.append(len("\n".join(current).strip()))
            current = []
            continue
        current.append(line)
    if current:
        sections.append(len("\n".join(current).strip()))
    return [length for length in sections if length > 0]


def _table_count(markdown: str) -> int:
    lines = markdown.splitlines()
    return sum(
        1
        for index in range(len(lines) - 1)
        if lines[index].strip().startswith("|") and set(lines[index + 1].strip()) <= {"|", "-", ":", " "}
    )
