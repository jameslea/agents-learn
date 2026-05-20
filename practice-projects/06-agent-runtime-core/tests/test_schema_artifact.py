from __future__ import annotations

import pytest

from runtime_core.artifact import ArtifactRecord
from scenarios.research_mini.schemas import DEFAULT_RESEARCH_MINI_SCHEMAS, DraftReport, DraftSection, EvidenceItem, EvidenceTable, ReviewResult
from runtime_core.artifact import ArtifactStore, ArtifactValidationError
from runtime_core.context import ContextBuilder, ContextPolicy, ContextSourceType
from runtime_core.task import TaskContract, TaskType
from runtime_core.task import RuntimeState


def _contract() -> TaskContract:
    return TaskContract(
        task_id="test:schema-artifact",
        task_type=TaskType.RESEARCH,
        goal="Validate schema artifact handoff.",
    )


def test_artifact_store_saves_and_loads_schema_payload() -> None:
    store = ArtifactStore(schemas=DEFAULT_RESEARCH_MINI_SCHEMAS)
    evidence = EvidenceTable(
        topic="Runtime Core",
        rows=[
            EvidenceItem(
                evidence_id="ev-1",
                claim="Structured handoff is easier to validate.",
                source="test",
                confidence=0.9,
            )
        ],
    )

    record = store.save_model(
        artifact_id="artifact:evidence",
        artifact_type="evidence_table",
        title="Evidence",
        summary="Evidence summary.",
        schema_name="EvidenceTableV1",
        model=evidence,
        producer_step_id="research",
        tags=["evidence"],
    )
    loaded = store.load_payload("artifact:evidence", schema_name="EvidenceTableV1")

    assert record.validated is True
    assert isinstance(loaded, EvidenceTable)
    assert loaded.rows[0].evidence_id == "ev-1"


def test_artifact_store_rejects_missing_required_fields() -> None:
    store = ArtifactStore(schemas=DEFAULT_RESEARCH_MINI_SCHEMAS)
    invalid = ArtifactRecord(
        artifact_id="artifact:invalid",
        artifact_type="evidence_table",
        title="Invalid",
        summary="Missing rows.",
        schema_name="EvidenceTableV1",
        payload={"topic": "Runtime Core"},
    )

    with pytest.raises(ArtifactValidationError) as exc:
        store.save(invalid)

    assert any("rows" in error for error in exc.value.result.errors)
    assert "artifact:invalid" not in [record.artifact_id for record in store.list_records()]


def test_downstream_reads_artifact_payload_instead_of_free_text() -> None:
    store = ArtifactStore(schemas=DEFAULT_RESEARCH_MINI_SCHEMAS)
    evidence_record = store.save_model(
        artifact_id="artifact:evidence",
        artifact_type="evidence_table",
        title="Evidence",
        summary="Only this summary may enter context.",
        schema_name="EvidenceTableV1",
        model=EvidenceTable(
            topic="Runtime Core",
            rows=[
                EvidenceItem(
                    evidence_id="ev-1",
                    claim="Artifact payload carries stable fields.",
                    source="test",
                    confidence=0.88,
                )
            ],
        ),
        producer_step_id="research",
        tags=["handoff"],
    )

    evidence = store.load_payload(evidence_record.artifact_id, schema_name="EvidenceTableV1")
    assert isinstance(evidence, EvidenceTable)
    draft_record = store.save_model(
        artifact_id="artifact:draft",
        artifact_type="draft_report",
        title="Draft",
        summary="Draft generated from evidence payload.",
        schema_name="DraftReportV1",
        model=DraftReport(
            title=f"{evidence.topic} note",
            evidence_artifact_id=evidence_record.artifact_id,
            sections=[
                DraftSection(
                    heading="Handoff",
                    content=evidence.rows[0].claim,
                    evidence_refs=[evidence.rows[0].evidence_id],
                )
            ],
        ),
        producer_step_id="writer",
        tags=["handoff"],
        metadata={"consumed_artifact_ids": [evidence_record.artifact_id]},
    )

    draft = store.load_payload(draft_record.artifact_id, schema_name="DraftReportV1")
    assert isinstance(draft, DraftReport)
    assert draft.evidence_artifact_id == "artifact:evidence"
    assert draft.sections[0].evidence_refs == ["ev-1"]
    assert draft_record.metadata["consumed_artifact_ids"] == ["artifact:evidence"]


def test_schema_mismatch_or_unvalidated_artifact_blocks_consumption() -> None:
    store = ArtifactStore(schemas=DEFAULT_RESEARCH_MINI_SCHEMAS)
    review_record = store.save_model(
        artifact_id="artifact:review",
        artifact_type="review_result",
        title="Review",
        summary="Review summary.",
        schema_name="ReviewResultV1",
        model=ReviewResult(score=92, issues=[], required_changes=[], passed=True),
        producer_step_id="reviewer",
    )

    with pytest.raises(ArtifactValidationError) as exc:
        store.get(review_record.artifact_id, expected_schema_name="DraftReportV1")

    assert any("schema mismatch" in error for error in exc.value.result.errors)

    unvalidated = ArtifactRecord(
        artifact_id="artifact:unvalidated",
        artifact_type="evidence_table",
        title="Unvalidated",
        summary="Saved without schema validation.",
        schema_name="EvidenceTableV1",
        payload={
            "topic": "Runtime Core",
            "rows": [
                {
                    "evidence_id": "ev-1",
                    "claim": "Valid shape but not validated by store.",
                    "source": "test",
                    "confidence": 0.8,
                }
            ],
        },
    )
    store.save(unvalidated, validate=False)

    with pytest.raises(ArtifactValidationError) as unvalidated_exc:
        store.get("artifact:unvalidated", expected_schema_name="EvidenceTableV1")

    assert any("not validated" in error for error in unvalidated_exc.value.result.errors)


def test_context_builder_references_schema_artifact_summary_only() -> None:
    store = ArtifactStore(schemas=DEFAULT_RESEARCH_MINI_SCHEMAS)
    record = store.save_model(
        artifact_id="artifact:evidence",
        artifact_type="evidence_table",
        title="Evidence",
        summary="Safe evidence summary.",
        schema_name="EvidenceTableV1",
        model=EvidenceTable(
            topic="Runtime Core",
            rows=[
                EvidenceItem(
                    evidence_id="ev-secret",
                    claim="Hidden payload content should not enter context.",
                    source="test",
                    confidence=0.8,
                )
            ],
        ),
        producer_step_id="research",
        tags=["handoff"],
    )

    bundle = ContextBuilder().build(
        contract=_contract(),
        state=RuntimeState.from_contract(_contract()),
        step_id="writer",
        current_step="Write from artifact.",
        step_tags=["handoff"],
        artifacts=[record],
        policy=ContextPolicy(required_artifact_types=["evidence_table"]),
    )

    assert bundle.ready is True
    assert bundle.items[0].source_type == ContextSourceType.ARTIFACT_REF
    assert bundle.items[0].content == "Safe evidence summary."
    assert "Hidden payload content" not in bundle.items[0].content
    assert bundle.items[0].metadata["schema_name"] == "EvidenceTableV1"
