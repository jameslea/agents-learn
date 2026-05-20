from __future__ import annotations

"""运行 Schema Artifact 交接最小验证。

流程：
- Research step 生成 EvidenceTable artifact。
- Writer step 只读取 EvidenceTable payload，生成 DraftReport artifact。
- Reviewer step 只读取 DraftReport payload，生成 ReviewResult artifact。

这个 demo 故意不传递上游自由文本，用 store 中的 schema artifact 作为 step 间接口。
"""

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, cast

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from runtime_core.artifact import ArtifactRecord
from scenarios.research_mini.schemas import DEFAULT_RESEARCH_MINI_SCHEMAS, DraftReport, DraftSection, EvidenceItem, EvidenceTable, ReviewIssue, ReviewResult
from runtime_core.artifact import ArtifactStore, ArtifactValidationError


def run_demo() -> dict[str, Any]:
    store = ArtifactStore(schemas=DEFAULT_RESEARCH_MINI_SCHEMAS)

    evidence = EvidenceTable(
        topic="Agent Runtime Core",
        rows=[
            EvidenceItem(
                evidence_id="ev-001",
                claim="Agent steps should hand off structured artifacts instead of free text.",
                source="docs/agent-core-capabilities-validation-plan.md",
                confidence=0.9,
                notes="The plan explicitly lists Schema Artifact as a runtime core capability.",
            ),
            EvidenceItem(
                evidence_id="ev-002",
                claim="Context should reference artifact summaries, not full payloads.",
                source="practice-projects/06-agent-runtime-core/docs/01-context-builder.md",
                confidence=0.85,
            ),
        ],
    )
    evidence_record = store.save_model(
        artifact_id="artifact:evidence-table",
        artifact_type="evidence_table",
        title="Runtime Core Evidence Table",
        summary="Two evidence rows about structured handoff and context references.",
        schema_name="EvidenceTableV1",
        model=evidence,
        producer_step_id="research",
        tags=["artifact", "handoff", "research"],
        path="artifacts/schema-artifact/evidence_table.json",
    )

    loaded_evidence = cast(EvidenceTable, store.load_payload("artifact:evidence-table", schema_name="EvidenceTableV1"))
    draft = DraftReport(
        title=f"{loaded_evidence.topic} handoff note",
        evidence_artifact_id=evidence_record.artifact_id,
        sections=[
            DraftSection(
                heading="Structured handoff",
                content="Runtime steps should exchange validated artifacts so downstream steps can rely on stable fields.",
                evidence_refs=[row.evidence_id for row in loaded_evidence.rows],
            )
        ],
    )
    draft_record = store.save_model(
        artifact_id="artifact:draft-report",
        artifact_type="draft_report",
        title="Runtime Core Draft Report",
        summary="Draft report generated only from EvidenceTable payload.",
        schema_name="DraftReportV1",
        model=draft,
        producer_step_id="writer",
        tags=["artifact", "handoff", "writing"],
        path="artifacts/schema-artifact/draft_report.json",
        metadata={"consumed_artifact_ids": [evidence_record.artifact_id]},
    )

    loaded_draft = cast(DraftReport, store.load_payload("artifact:draft-report", schema_name="DraftReportV1"))
    review = ReviewResult(
        score=86,
        issues=[
            ReviewIssue(
                severity="low",
                message="The draft is valid but still short.",
                evidence_ref=loaded_draft.sections[0].evidence_refs[0],
            )
        ],
        required_changes=[],
        passed=True,
    )
    review_record = store.save_model(
        artifact_id="artifact:review-result",
        artifact_type="review_result",
        title="Runtime Core Review Result",
        summary="Review passed with one low severity note.",
        schema_name="ReviewResultV1",
        model=review,
        producer_step_id="reviewer",
        tags=["artifact", "handoff", "review"],
        path="artifacts/schema-artifact/review_result.json",
        metadata={"consumed_artifact_ids": [draft_record.artifact_id]},
    )

    invalid_error = _try_invalid_artifact(store)

    return {
        "handoff": [
            _record_summary(evidence_record),
            _record_summary(draft_record),
            _record_summary(review_record),
        ],
        "consumption_chain": [
            {"step": "writer", "consumes": evidence_record.artifact_id, "schema": "EvidenceTableV1"},
            {"step": "reviewer", "consumes": draft_record.artifact_id, "schema": "DraftReportV1"},
        ],
        "invalid_artifact_error": invalid_error,
    }


def _try_invalid_artifact(store: ArtifactStore) -> list[str]:
    invalid = ArtifactRecord(
        artifact_id="artifact:invalid-evidence",
        artifact_type="evidence_table",
        title="Invalid Evidence",
        summary="This artifact intentionally misses required rows.",
        schema_name="EvidenceTableV1",
        producer_step_id="research",
        payload={"topic": "Invalid example"},
    )
    try:
        store.save(invalid)
    except ArtifactValidationError as exc:
        return exc.result.errors
    return []


def _record_summary(record: ArtifactRecord) -> dict[str, Any]:
    return {
        "artifact_id": record.artifact_id,
        "artifact_type": record.artifact_type,
        "schema_name": record.schema_name,
        "producer_step_id": record.producer_step_id,
        "validated": record.validated,
        "payload_keys": list(record.payload.keys()),
        "consumed_artifact_ids": record.metadata.get("consumed_artifact_ids", []),
    }


def render_text_report(payload: dict[str, Any]) -> str:
    lines = [
        "Schema Artifact Handoff Demo",
        "=" * 29,
        "",
        "[Handoff artifacts]",
    ]
    for artifact in payload["handoff"]:
        consumed = artifact["consumed_artifact_ids"] or "-"
        lines.append(
            f"- {artifact['artifact_id']} | schema={artifact['schema_name']} | "
            f"producer={artifact['producer_step_id']} | validated={artifact['validated']} | "
            f"payload_keys={artifact['payload_keys']} | consumes={consumed}"
        )

    lines.extend(["", "[Consumption chain]"])
    for item in payload["consumption_chain"]:
        lines.append(f"- {item['step']} reads {item['consumes']} as {item['schema']}")

    lines.extend(["", "[Invalid artifact check]"])
    for error in payload["invalid_artifact_error"]:
        lines.append(f"- {error}")

    lines.extend(
        [
            "",
            "[结论]",
            "- 下游 step 读取 schema artifact payload，而不是读取上游自由文本。",
            "- artifact 保存前会执行 schema 校验，缺字段会返回明确错误。",
            "- ContextBuilder 后续仍只引用 artifact summary/path/schema，不读取完整 payload。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = ArgumentParser(description="Run the Schema Artifact handoff demo.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    payload = run_demo()
    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text_report(payload))


if __name__ == "__main__":
    main()
