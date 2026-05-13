import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from crew.writer import build_quality_repair_feedback, writer_node  # noqa: E402
from sop_artifacts import (  # noqa: E402
    ContentOutline,
    DraftContent,
    ResearchMaterial,
    ResearchReport,
    ReviewFeedback,
)
from utils.quality import validate_draft  # noqa: E402


def flat_body() -> str:
    section_text = "这是一个缺少内部结构的长段落[1]。" * 500
    return (
        "# 测试报告\n\n"
        f"## 一、背景\n{section_text}\n\n"
        f"## 二、案例\n{section_text}\n\n"
        f"## 三、建议\n{section_text}\n\n"
        "## 参考资料\n[1] https://example.com/report\n"
    )


def valid_body() -> str:
    section_text = "这是一个有效段落[1]。" * 500
    subsection_text = "该小节补充案例背景、关键指标、约束条件和管理启示[1]。" * 8
    return (
        "# 测试报告\n\n"
        f"## 一、背景\n{section_text}\n\n"
        "### 横向对比\n"
        f"{subsection_text}\n"
        "- 背景判断一[1]\n"
        "- 背景判断二[1]\n\n"
        f"## 二、案例\n{section_text}\n\n"
        "### 成功案例\n"
        f"{subsection_text}\n"
        "- 成功案例指标[1]\n"
        "- 公开案例证据[1]\n\n"
        "### 失败教训\n"
        f"{subsection_text}\n"
        "- 失败教训一[1]\n"
        "- 挑战与教训二[1]\n\n"
        f"## 三、建议\n{section_text}\n\n"
        "### 实施路径\n"
        f"{subsection_text}\n"
        "- 最佳实践一[1]\n"
        "- 行动建议二[1]\n\n"
        "## 参考资料\n[1] https://example.com/report\n"
    )


def base_state() -> dict:
    return {
        "outline": ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=["背景", "案例", "建议"],
            key_points=["趋势", "案例", "建议"],
        ),
        "research_report": ResearchReport(
            materials=[
                ResearchMaterial(
                    section_name="背景",
                    raw_data="事实（来源1）",
                    sources=["https://example.com/report"],
                    source_quality=["tier_1"],
                    source_notes=["官方报告"],
                )
            ]
        ),
        "history_summary": "",
    }


class WriterNodeTests(unittest.TestCase):
    def test_quality_repair_feedback_preserves_previous_feedback(self):
        previous = ReviewFeedback(
            is_approved=False,
            suggestions=["补充案例限制。"],
            specific_issues=["案例: 来源质量弱。"],
            target_agent="writer",
        )

        feedback = build_quality_repair_feedback(
            ["正文列表项数量 0 少于 5。"],
            previous_feedback=previous,
        )

        self.assertEqual(feedback.target_agent, "writer")
        self.assertIn("补充案例限制。", feedback.suggestions)
        self.assertIn("案例: 来源质量弱。", feedback.specific_issues)
        self.assertTrue(any(issue.startswith("质量门禁:") for issue in feedback.specific_issues))

    def test_writer_node_repairs_deterministic_quality_issues_locally(self):
        first = DraftContent(
            title="测试报告",
            content_markdown=flat_body(),
            word_count=3200,
            citations=["https://example.com/report"],
        )
        second = DraftContent(
            title="测试报告",
            content_markdown=valid_body(),
            word_count=3600,
            citations=["https://example.com/report"],
        )
        writer_instance = Mock()
        writer_instance.write_draft.side_effect = [first, second]

        with patch("crew.writer.Writer", return_value=writer_instance):
            result = writer_node(base_state())

        self.assertEqual(writer_instance.write_draft.call_count, 2)
        self.assertEqual(validate_draft(result["draft"]), [])
        self.assertIn("本地质量自修 1 次", result["history"][0])


if __name__ == "__main__":
    unittest.main()
