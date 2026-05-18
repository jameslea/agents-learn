from __future__ import annotations

import json

from adapters.content_team_adapter import ContentTeamReportAdapter, DEFAULT_REPORT, run_content_team_report
from adapters.rag_adapter import RAGReadinessAdapter, run_rag_readiness
from adapters.research_adapter import run_research_report
from runtime.agent_adapter import run_agent_adapter
from runtime.evaluation import RuntimeFinalStatus


def test_agent_adapter_protocol_runs_project_adapter(tmp_path) -> None:
    adapter = RAGReadinessAdapter()

    result = run_agent_adapter(adapter, trace_dir=tmp_path)

    assert result.task_id == "rag:static_readiness"
    events = _read_trace_events(tmp_path / "knowledge_base_qa.runtime.jsonl")
    assert [event["event"] for event in events] == [
        "task_started",
        "tool_called",
        "artifact_created",
        "evaluation_run",
        "task_finished",
    ]


def test_rag_adapter_static_readiness(tmp_path) -> None:
    result = run_rag_readiness(trace_dir=tmp_path)

    assert result.status == RuntimeFinalStatus.PASSED
    assert result.metrics["data_file_count"] >= 3
    assert result.metrics["expected_terms_found"]["long_doc_secret"] is True
    assert (tmp_path / "knowledge_base_qa.runtime.jsonl").exists()


def test_content_team_adapter_reports_deterministic_quality(tmp_path) -> None:
    result = run_content_team_report(trace_dir=tmp_path, passing_score=70)

    assert result.task_id == "content_team:report_quality"
    assert "total_score" in result.metrics
    assert "improvement_plan" in result.metrics
    assert result.metrics["improvement_plan"]["steps"]
    assert result.status in {RuntimeFinalStatus.PASSED, RuntimeFinalStatus.FAILED}
    assert (tmp_path / "content_team.runtime.jsonl").exists()

    events = _read_trace_events(tmp_path / "content_team.runtime.jsonl")
    assert any(
        event["event"] == "artifact_created"
        and event["payload"]["artifact_type"] == "improvement_plan"
        for event in events
    )


def test_content_team_adapter_describes_runtime_contract() -> None:
    adapter = ContentTeamReportAdapter(report_path=DEFAULT_REPORT, passing_score=70)

    contract = adapter.describe_contract()

    assert contract.task_id == "content_team:report_quality"
    assert "content_team.evaluate_report_quality" in contract.allowed_tools
    assert "ImprovementPlanArtifact" in contract.expected_outputs


def test_research_adapter_evaluates_existing_report(tmp_path) -> None:
    result = run_research_report(trace_dir=tmp_path)

    assert result.status == RuntimeFinalStatus.PASSED
    assert result.metrics["chars"] > 3000
    assert result.metrics["headings"] >= 4
    assert (tmp_path / "autonomous_research.runtime.jsonl").exists()


def _read_trace_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
