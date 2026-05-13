import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from crew.reviewer import Reviewer, reviewer_node  # noqa: E402
from sop_artifacts import DraftContent, ReviewFeedback  # noqa: E402


def enhancement_candidate_body() -> str:
    long_text = "该段落用于补足报告厚度、案例背景、实施条件、证据边界和管理判断[1]。" * 35
    subsection_text = "该小节包含可执行分析、约束条件和风险说明[1]。" * 10
    parts = ["# 测试报告\n"]
    for index in range(1, 9):
        parts.append(f"## {index}、章节{index}\n{long_text}\n")
        if index in {2, 3, 4}:
            parts.append("### 成功案例\n" + subsection_text + "\n")
            parts.append("### 挑战与教训\n" + subsection_text + "\n")
            parts.append("### 横向对比\n" + subsection_text + "\n")
        elif index in {6, 7}:
            parts.append("### 实施路径\n" + subsection_text + "\n")
            parts.append("### 最佳实践\n" + subsection_text + "\n")
    parts.append("\n".join(f"- 建议项 {index}[1]" for index in range(10)))
    parts.append("\n## 参考资料\n[1] https://example.com/report\n")
    return "\n".join(parts)


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

    def test_reviewer_node_converts_basic_approval_to_quality_enhancement(self):
        draft = DraftContent(
            title="测试报告",
            content_markdown=enhancement_candidate_body(),
            word_count=4200,
            citations=["https://example.com/report"],
        )
        approved_feedback = ReviewFeedback(
            is_approved=True,
            suggestions=["基本可以通过。"],
            specific_issues=[],
            target_agent=None,
        )

        with patch("crew.reviewer.Reviewer") as reviewer_cls:
            reviewer_cls.return_value.review_draft.return_value = approved_feedback
            result = reviewer_node(
                {
                    "draft": draft,
                    "review_count": 1,
                    "quality_enhancement_count": 0,
                }
            )

        feedback = result["latest_feedback"]
        self.assertFalse(feedback.is_approved)
        self.assertEqual(feedback.target_agent, "writer")
        self.assertEqual(result["review_count"], 2)
        self.assertEqual(result["quality_enhancement_count"], 1)
        self.assertTrue(any(issue.startswith("质量增强:") for issue in feedback.specific_issues))
        self.assertIn("需增强", result["history"][0])

    def test_reviewer_node_does_not_repeat_quality_enhancement(self):
        draft = DraftContent(
            title="测试报告",
            content_markdown=enhancement_candidate_body(),
            word_count=4200,
            citations=["https://example.com/report"],
        )
        approved_feedback = ReviewFeedback(
            is_approved=True,
            suggestions=["增强后可以通过。"],
            specific_issues=[],
            target_agent=None,
        )

        with patch("crew.reviewer.Reviewer") as reviewer_cls:
            reviewer_cls.return_value.review_draft.return_value = approved_feedback
            result = reviewer_node(
                {
                    "draft": draft,
                    "review_count": 2,
                    "quality_enhancement_count": 1,
                }
            )

        feedback = result["latest_feedback"]
        self.assertTrue(feedback.is_approved)
        self.assertEqual(result["review_count"], 3)
        self.assertNotIn("quality_enhancement_count", result)


if __name__ == "__main__":
    unittest.main()
