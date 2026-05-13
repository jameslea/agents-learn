import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from crew.researcher import (  # noqa: E402
    Researcher,
    build_research_feedback_context,
    material_quality_issues,
    merge_research_materials,
    normalize_source_numbers,
    prioritize_search_results,
    select_sections_for_research,
    source_number_issues,
)
from sop_artifacts import CaseCandidate, ContentOutline, ResearchMaterial, ResearchReport, ReviewFeedback  # noqa: E402


class ResearchFeedbackTests(unittest.TestCase):
    def test_splits_section_and_global_feedback(self):
        feedback = ReviewFeedback(
            is_approved=False,
            suggestions=["优先补充 Gartner、IDC 等权威来源。"],
            specific_issues=[
                "制造业案例: 缺少可核验失败案例。",
                "质量门禁: 参考资料编号未在正文中使用: [9]",
            ],
            target_agent="researcher",
        )

        section_issues, global_issues = build_research_feedback_context(
            feedback,
            ["制造业案例", "零售业案例"],
        )

        self.assertEqual(section_issues, {"制造业案例": ["缺少可核验失败案例。"]})
        self.assertIn("优先补充 Gartner、IDC 等权威来源。", global_issues)
        self.assertIn("质量门禁: 参考资料编号未在正文中使用: [9]", global_issues)

    def test_approved_feedback_has_no_research_guidance(self):
        feedback = ReviewFeedback(
            is_approved=True,
            suggestions=[],
            specific_issues=[],
            target_agent=None,
        )

        section_issues, global_issues = build_research_feedback_context(
            feedback,
            ["制造业案例"],
        )

        self.assertEqual(section_issues, {})
        self.assertEqual(global_issues, [])

    def test_initial_research_selects_all_sections(self):
        sections = ["金融", "制造", "零售"]

        self.assertEqual(select_sections_for_research(sections, None, None), sections)

    def test_writer_feedback_does_not_trigger_research_retry(self):
        feedback = ReviewFeedback(
            is_approved=False,
            suggestions=["扩写正文到 3000 字。"],
            specific_issues=["质量门禁: 正文估算字数低于 3000。"],
            target_agent="writer",
        )
        existing = ResearchReport(
            materials=[
                ResearchMaterial(
                    section_name="金融",
                    raw_data="事实（来源1）",
                    sources=["https://example.com/a"],
                )
            ]
        )

        selected = select_sections_for_research(["金融", "制造"], feedback, existing)

        self.assertEqual(selected, [])

    def test_research_feedback_limits_named_sections(self):
        feedback = ReviewFeedback(
            is_approved=False,
            suggestions=[],
            specific_issues=[
                "金融: 缺少官方案例。",
                "制造: 缺少失败案例。",
                "零售: 来源质量弱。",
            ],
            target_agent="researcher",
        )
        existing = ResearchReport(materials=[])

        selected = select_sections_for_research(
            ["金融", "制造", "零售"],
            feedback,
            existing,
            max_sections=2,
        )

        self.assertEqual(selected, ["金融", "制造"])

    def test_global_research_feedback_limits_to_first_sections(self):
        feedback = ReviewFeedback(
            is_approved=False,
            suggestions=["整体来源质量弱，需要权威机构报告。"],
            specific_issues=[],
            target_agent="researcher",
        )
        existing = ResearchReport(materials=[])

        selected = select_sections_for_research(
            ["金融", "制造", "零售"],
            feedback,
            existing,
            max_sections=2,
        )

        self.assertEqual(selected, ["金融", "制造"])

    def test_global_case_feedback_prioritizes_case_sections(self):
        feedback = ReviewFeedback(
            is_approved=False,
            suggestions=["所有案例均为综合案例，无法核验具体企业名称。"],
            specific_issues=[],
            target_agent="researcher",
        )
        existing = ResearchReport(materials=[])

        selected = select_sections_for_research(
            ["技术基础", "案例一：制造业", "案例二：金融业", "实施路径"],
            feedback,
            existing,
            max_sections=2,
        )

        self.assertEqual(selected, ["案例一：制造业", "案例二：金融业"])

    def test_merge_research_materials_preserves_order_and_replaces_refreshed(self):
        existing = ResearchReport(
            materials=[
                ResearchMaterial(
                    section_name="金融",
                    raw_data="旧金融（来源1）",
                    sources=["https://example.com/old-finance"],
                    source_quality=["tier_1"],
                    source_notes=["官方案例"],
                ),
                ResearchMaterial(
                    section_name="制造",
                    raw_data="旧制造（来源1）",
                    sources=["https://example.com/old-manufacturing"],
                    source_quality=["tier_3"],
                    source_notes=["博客辅助"],
                ),
            ]
        )
        refreshed = [
            ResearchMaterial(
                section_name="制造",
                raw_data="新制造（来源1）",
                sources=["https://example.com/new-manufacturing"],
                source_quality=["tier_2"],
                source_notes=["权威媒体转述官方案例"],
            )
        ]

        merged = merge_research_materials(["金融", "制造"], existing, refreshed)

        self.assertEqual([material.section_name for material in merged], ["金融", "制造"])
        self.assertEqual(merged[0].raw_data, "旧金融（来源1）")
        self.assertEqual(merged[1].raw_data, "新制造（来源1）")
        self.assertEqual(merged[1].source_quality, ["tier_2"])

    def test_source_number_issue_detection_and_normalization(self):
        material = ResearchMaterial(
            section_name="案例",
            raw_data="事实A（来源1）；事实B（来源3）。",
            sources=["https://example.com/a", "https://example.com/b"],
            source_quality=["tier_1", "tier_2"],
            source_notes=["官方报告", "权威媒体"],
        )

        self.assertTrue(source_number_issues(material))

        with self.assertLogs("crew.researcher", level="WARNING"):
            normalized = normalize_source_numbers(material)

        self.assertEqual(normalized.raw_data, "事实A（来源1）；事实B（来源2）。")
        self.assertFalse(source_number_issues(normalized))

    def test_material_quality_issues_rejects_missing_sources(self):
        material = ResearchMaterial(
            section_name="案例",
            raw_data="事实A（来源1）。",
            sources=[],
        )

        issues = material_quality_issues(material)

        self.assertTrue(any("缺少来源 URL" in issue for issue in issues))

    def test_normalize_case_candidates_downgrades_anonymous_or_vendor_claims(self):
        from crew.researcher import normalize_case_candidates

        material = ResearchMaterial(
            section_name="案例",
            raw_data="事实（来源1）。",
            sources=["https://example.com/report"],
            case_candidates=[
                CaseCandidate(
                    name="未命名",
                    scenario="供应链调度",
                    evidence="匿名综合案例",
                    source_url="https://mckinsey.com/report.pdf",
                    source_tier="tier_1",
                    verification_status="verified",
                    is_writable_case=True,
                ),
                CaseCandidate(
                    name="某厂商客户",
                    scenario="客服Agent",
                    evidence="厂商自述成效",
                    source_url="https://vendor.example.com/case",
                    source_tier="tier_3",
                    verification_status="vendor_claim",
                    is_writable_case=True,
                ),
            ],
        )

        normalized = normalize_case_candidates(material)

        self.assertFalse(normalized.case_candidates[0].is_writable_case)
        self.assertFalse(normalized.case_candidates[1].is_writable_case)

    def test_extract_material_retries_when_sources_are_missing(self):
        first_response = Mock()
        first_response.content = """
        {
          "section_name": "案例",
          "raw_data": "关键事实缺少可用来源。",
          "sources": [],
          "source_quality": [],
          "source_notes": []
        }
        """
        second_response = Mock()
        second_response.content = """
        {
          "section_name": "案例",
          "raw_data": "关键事实（来源1）。",
          "sources": ["https://example.com/report"],
          "source_quality": ["tier_2"],
          "source_notes": ["权威媒体转述"]
        }
        """
        researcher = Researcher.__new__(Researcher)
        researcher.llm = Mock()
        researcher.llm.invoke.side_effect = [first_response, second_response]
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=["案例"],
            key_points=["事实"],
        )

        material = researcher._extract_material_with_retry(
            outline,
            "案例",
            {"results": [{"url": "https://example.com/report", "content": "关键事实"}]},
            [],
        )

        self.assertEqual(material.sources, ["https://example.com/report"])
        self.assertEqual(researcher.llm.invoke.call_count, 2)

    def test_prioritize_search_results_ranks_strong_sources_first(self):
        search_results = {
            "results": [
                {"url": "https://zhihu.com/p/123", "content": "弱来源"},
                {"url": "https://mckinsey.com/capabilities/report.pdf", "content": "强来源"},
                {"url": "https://thepaper.cn/newsDetail_forward_1", "content": "媒体来源"},
            ]
        }

        prioritized = prioritize_search_results(search_results)
        urls = [result["url"] for result in prioritized["results"]]

        self.assertEqual(urls[0], "https://mckinsey.com/capabilities/report.pdf")
        self.assertEqual(prioritized["results"][0]["source_quality_hint"], "tier_1")
        self.assertIn("不能单独支撑核心数字", prioritized["results"][-1]["source_use_guidance"])
        self.assertIn("按来源质量排序", prioritized["source_selection_note"])

    def test_material_prompt_uses_source_quality_hints(self):
        researcher = Researcher.__new__(Researcher)
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=["案例"],
            key_points=["事实"],
        )

        prompt = researcher._material_user_prompt(
            outline,
            "案例",
            {"results": []},
            "",
            "",
        )

        self.assertIn("source_quality_hint", prompt)
        self.assertIn("优先从 tier_1/tier_2 中提炼核心事实", prompt)


if __name__ == "__main__":
    unittest.main()
