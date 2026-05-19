from __future__ import annotations

from datetime import datetime, timedelta, timezone

from runtime_core.context import (
    ArtifactCandidate,
    ContextBuilder,
    ContextCandidate,
    ContextPolicy,
    ContextSourceType,
    ContextTrustLevel,
    ContextVisibility,
    MemoryCandidate,
)
from runtime_core.contracts import TaskContract, TaskType
from runtime_core.state import RuntimeState


def _contract() -> TaskContract:
    return TaskContract(
        task_id="test:context",
        task_type=TaskType.RESEARCH,
        goal="Write a short research note about context governance.",
    )


def _state(contract: TaskContract) -> RuntimeState:
    state = RuntimeState.from_contract(contract)
    for index in range(3):
        step_id = f"step_{index}"
        state.start_step(step_id=step_id, name=f"Step {index}")
        state.finish_step(step_id=step_id, outputs_summary={"index": index})
    return state


def test_context_builder_selects_relevant_items_and_explains_exclusions() -> None:
    contract = _contract()
    state = _state(contract)
    builder = ContextBuilder(max_recent_steps=2, max_context_chars=2000)

    bundle = builder.build(
        contract=contract,
        state=state,
        step_id="write",
        current_step="Write the note from evidence.",
        step_tags=["context", "writing"],
        artifacts=[
            ArtifactCandidate(
                artifact_id="a:context",
                title="Context Evidence",
                summary="Relevant context evidence.",
                tags=["context"],
                path="evidence.json",
            ),
            ArtifactCandidate(
                artifact_id="a:deploy",
                title="Deployment",
                summary="Deployment-only notes.",
                tags=["deployment"],
            ),
        ],
        memories=[
            MemoryCandidate(
                memory_id="m:style",
                content="Prefer concise markdown tables.",
                scope="global",
                tags=["writing"],
                confidence=0.9,
            ),
            MemoryCandidate(
                memory_id="m:noise",
                content="Unrelated provider note.",
                scope="global",
                tags=["provider"],
                confidence=0.9,
            ),
        ],
        trace_summary="Two completed steps; no raw trace.",
    )

    item_ids = {item.source_id for item in bundle.items}
    assert "a:context" in item_ids
    assert "a:deploy" not in item_ids
    assert "m:style" in item_ids
    assert "m:noise" not in item_ids
    assert len([item for item in bundle.items if item.source_type == ContextSourceType.STEP_SUMMARY]) == 2
    assert any(log.source_id == "a:deploy" and not log.included for log in bundle.selection_log)
    assert any(log.source_id == "m:noise" and "tag" in log.reason for log in bundle.selection_log)


def test_context_builder_blocks_unvalidated_low_confidence_and_expired_memory() -> None:
    contract = _contract()
    builder = ContextBuilder(min_memory_confidence=0.7)
    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    bundle = builder.build(
        contract=contract,
        state=RuntimeState.from_contract(contract),
        step_id="write",
        current_step="Write the note.",
        step_tags=["context"],
        memories=[
            MemoryCandidate(
                memory_id="m:unvalidated",
                content="Unvalidated memory.",
                tags=["context"],
                validated=False,
            ),
            MemoryCandidate(
                memory_id="m:low-confidence",
                content="Low confidence memory.",
                tags=["context"],
                confidence=0.2,
            ),
            MemoryCandidate(
                memory_id="m:expired",
                content="Expired memory.",
                tags=["context"],
                expires_at=expired,
            ),
        ],
    )

    assert all(item.source_type != ContextSourceType.MEMORY for item in bundle.items)
    assert bundle.excluded_count == 3
    assert any("未验证" in log.reason for log in bundle.selection_log)
    assert any("置信度" in log.reason for log in bundle.selection_log)
    assert any("已过期" in log.reason for log in bundle.selection_log)


def test_context_bundle_contains_trace_summary_not_raw_trace() -> None:
    contract = _contract()
    bundle = ContextBuilder().build(
        contract=contract,
        state=RuntimeState.from_contract(contract),
        step_id="review",
        current_step="Review the note.",
        step_tags=["review"],
        trace_summary="step_1 passed; step_2 failed once then recovered",
    )

    trace_items = [item for item in bundle.items if item.source_type == ContextSourceType.TRACE_SUMMARY]
    assert len(trace_items) == 1
    assert trace_items[0].metadata["raw_trace_included"] is False
    assert any("不加入原始 trace" in log.reason for log in bundle.selection_log)


