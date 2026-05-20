from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from scenarios.code_review_mini.scenario import run_code_review_mini
from scenarios.code_review_mini.schemas import CodeFinding, ReviewReport


class FakeReviewer(BaseModel):
    provider: str = "fake"
    model: str = "fake-code-reviewer"

    def review(self, *, file_path: str, code: str, context_summary: str):
        from scenarios.code_review_mini.llm_reviewer import CodeReviewLLMResult

        assert file_path
        assert code
        assert context_summary
        return CodeReviewLLMResult(
            report=ReviewReport(
                summary="fake reviewer found one issue",
                findings=[
                    CodeFinding(
                        finding_id="finding-fake-001",
                        severity="medium",
                        category="maintainability",
                        message="fake issue",
                        file_path=file_path,
                        line_start=1,
                        line_end=1,
                        evidence="def example():",
                        recommendation="add clearer structure",
                    )
                ],
                risk_level="medium",
                passed=False,
                reviewer="fake",
            ),
            provider=self.provider,
            model=self.model,
            latency_ms=1,
        )


def test_code_review_mini_runs_with_deterministic_reviewer(tmp_path: Path) -> None:
    target = tmp_path / "unsafe.py"
    target.write_text(
        "import os\n\n"
        "def cleanup(path):\n"
        "    os.system('rm -rf ' + path)\n"
        "    try:\n"
        "        return int(path)\n"
        "    except:\n"
        "        return 0\n",
        encoding="utf-8",
    )

    result = run_code_review_mini(workdir=tmp_path / "run", target_path=target, reset=True)

    assert result.status == "completed"
    assert result.reviewer == "deterministic"
    assert result.reviewer_provider == "deterministic"
    assert result.reviewer_model == "rule-reviewer"
    assert result.reviewer_status == "success"
    assert result.finding_count == 2
    assert result.risk_level == "high"
    assert "artifact:code-snapshot" in result.artifacts
    assert "artifact:review-report" in result.artifacts
    assert "artifact:patch-suggestion" in result.artifacts
    assert result.runtime_friction


def test_code_review_mini_can_resume_after_review_step(tmp_path: Path) -> None:
    target = tmp_path / "unsafe.py"
    target.write_text("import os\nos.system('rm -rf ' + '/tmp/example')\n", encoding="utf-8")
    workdir = tmp_path / "run"

    first = run_code_review_mini(
        workdir=workdir,
        target_path=target,
        reset=True,
        stop_after="llm_or_rule_review",
    )
    assert first.status == "interrupted"

    second = run_code_review_mini(workdir=workdir, target_path=target)

    assert second.status == "completed"
    assert second.resumed is True
    assert second.skipped_steps == ["collect_code_context", "llm_or_rule_review"]


def test_code_review_mini_blocks_when_patch_writer_requires_approval(tmp_path: Path) -> None:
    target = tmp_path / "unsafe.py"
    target.write_text("import os\nos.system('rm -rf ' + '/tmp/example')\n", encoding="utf-8")

    result = run_code_review_mini(
        workdir=tmp_path / "run",
        target_path=target,
        reset=True,
        force_blocked=True,
    )

    assert result.status == "blocked"
    assert result.blocked_reason is not None
    assert result.blocked_reason.step_id == "propose_patch"
    assert "requires approval" in result.blocked_reason.reason


def test_code_review_mini_accepts_injected_llm_reviewer(tmp_path: Path) -> None:
    target = tmp_path / "review.py"
    target.write_text("def example():\n    return 1\n", encoding="utf-8")

    result = run_code_review_mini(
        workdir=tmp_path / "run",
        target_path=target,
        reset=True,
        reviewer=FakeReviewer(),
    )

    assert result.status == "completed"
    assert result.reviewer == "fake"
    assert result.reviewer_provider == "fake"
    assert result.reviewer_model == "fake-code-reviewer"
    assert result.reviewer_status == "success"
    assert result.reviewer_latency_ms == 1
    assert result.finding_count == 1
    assert any("LLM reviewer" in item for item in result.runtime_friction)
