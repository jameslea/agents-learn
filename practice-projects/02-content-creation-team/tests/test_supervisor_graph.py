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

from sop_artifacts import ReviewFeedback  # noqa: E402
from supervisor_graph import (  # noqa: E402
    MAX_REVIEW_COUNT,
    final_status_heading,
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


if __name__ == "__main__":
    unittest.main()