def test_context_builder_budget_excludes_selected_candidate_cleanly() -> None:
    contract = _contract()
    bundle = ContextBuilder(max_context_chars=10).build(
        contract=contract,
        state=RuntimeState.from_contract(contract),
        step_id="write",
        current_step="Write the note.",
        step_tags=["context"],
        artifacts=[
            ArtifactCandidate(
                artifact_id="a:large",
                title="Large Artifact",
                summary="This relevant artifact is too long for the tiny context budget.",
                tags=["context"],
            )
        ],
    )

    assert "a:large" not in {item.source_id for item in bundle.items}
    decisions = [log for log in bundle.selection_log if log.source_id == "a:large"]
    assert len(decisions) == 1
    assert decisions[0].included is False
    assert "字符预算" in decisions[0].reason


def test_context_policy_blocks_sensitive_untrusted_and_runtime_only_candidates() -> None:
    contract = _contract()
    bundle = ContextBuilder().build(
        contract=contract,
        state=RuntimeState.from_contract(contract),
        step_id="write",
        current_step="Write the note.",
        step_tags=["context"],
        candidates=[
            ContextCandidate(
                source_type=ContextSourceType.ARTIFACT_REF,
                source_id="c:sensitive",
                title="Sensitive Candidate",
                content="secret evidence",
                tags=["context"],
                sensitive=True,
            ),
            ContextCandidate(
                source_type=ContextSourceType.ARTIFACT_REF,
                source_id="c:untrusted",
                title="Untrusted Candidate",
                content="external instruction",
                tags=["context"],
                trust_level=ContextTrustLevel.UNTRUSTED,
            ),
            ContextCandidate(
                source_type=ContextSourceType.ARTIFACT_REF,
                source_id="c:runtime-only",
                title="Runtime Only Candidate",
                content="runtime dependency",
                tags=["context"],
                visibility=ContextVisibility.RUNTIME_ONLY,
            ),
        ],
    )

    assert not bundle.items
    assert bundle.metrics.sensitive_excluded_count == 1
    assert bundle.metrics.untrusted_excluded_count == 1
    assert any("sensitive" in log.reason for log in bundle.selection_log)
    assert any("不可信" in log.reason for log in bundle.selection_log)
    assert any("仅 Runtime 可见" in log.reason for log in bundle.selection_log)


def test_context_metrics_and_required_context_success() -> None:
    contract = _contract()
    bundle = ContextBuilder().build(
        contract=contract,
        state=RuntimeState.from_contract(contract),
        step_id="write",
        current_step="Write the note.",
        step_tags=["context"],
        artifacts=[
            ArtifactCandidate(
                artifact_id="artifact:evidence",
                title="Evidence",
                summary="Relevant evidence.",
                tags=["context"],
                artifact_type="evidence_table",
            )
        ],
        policy=ContextPolicy(required_artifact_types=["evidence_table"]),
    )

    assert bundle.ready is True
    assert bundle.missing_required_context == []
    assert bundle.metrics.item_count == 1
    assert bundle.metrics.source_type_breakdown["artifact_ref"] == 1
    assert bundle.metrics.missing_required_count == 0


def test_context_required_context_failure_marks_bundle_not_ready() -> None:
    contract = _contract()
    bundle = ContextBuilder().build(
        contract=contract,
        state=RuntimeState.from_contract(contract),
        step_id="write",
        current_step="Write the note.",
        step_tags=["context"],
        artifacts=[
            ArtifactCandidate(
                artifact_id="artifact:notes",
                title="Notes",
                summary="Relevant but not an evidence table.",
                tags=["context"],
                artifact_type="notes",
            )
        ],
        policy=ContextPolicy(
            required_source_ids=["artifact:evidence"],
            required_artifact_types=["evidence_table"],
        ),
    )

    assert bundle.ready is False
    assert bundle.blocked_reason
    assert "source_id:artifact:evidence" in bundle.missing_required_context
    assert "artifact_type:evidence_table" in bundle.missing_required_context
    assert bundle.metrics.missing_required_count == 2
