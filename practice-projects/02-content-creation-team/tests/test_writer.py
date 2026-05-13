import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from crew.writer import (  # noqa: E402
    build_evidence_adjusted_outline,
    build_quality_repair_feedback,
    build_writer_editorial_contract,
    downgrade_case_section_title,
    format_case_candidates,
    writer_node,
)
from sop_artifacts import (  # noqa: E402
    CaseCandidate,
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
    def test_downgrade_case_section_title_removes_case_claim(self):
        adjusted = downgrade_case_section_title("案例二：客服Agent 进阶")

        self.assertEqual(adjusted, "证据边界与趋势观察：客服Agent 进阶")

    def test_evidence_adjusted_outline_downgrades_unwritable_case_sections(self):
        outline = ContentOutline(
            title="2026 年 AI Agent 在企业数字转型中的实际应用案例与实施框架",
            target_audience="企业管理者",
            sections=[
                "问题定义：AI Agent 在数字转型中的角色",
                "案例一：供应链智能调度",
                "案例二：客服Agent 进阶",
                "横向比较：不同行业场景下Agent模式",
            ],
            key_points=["案例", "证据", "路径"],
        )
        research = ResearchReport(
            materials=[
                ResearchMaterial(
                    section_name="案例一：供应链智能调度",
                    raw_data="匿名综合案例，缺少企业名（来源1）。",
                    sources=["https://example.com/vendor"],
                    case_candidates=[
                        CaseCandidate(
                            name="未命名",
                            scenario="供应链调度",
                            evidence="厂商白皮书综合案例，企业名称不可核验",
                            source_url="https://example.com/vendor",
                            source_tier="tier_3",
                            verification_status="anonymous",
                            is_writable_case=False,
                        )
                    ],
                ),
                ResearchMaterial(
                    section_name="案例二：客服Agent 进阶",
                    raw_data="未找到直接匹配的公开案例（来源1）。",
                    sources=["https://example.com/trend"],
                ),
                ResearchMaterial(
                    section_name="横向比较：不同行业场景下Agent模式",
                    raw_data="横向比较材料（来源1）。",
                    sources=["https://example.com/compare"],
                ),
            ]
        )

        adjusted, aliases = build_evidence_adjusted_outline(outline, research)

        self.assertIn("应用场景与证据边界", adjusted.title)
        self.assertNotIn("实际应用案例", adjusted.title)
        self.assertEqual(
            adjusted.sections,
            [
                "问题定义：AI Agent 在数字转型中的角色",
                "证据边界与趋势观察：供应链智能调度",
                "证据边界与趋势观察：客服Agent 进阶",
                "横向比较：不同行业场景下Agent模式",
            ],
        )
        self.assertEqual(
            aliases,
            {
                "案例一：供应链智能调度": "证据边界与趋势观察：供应链智能调度",
                "案例二：客服Agent 进阶": "证据边界与趋势观察：客服Agent 进阶",
            },
        )

    def test_evidence_adjusted_outline_keeps_writable_case_sections(self):
        outline = ContentOutline(
            title="AI Agent 应用案例报告",
            target_audience="企业管理者",
            sections=["案例一：金融合规Agent"],
            key_points=["案例"],
        )
        research = ResearchReport(
            materials=[
                ResearchMaterial(
                    section_name="案例一：金融合规Agent",
                    raw_data="公开企业案例（来源1）。",
                    sources=["https://example.com/verified"],
                    case_candidates=[
                        CaseCandidate(
                            name="公开企业",
                            scenario="金融合规审核",
                            evidence="企业公开披露项目背景和效果边界",
                            source_url="https://example.com/verified",
                            source_tier="tier_1",
                            verification_status="verified",
                            is_writable_case=True,
                        )
                    ],
                )
            ]
        )

        adjusted, aliases = build_evidence_adjusted_outline(outline, research)

        self.assertEqual(adjusted, outline)
        self.assertEqual(aliases, {})

    def test_writer_editorial_contract_sets_stable_density_targets(self):
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=[
                "问题界定与技术基础",
                "案例一：客户服务Agent落地",
                "案例二：供应链Agent实践",
                "风险边界与治理",
                "实施路径与高管建议",
            ],
            key_points=["价值", "边界", "路径"],
        )

        contract = build_writer_editorial_contract(outline)

        self.assertIn("15-19 个有效三级小节", contract)
        self.assertIn("28-40 条列表项", contract)
        self.assertIn("列表超过 50 条", contract)
        self.assertIn("至少安排 1 个紧凑对比表", contract)
        self.assertIn("不要把“格式丰富”理解成增加更多短标题", contract)
        self.assertIn("不要把弱证据拆成多个短小节", contract)
        self.assertIn("客户服务Agent", contract)

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

    def test_format_case_candidates_marks_unwritable_candidates(self):
        material = ResearchMaterial(
            section_name="案例",
            raw_data="事实（来源1）。",
            sources=["https://example.com/report"],
            case_candidates=[
                CaseCandidate(
                    name="未命名",
                    scenario="制造业运维",
                    evidence="匿名综合案例，缺少企业名",
                    source_url="https://example.com/report",
                    source_tier="tier_3",
                    verification_status="anonymous",
                    is_writable_case=False,
                )
            ],
        )

        formatted = format_case_candidates(material)

        self.assertIn("不可作为核心案例", formatted)
        self.assertIn("未命名", formatted)

    def test_format_case_candidates_warns_when_empty(self):
        material = ResearchMaterial(
            section_name="案例",
            raw_data="趋势事实（来源1）。",
            sources=["https://example.com/report"],
        )

        formatted = format_case_candidates(material)

        self.assertIn("无可核验案例候选", formatted)
        self.assertIn("不得编造成具体企业案例", formatted)

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
