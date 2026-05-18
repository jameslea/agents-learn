from __future__ import annotations

import json

import pytest

from runtime.evaluation import RuntimeFinalStatus
from runtime.contracts import RiskLevel
from runtime.tools import GovernedToolRunner, ToolCallBlocked, ToolPolicy, ToolRegistry, ToolSpec
from runtime.trace import RuntimeTraceRecorder
from scenarios.report_governance.llm_reviewer import LLMReviewResult
from scenarios.report_governance.scenario import run_report_governance


def test_report_governance_creates_failed_result_for_weak_doc(tmp_path) -> None:
    doc = tmp_path / "weak.md"
    doc.write_text("# Weak\n\nOnly a short paragraph.", encoding="utf-8")

    result = run_report_governance(doc, trace_dir=tmp_path)

    assert result.status == RuntimeFinalStatus.FAILED
    assert result.metrics["issue_count"] > 0
    assert (tmp_path / "weak.report_governance.runtime.jsonl").exists()


def test_report_governance_passes_structured_doc(tmp_path) -> None:
    doc = _write_strong_doc(tmp_path)

    result = run_report_governance(doc, trace_dir=tmp_path)

    assert result.status == RuntimeFinalStatus.PASSED
    assert result.score >= 0.7
    assert result.metrics["high_issue_count"] == 0
    manifest_path = tmp_path.parent / "manifests" / "strong.report_governance.runtime.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["adapter_id"] == "report_governance"
    assert manifest["task_id"] == "report_governance:strong"
    assert manifest["status"] == "passed"
    assert manifest["trace_path"] == str(tmp_path / "strong.report_governance.runtime.jsonl")


def test_governed_tool_runner_blocks_unlisted_tool(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="safe.echo", description="echo", risk_level=RiskLevel.LOW),
        lambda value: value,
    )
    runner = GovernedToolRunner(
        registry=registry,
        policy=ToolPolicy(allowed_tools=[]),
        trace=RuntimeTraceRecorder(tmp_path / "trace.jsonl"),
        task_id="t1",
    )

    with pytest.raises(ToolCallBlocked):
        runner.call("safe.echo", value="blocked")

    trace_events = _read_trace_events(tmp_path / "trace.jsonl")
    assert trace_events[0]["event"] == "tool_decision"
    assert trace_events[0]["payload"]["decision"] == "blocked"
    assert trace_events[1]["event"] == "guardrail_blocked"


def test_governed_tool_runner_blocks_write_outside_allowed_scope(tmp_path) -> None:
    safe_dir = tmp_path / "safe"
    outside_dir = tmp_path / "outside"
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="safe.write",
            description="write",
            risk_level=RiskLevel.HIGH,
            approval_required=True,
            write_path_args=["output_dir"],
        ),
        lambda output_dir: output_dir,
    )
    runner = GovernedToolRunner(
        registry=registry,
        policy=ToolPolicy(
            allowed_tools=["safe.write"],
            allow_high_risk=True,
            approved_tools=["safe.write"],
            allowed_write_dirs=[str(safe_dir)],
        ),
        trace=RuntimeTraceRecorder(tmp_path / "scope.jsonl"),
        task_id="t1",
    )

    with pytest.raises(ToolCallBlocked) as error:
        runner.call("safe.write", output_dir=str(outside_dir))

    assert error.value.decision.decision == "blocked"
    assert "outside allowed scope" in error.value.decision.reason
    trace_events = _read_trace_events(tmp_path / "scope.jsonl")
    assert trace_events[0]["payload"]["decision"] == "blocked"
    assert trace_events[1]["event"] == "guardrail_blocked"


def test_governed_tool_runner_allows_write_inside_allowed_scope(tmp_path) -> None:
    safe_dir = tmp_path / "safe"
    nested_dir = safe_dir / "nested"
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="safe.write",
            description="write",
            risk_level=RiskLevel.HIGH,
            approval_required=True,
            write_path_args=["output_dir"],
        ),
        lambda output_dir: output_dir,
    )
    runner = GovernedToolRunner(
        registry=registry,
        policy=ToolPolicy(
            allowed_tools=["safe.write"],
            allow_high_risk=True,
            approved_tools=["safe.write"],
            allowed_write_dirs=[str(safe_dir)],
        ),
        trace=RuntimeTraceRecorder(tmp_path / "scope_allowed.jsonl"),
        task_id="t1",
    )

    result = runner.call("safe.write", output_dir=str(nested_dir))

    assert result == str(nested_dir)
    trace_events = _read_trace_events(tmp_path / "scope_allowed.jsonl")
    assert trace_events[0]["payload"]["decision"] == "allowed"
    assert trace_events[1]["event"] == "tool_called"


def test_governed_tool_runner_blocks_network_tool_without_policy(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="llm.review",
            description="review",
            risk_level=RiskLevel.MEDIUM,
            requires_network=True,
        ),
        lambda: "reviewed",
    )
    runner = GovernedToolRunner(
        registry=registry,
        policy=ToolPolicy(allowed_tools=["llm.review"], allow_network=False),
        trace=RuntimeTraceRecorder(tmp_path / "network.jsonl"),
        task_id="t1",
    )

    with pytest.raises(ToolCallBlocked) as error:
        runner.call("llm.review")

    assert "network access is not allowed" in error.value.decision.reason
    trace_events = _read_trace_events(tmp_path / "network.jsonl")
    assert trace_events[0]["payload"]["decision"] == "blocked"
    assert trace_events[1]["event"] == "guardrail_blocked"


