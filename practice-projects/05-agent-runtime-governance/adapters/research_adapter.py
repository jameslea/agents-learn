from __future__ import annotations

import re
from pathlib import Path

from runtime.agent_adapter import AdapterRunContext, AgentRunResult, run_agent_adapter
from runtime.artifacts import ResearchReportArtifact
from runtime.contracts import Budget, HumanReviewPolicy, RiskLevel, TaskContract, TaskType
from runtime.evaluation import EvaluationResult, RuntimeFinalStatus


PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_DIR.parents[1]
RESEARCH_PROJECT_DIR = REPO_ROOT / "practice-projects" / "03-autonomous-research"
DEFAULT_REPORT = RESEARCH_PROJECT_DIR / "final_research_report.md"


def run_research_report(
    report_path: Path | None = None,
    *,
    trace_dir: Path,
    min_chars: int = 3000,
    min_headings: int = 4,
) -> EvaluationResult:
    """Evaluate an existing autonomous research report without LLM calls."""
    adapter = ResearchReportAdapter(
        report_path=report_path or DEFAULT_REPORT,
        min_chars=min_chars,
        min_headings=min_headings,
    )
    return run_agent_adapter(adapter, trace_dir=trace_dir)


class ResearchReportAdapter:
    """Runtime adapter for project C: autonomous research."""

    adapter_id = "research_adapter"
    trace_name = "autonomous_research.runtime.jsonl"

    def __init__(self, *, report_path: Path, min_chars: int, min_headings: int) -> None:
        self.report_path = report_path
        self.min_chars = min_chars
        self.min_headings = min_headings

    def describe_contract(self) -> TaskContract:
        return _contract(self.report_path, self.min_chars, self.min_headings)

    def run(self, context: AdapterRunContext) -> AgentRunResult:
        context.record_tool_call(
            "research.static_report_metrics",
            {
                "report_path": str(self.report_path),
                "min_chars": self.min_chars,
                "min_headings": self.min_headings,
            },
        )
        contract = context.contract
        path = self.report_path

        markdown = path.read_text(encoding="utf-8")
        metrics = _metrics(markdown)
        passed = metrics["chars"] >= self.min_chars and metrics["headings"] >= self.min_headings
        status = RuntimeFinalStatus.PASSED if passed else RuntimeFinalStatus.FAILED
        artifact = ResearchReportArtifact(
            artifact_id=f"{contract.task_id}:research_report",
            task_id=contract.task_id,
            source=self.adapter_id,
            report_path=str(path),
            chars=metrics["chars"],
            headings=metrics["headings"],
            bullets=metrics["bullets"],
            tables=metrics["tables"],
            risk_terms=metrics["risk_terms"],
        )
        score = min(1.0, round((metrics["chars"] / self.min_chars + metrics["headings"] / self.min_headings) / 2, 3))
        result = EvaluationResult(
            task_id=contract.task_id,
            task_name=path.name,
            status=status,
            score=score,
            attempts=1,
            reason=f"Research report chars={metrics['chars']}, headings={metrics['headings']}.",
            metrics=metrics,
        )
        return AgentRunResult(evaluation=result, artifacts=[artifact])



def _metrics(markdown: str) -> dict:
    risk_terms = {
        "信息缺口": markdown.count("信息缺口"),
        "冲突": markdown.count("冲突"),
        "局限": markdown.count("局限"),
        "成本": markdown.count("成本"),
        "延迟": markdown.count("延迟"),
    }
    return {
        "chars": len(markdown),
        "headings": len(re.findall(r"^#{1,6}\s+", markdown, flags=re.MULTILINE)),
        "bullets": len(re.findall(r"^\s*[-*]\s+", markdown, flags=re.MULTILINE)),
        "tables": sum(1 for line in markdown.splitlines() if line.strip().startswith("|")),
        "risk_terms": risk_terms,
    }


def _contract(path: Path, min_chars: int, min_headings: int) -> TaskContract:
    return TaskContract(
        task_id="autonomous_research:final_report",
        task_type=TaskType.RESEARCH,
        goal="Evaluate an autonomous research final report with deterministic runtime metrics.",
        inputs={"report_path": str(path)},
        expected_outputs=["ResearchReportArtifact", "EvaluationResult"],
        success_criteria=[f"chars >= {min_chars}", f"headings >= {min_headings}"],
        risk_level=RiskLevel.LOW,
        allowed_tools=["research.static_report_metrics"],
        budget=Budget(max_attempts=1, timeout_seconds=5.0),
        human_review_policy=HumanReviewPolicy.NEVER,
    )
