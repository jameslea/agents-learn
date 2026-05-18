from __future__ import annotations

import sys
from pathlib import Path

from runtime.agent_adapter import AdapterRunContext, AgentRunResult, run_agent_adapter
from runtime.artifacts import ContentReportArtifact, ImprovementPlanArtifact
from runtime.contracts import Budget, HumanReviewPolicy, RiskLevel, TaskContract, TaskType
from runtime.evaluation import EvaluationResult, RuntimeFinalStatus


PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_DIR.parents[1]
CONTENT_PROJECT_DIR = REPO_ROOT / "practice-projects" / "02-content-creation-team"
DEFAULT_REPORT = CONTENT_PROJECT_DIR / "final_report.md"

if str(CONTENT_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(CONTENT_PROJECT_DIR))

from utils.report_evaluation import evaluate_report_quality  # noqa: E402


def run_content_team_report(
    report_path: Path | None = None,
    *,
    trace_dir: Path,
    passing_score: int = 70,
) -> EvaluationResult:
    """Evaluate an existing content-team report through runtime semantics."""
    adapter = ContentTeamReportAdapter(
        report_path=report_path or DEFAULT_REPORT,
        passing_score=passing_score,
    )
    return run_agent_adapter(adapter, trace_dir=trace_dir)


class ContentTeamReportAdapter:
    """Runtime adapter for project B: content creation team."""

    adapter_id = "content_team_adapter"
    trace_name = "content_team.runtime.jsonl"

    def __init__(self, *, report_path: Path, passing_score: int) -> None:
        self.report_path = report_path
        self.passing_score = passing_score

    def describe_contract(self) -> TaskContract:
        return _contract(self.report_path, self.passing_score)

    def run(self, context: AdapterRunContext) -> AgentRunResult:
        context.record_tool_call(
            "content_team.evaluate_report_quality",
            {"report_path": str(self.report_path), "passing_score": self.passing_score},
        )
        contract = context.contract
        path = self.report_path

        markdown = path.read_text(encoding="utf-8")
        metrics = evaluate_report_quality(markdown, name=path.name)
        status = RuntimeFinalStatus.PASSED if metrics.total_score >= self.passing_score else RuntimeFinalStatus.FAILED
        artifact = ContentReportArtifact(
            artifact_id=f"{contract.task_id}:content_report",
            task_id=contract.task_id,
            source=self.adapter_id,
            report_path=str(path),
            total_score=metrics.total_score,
            editorial_score=metrics.editorial_score,
            evidence_score=metrics.evidence_score,
            issues=metrics.issues,
            strengths=metrics.strengths,
            metadata={
                "units": metrics.units,
                "main_sections": metrics.main_sections,
                "subsections": metrics.subsections,
                "references": metrics.references,
            },
        )
        improvement_plan = _build_improvement_plan(contract.task_id, metrics)
        result = EvaluationResult(
            task_id=contract.task_id,
            task_name=path.name,
            status=status,
            score=round(metrics.total_score / 100, 3),
            attempts=1,
            reason=f"Report quality score {metrics.total_score}; threshold {self.passing_score}.",
            metrics={
                **metrics.to_dict(),
                "improvement_plan": {
                    "plan_id": improvement_plan.plan_id,
                    "summary": improvement_plan.summary,
                    "steps": improvement_plan.steps,
                    "issue_ids": improvement_plan.issue_ids,
                },
            },
        )
        return AgentRunResult(evaluation=result, artifacts=[artifact, improvement_plan])


def _contract(path: Path, passing_score: int) -> TaskContract:
    return TaskContract(
        task_id="content_team:report_quality",
        task_type=TaskType.CONTENT_GENERATION,
        goal="Evaluate a generated content-team report with deterministic quality metrics.",
        inputs={"report_path": str(path)},
        expected_outputs=["ContentReportArtifact", "ImprovementPlanArtifact", "EvaluationResult"],
        success_criteria=[f"report quality score >= {passing_score}", "issues are structured"],
        risk_level=RiskLevel.LOW,
        allowed_tools=["content_team.evaluate_report_quality"],
        budget=Budget(max_attempts=1, timeout_seconds=5.0),
        human_review_policy=HumanReviewPolicy.NEVER,
    )


def _build_improvement_plan(task_id: str, metrics) -> ImprovementPlanArtifact:
    issue_ids = [f"B{index + 1:02d}" for index, _issue in enumerate(metrics.issues)]
    steps = [_recommendation_for_issue(issue) for issue in metrics.issues]
    if not steps:
        steps = ["当前报告达到质量阈值；后续可进行人工事实核查和表达润色。"]

    return ImprovementPlanArtifact(
        artifact_id=f"{task_id}:improvement_plan",
        task_id=task_id,
        source="content_team_adapter",
        plan_id="content_team:report_quality:improvement_plan",
        summary=f"基于 B 项目确定性质量评估生成 {len(metrics.issues)} 条改进建议。",
        steps=steps,
        issue_ids=issue_ids,
        metadata={
            "total_score": metrics.total_score,
            "editorial_score": metrics.editorial_score,
            "evidence_score": metrics.evidence_score,
        },
    )


def _recommendation_for_issue(issue: str) -> str:
    if "主章节数量" in issue:
        return f"{issue} 调整一级结构，保留 8-10 个主章节，避免过粗或过碎。"
    if "三级小节数量" in issue:
        return f"{issue} 为关键章节补充稳定三级小节，覆盖背景、案例、分析、风险和建议。"
    if "列表项数量" in issue:
        return f"{issue} 将关键发现、案例对比和行动建议整理成适量列表，提升扫描性。"
    if "小节平均厚度" in issue or "过薄小节" in issue:
        return f"{issue} 合并空洞小节，或补充论据、案例、数据解释和明确结论。"
    if "成功/挑战/分析节奏" in issue:
        return f"{issue} 在案例章节中补齐成功做法、失败/挑战和横纵向分析。"
    if "后半部分" in issue:
        return f"{issue} 为后半部分补充内部结构，避免后段变成松散总结。"
    if "引用来源" in issue:
        return f"{issue} 补充官方文档、公开报告、论文或可验证数据来源。"
    if "一手/准一手来源" in issue:
        return f"{issue} 优先替换为官方、论文、监管、财报或厂商原始资料。"
    if "综合案例" in issue or "公开案例" in issue:
        return f"{issue} 明确案例来源、适用范围和证据边界，避免把综合推断写成事实。"
    return f"{issue} 根据该问题补充具体内容、证据和结构修正。"