def test_report_governance_requests_human_review_for_unapproved_patch(tmp_path) -> None:
    doc = _write_strong_doc(tmp_path)

    result = run_report_governance(doc, trace_dir=tmp_path, request_patch=True, patch_output_dir=tmp_path)

    assert result.status == RuntimeFinalStatus.NEEDS_HUMAN
    assert result.metrics["human_review_required"] is True
    assert result.metrics["blocked_tool"] == "report.write_improvement_patch"
    assert not (tmp_path / "strong.improvement_patch.md").exists()

    events = _read_trace_events(tmp_path / "strong.report_governance.runtime.jsonl")
    assert "tool_decision" in [event["event"] for event in events]
    assert "human_review_requested" in [event["event"] for event in events]
    assert any(
        event["event"] == "artifact_created"
        and event["payload"]["artifact_type"] == "human_review_request"
        for event in events
    )


def test_report_governance_writes_patch_after_approval(tmp_path) -> None:
    doc = _write_strong_doc(tmp_path)

    result = run_report_governance(
        doc,
        trace_dir=tmp_path,
        request_patch=True,
        approve_high_risk=True,
        patch_output_dir=tmp_path,
    )

    assert result.status == RuntimeFinalStatus.PASSED
    patch_path = tmp_path / "strong.improvement_patch.md"
    assert result.metrics["patch_path"] == str(patch_path)
    assert patch_path.exists()
    assert "不会修改原始文档" in patch_path.read_text(encoding="utf-8")

    events = _read_trace_events(tmp_path / "strong.report_governance.runtime.jsonl")
    assert "human_review_decided" in [event["event"] for event in events]
    assert any(
        event["event"] == "tool_decision"
        and event["payload"]["tool_name"] == "report.write_improvement_patch"
        and event["payload"]["decision"] == "allowed"
        for event in events
    )


def test_report_governance_adds_optional_llm_review_artifact(tmp_path) -> None:
    doc = _write_strong_doc(tmp_path)

    result = run_report_governance(
        doc,
        trace_dir=tmp_path,
        llm_review=True,
        reviewer=FakeReviewer(),
    )

    assert result.status == RuntimeFinalStatus.PASSED
    assert result.metrics["llm_review"]["provider"] == "fake"
    assert result.metrics["llm_review"]["model"] == "fake-reviewer"
    assert result.metrics["llm_review"]["verdict"] == "caution"
    assert result.metrics["llm_review"]["confidence"] == 0.8
    assert result.metrics["llm_review"]["concern_count"] == 1
    assert result.metrics["llm_review"]["suggested_action_count"] == 1
    assert result.metrics["llm_review"]["status"] == "success"
    assert result.metrics["llm_review"]["failure_reason"] == ""
    assert result.metrics["llm_review"]["latency_ms"] >= 0

    events = _read_trace_events(tmp_path / "strong.report_governance.runtime.jsonl")
    assert any(
        event["event"] == "tool_decision"
        and event["payload"]["tool_name"] == "report.llm_review"
        and event["payload"]["decision"] == "allowed"
        for event in events
    )
    assert any(
        event["event"] == "artifact_created"
        and event["payload"]["artifact_type"] == "llm_review"
        and event["payload"]["verdict"] == "caution"
        and event["payload"]["status"] == "success"
        and event["payload"]["latency_ms"] >= 0
        for event in events
    )


def test_report_governance_records_failed_llm_review_without_failing_task(tmp_path) -> None:
    doc = _write_strong_doc(tmp_path)

    result = run_report_governance(
        doc,
        trace_dir=tmp_path,
        llm_review=True,
        reviewer=FailingReviewer(),
    )

    assert result.status == RuntimeFinalStatus.PASSED
    assert result.metrics["llm_review"]["provider"] == "fake"
    assert result.metrics["llm_review"]["status"] == "failed"
    assert "provider timeout" in result.metrics["llm_review"]["failure_reason"]
    assert result.metrics["llm_review"]["latency_ms"] >= 0

    events = _read_trace_events(tmp_path / "strong.report_governance.runtime.jsonl")
    assert any(
        event["event"] == "artifact_created"
        and event["payload"]["artifact_type"] == "llm_review"
        and event["payload"]["status"] == "failed"
        for event in events
    )


def _write_strong_doc(tmp_path) -> object:
    doc = tmp_path / "strong.md"
    section_body = "这是一段包含充分分析、证据解释和明确结论的内容。" * 30
    markdown = "\n\n".join(
        [
            "# Strong Report",
            f"## 背景\n\n{section_body}",
            f"## 方法\n\n- 方法一\n- 方法二\n- 方法三\n\n{section_body}",
            f"## 发现\n\n| 项目 | 结论 |\n|------|------|\n| A | 有效 |\n\n{section_body}",
            f"## 证据\n\n- https://example.com/a\n- https://example.com/b\n- https://example.com/c\n- https://example.com/d\n- https://example.com/e\n\n{section_body}",
            f"## 局限与证据边界\n\n{section_body}",
            f"## 建议\n\n- 建议一\n- 建议二\n- 建议三\n\n{section_body}",
        ]
    )
    doc.write_text(markdown, encoding="utf-8")
    return doc


def _read_trace_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class FakeReviewer:
    provider = "fake"
    model = "fake-reviewer"

    def review(self, *, markdown, metrics, issues):
        assert markdown
        assert metrics["chars"] > 0
        assert issues == []
        return LLMReviewResult(
            verdict="caution",
            confidence=0.8,
            strengths=["结构完整"],
            concerns=["仍需要人工抽查关键事实"],
            suggested_actions=["抽查引用来源"],
            raw_text='{"verdict":"caution"}',
        )


class FailingReviewer:
    provider = "fake"
    model = "failing-reviewer"

    def review(self, *, markdown, metrics, issues):
        raise RuntimeError("provider timeout")
