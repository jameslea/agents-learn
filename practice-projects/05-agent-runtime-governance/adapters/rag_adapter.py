from __future__ import annotations

from pathlib import Path

from runtime.artifacts import RAGEvaluationArtifact
from runtime.agent_adapter import AdapterRunContext, AgentRunResult, run_agent_adapter
from runtime.contracts import Budget, HumanReviewPolicy, RiskLevel, TaskContract, TaskType
from runtime.evaluation import EvaluationResult, RuntimeFinalStatus


PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_DIR.parents[1]
RAG_PROJECT_DIR = REPO_ROOT / "practice-projects" / "01-knowledge-base-qa"
DATA_DIR = RAG_PROJECT_DIR / "data"
INDEX_DIR = RAG_PROJECT_DIR / "chroma_db"

EXPECTED_TERMS = {
    "marketing_metric": "1000 万",
    "hardware_security": "AES-256",
    "long_doc_secret": "ComplexPass!2025_Secret",
}


def run_rag_readiness(*, trace_dir: Path) -> EvaluationResult:
    """Run deterministic RAG readiness checks without LLM calls."""
    return run_agent_adapter(RAGReadinessAdapter(), trace_dir=trace_dir)


class RAGReadinessAdapter:
    """Runtime adapter for project A: knowledge-base QA."""

    adapter_id = "rag_adapter"
    trace_name = "knowledge_base_qa.runtime.jsonl"

    def describe_contract(self) -> TaskContract:
        return _contract()

    def run(self, context: AdapterRunContext) -> AgentRunResult:
        context.record_tool_call(
            "rag.static_readiness_check",
            {"data_dir": str(DATA_DIR), "index_dir": str(INDEX_DIR)},
        )
        contract = context.contract

        data_files = sorted(DATA_DIR.glob("*.md"))
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in data_files)
        expected_terms_found = {name: term in corpus for name, term in EXPECTED_TERMS.items()}
        index_present = INDEX_DIR.exists() and any(INDEX_DIR.iterdir())
        notes = []
        if not data_files:
            notes.append("No markdown data files found.")
        missing = [name for name, found in expected_terms_found.items() if not found]
        if missing:
            notes.append(f"Missing expected test terms: {', '.join(missing)}")
        if not index_present:
            notes.append("Chroma index directory is missing or empty.")

        passed = bool(data_files) and all(expected_terms_found.values()) and index_present
        status = RuntimeFinalStatus.PASSED if passed else RuntimeFinalStatus.FAILED
        artifact = RAGEvaluationArtifact(
            artifact_id=f"{contract.task_id}:rag_evaluation",
            task_id=contract.task_id,
            source=self.adapter_id,
            data_files=[str(path) for path in data_files],
            expected_terms_found=expected_terms_found,
            index_present=index_present,
            notes=notes,
        )
        metrics = {
            "data_file_count": len(data_files),
            "expected_terms_found": expected_terms_found,
            "index_present": index_present,
            "notes": notes,
        }
        score_parts = [bool(data_files), all(expected_terms_found.values()), index_present]
        score = sum(1 for part in score_parts if part) / len(score_parts)
        result = EvaluationResult(
            task_id=contract.task_id,
            task_name="knowledge-base-qa",
            status=status,
            score=round(score, 3),
            attempts=1,
            reason="RAG static readiness check passed." if passed else "; ".join(notes),
            metrics=metrics,
        )
        return AgentRunResult(evaluation=result, artifacts=[artifact])

def _contract() -> TaskContract:
    return TaskContract(
        task_id="rag:static_readiness",
        task_type=TaskType.RAG_QA,
        goal="Check whether the RAG project has required test data and persisted index assets.",
        inputs={"data_dir": str(DATA_DIR), "index_dir": str(INDEX_DIR)},
        expected_outputs=["RAGEvaluationArtifact", "EvaluationResult"],
        success_criteria=[
            "test data files exist",
            "expected pitfall terms exist in corpus",
            "persisted index directory exists",
        ],
        risk_level=RiskLevel.LOW,
        allowed_tools=["rag.static_readiness_check"],
        budget=Budget(max_attempts=1, timeout_seconds=5.0),
        human_review_policy=HumanReviewPolicy.NEVER,
    )
