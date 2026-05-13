import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))


class _FakeStateGraph:
    def __init__(self, *args, **kwargs):
        pass


class _FakeMemorySaver:
    def __init__(self, *args, **kwargs):
        pass


langgraph_module = types.ModuleType("langgraph")
graph_module = types.ModuleType("langgraph.graph")
graph_module.StateGraph = _FakeStateGraph
graph_module.END = "__END__"
checkpoint_module = types.ModuleType("langgraph.checkpoint")
memory_module = types.ModuleType("langgraph.checkpoint.memory")
memory_module.MemorySaver = _FakeMemorySaver
sys.modules.setdefault("langgraph", langgraph_module)
sys.modules.setdefault("langgraph.graph", graph_module)
sys.modules.setdefault("langgraph.checkpoint", checkpoint_module)
sys.modules.setdefault("langgraph.checkpoint.memory", memory_module)

from sop_artifacts import ContentOutline, ReviewFeedback  # noqa: E402
from supervisor_graph import (  # noqa: E402
    MAX_REVIEW_COUNT,
    final_status_heading,
    outline_candidates_report,
    selected_outline_from_choice,
    should_auto_resume_research_retry,
)


class SupervisorGraphTests(unittest.TestCase):
    def test_auto_resumes_researcher_interrupt_after_rejection(self):
        snapshot = SimpleNamespace(
            next=("researcher",),
            values={
                "latest_feedback": ReviewFeedback(
                    is_approved=False,
                    suggestions=[],
                    specific_issues=["案例: 来源质量弱。"],
                    target_agent="researcher",
                )
            },
        )

        self.assertTrue(should_auto_resume_research_retry(snapshot))

    def test_does_not_auto_resume_initial_researcher_interrupt(self):
        snapshot = SimpleNamespace(
            next=("researcher",),
            values={"latest_feedback": None},
        )

        self.assertFalse(should_auto_resume_research_retry(snapshot))

    def test_rejected_before_max_review_count_has_accurate_heading(self):
        heading = final_status_heading(is_approved=False, review_count=1)

        self.assertIn("报告未通过评审", heading)
        self.assertNotIn("达到最大评审次数", heading)

    def test_rejected_at_max_review_count_mentions_max_review_count(self):
        heading = final_status_heading(
            is_approved=False,
            review_count=MAX_REVIEW_COUNT,
        )

        self.assertIn("达到最大评审次数", heading)

    def test_selected_outline_from_choice_uses_candidate_index(self):
        default = ContentOutline(
            title="默认",
            target_audience="管理者",
            sections=["背景", "案例", "建议"],
            key_points=["默认"],
        )
        candidate = ContentOutline(
            title="候选",
            target_audience="管理者",
            sections=["背景", "具体案例", "建议"],
            key_points=["候选"],
        )

        selected, name = selected_outline_from_choice(
            [default, candidate],
            [{"name": "sample_1"}, {"name": "sample_2"}],
            "2",
            default,
        )

        self.assertEqual(selected.title, "候选")
        self.assertEqual(name, "sample_2")

    def test_selected_outline_from_choice_keeps_default_on_blank_or_invalid_input(self):
        default = ContentOutline(
            title="默认",
            target_audience="管理者",
            sections=["背景", "案例", "建议"],
            key_points=["默认"],
        )

        selected, name = selected_outline_from_choice([], [], "", default)

        self.assertEqual(selected, default)
        self.assertIsNone(name)

    def test_outline_candidates_report_lists_candidates_and_strips_number_prefixes(self):
        outline = ContentOutline(
            title="候选",
            target_audience="管理者",
            sections=["1. 问题定义", "2、技术基础"],
            key_points=["价值"],
        )
        report = outline_candidates_report(
            {
                "outline_candidates": [outline],
                "outline_candidate_metrics": [
                    {
                        "name": "sample_1",
                        "total_score": 98,
                        "section_count": 2,
                        "case_sections": 1,
                        "case_specificity_ratio": 1.0,
                        "decision_value_sections": 1,
                        "issues": [],
                    }
                ],
                "outline_judge": {
                    "best_candidate": "sample_1",
                    "selection_reason": "结构更清晰。",
                },
            }
        )

        self.assertIn("LLM 主编推荐: sample_1", report)
        self.assertIn("1. 问题定义", report)
        self.assertNotIn("1. 1. 问题定义", report)


if __name__ == "__main__":
    unittest.main()
