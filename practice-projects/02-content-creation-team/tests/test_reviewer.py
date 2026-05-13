import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from crew.reviewer import Reviewer  # noqa: E402
from sop_artifacts import DraftContent  # noqa: E402


class ReviewerTests(unittest.TestCase):
    def test_approved_feedback_moves_specific_issues_to_suggestions(self):
        draft = DraftContent(
            title="测试报告",
            content_markdown="正文[1]\n\n## 参考资料\n[1] https://example.com/report",
            word_count=3000,
            citations=["https://example.com/report"],
        )
        response = Mock()
        response.content = """
        {
          "is_approved": true,
          "suggestions": ["整体可读性较好。"],
          "specific_issues": ["引言: 可增加背景解释。"],
          "target_agent": null
        }
        """

        with patch("crew.reviewer.ChatOpenAI") as chat_openai:
            chat_openai.return_value.invoke.return_value = response
            reviewer = Reviewer()
            feedback = reviewer.review_draft(draft)

        self.assertTrue(feedback.is_approved)
        self.assertEqual(feedback.specific_issues, [])
        self.assertIsNone(feedback.target_agent)
        self.assertIn("可选改进：引言: 可增加背景解释。", feedback.suggestions)


if __name__ == "__main__":
    unittest.main()
