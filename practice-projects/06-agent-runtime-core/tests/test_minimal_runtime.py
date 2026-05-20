from __future__ import annotations

from scenarios.research_mini.scenario import run_research_mini
from runtime_core.execution import ToolCallRequest, ToolPolicy, ToolPolicyChecker, ToolRiskLevel
from runtime_core.observability import TraceReader


def test_research_mini_completes_end_to_end(tmp_path) -> None:
    result = run_research_mini(workdir=tmp_path, reset=True)

    assert result.status == "completed"
    assert result.final_review_passed is True
    assert result.artifacts == ["artifact:evidence-table", "artifact:draft-report", "artifact:review-result"]
    assert result.trace_summary["event_type_counts"]["artifact_created"] == 3
    assert result.trace_summary["event_type_counts"]["artifact_consumed"] == 3


def test_research_mini_resumes_from_checkpoint_and_artifact_snapshot(tmp_path) -> None:
    first = run_research_mini(workdir=tmp_path, reset=True, stop_after="collect_evidence")
    assert first.status == "interrupted"
    assert first.artifacts == ["artifact:evidence-table"]

    second = run_research_mini(workdir=tmp_path)

    assert second.status == "completed"
    assert second.resumed is True
    assert second.skipped_steps == ["plan_research", "collect_evidence"]
    assert second.final_review_passed is True
    assert "artifact:draft-report" in second.artifacts
    assert "artifact:review-result" in second.artifacts


def test_research_mini_blocks_on_tool_policy(tmp_path) -> None:
    result = run_research_mini(workdir=tmp_path, reset=True, force_blocked=True)

    assert result.status == "blocked"
    assert result.blocked_reason is not None
    assert result.blocked_reason.step_id == "write_report"
    assert "read-only tool" in result.blocked_reason.reason
    assert result.trace_summary["human_required"][0]["step_id"] == "write_report"


def test_research_mini_trace_does_not_store_full_artifact_payload(tmp_path) -> None:
    result = run_research_mini(workdir=tmp_path, reset=True)
    events = TraceReader(result.trace_path).read_events()
    trace_text = "\n".join(event.model_dump_json() for event in events)

    assert "ev-runtime-001" not in trace_text
    assert "artifact:evidence-table" in trace_text
    assert "EvidenceTableV1" in trace_text


def test_tool_policy_checker_blocks_unregistered_or_mutating_calls() -> None:
    checker = ToolPolicyChecker(
        [ToolPolicy(tool_name="reader", risk_level=ToolRiskLevel.LOW, read_only=True)]
    )

    missing = checker.check(ToolCallRequest(tool_name="unknown", step_id="s1"))
    mutating = checker.check(ToolCallRequest(tool_name="reader", step_id="s1", mutating=True))
    allowed = checker.check(ToolCallRequest(tool_name="reader", step_id="s1"))

    assert missing.allowed is False
    assert missing.risk_level == ToolRiskLevel.HIGH
    assert mutating.allowed is False
    assert "read-only" in mutating.reason
    assert allowed.allowed is True
