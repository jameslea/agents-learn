import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from content_research.material_processing import (  # noqa: E402
    normalize_case_candidates,
    normalize_source_numbers,
)
from content_research.prompts import build_material_user_prompt  # noqa: E402
from content_research.search_planner import (  # noqa: E402
    build_section_search_query,
    classify_research_section,
    clean_section_for_search,
)
from content_research.source_curation import (  # noqa: E402
    prioritize_search_results,
)
from crew.researcher import Researcher  # noqa: E402
from sop_artifacts import CaseCandidate, ContentOutline, ResearchMaterial, ReviewFeedback  # noqa: E402


class ResearchFeedbackTests(unittest.TestCase):
    def test_classify_research_section_prioritizes_specific_roles(self):
        self.assertEqual(classify_research_section("AI Agent 的核心技术基础与成熟度评估：多模态感知、规划推理、工具调用"), "technology")
        self.assertEqual(classify_research_section("实施建议：企业引入 AI Agent 的四阶段框架（评估-试点-扩展-治理）"), "implementation")
        self.assertEqual(classify_research_section("风险治理：安全、合规与可靠性"), "risk")

    def test_clean_section_for_search_removes_outline_role_noise(self):
        cleaned = clean_section_for_search("案例二：客服Agent 进阶：金融服务自动理赔")

        self.assertEqual(cleaned, "客服Agent 进阶 金融服务自动理赔")

    def test_classify_comparison_section_before_case_keywords(self):
        section_type = classify_research_section("横向比较：不同行业场景下Agent模式")

        self.assertEqual(section_type, "comparison")

    def test_case_search_query_uses_case_terms_without_pdf_only_constraint(self):
        outline = ContentOutline(
            title="2026 年 AI Agent 在企业数字转型中的应用场景与证据边界",
            target_audience="管理者",
            sections=["案例一：供应链智能调度Agent"],
            key_points=["案例", "证据"],
        )

        query, section_type, cleaned = build_section_search_query(
            outline,
            "案例一：供应链智能调度Agent",
        )

        self.assertEqual(section_type, "case")
        self.assertEqual(cleaned, "供应链智能调度Agent")
        self.assertIn("case study", query)
        self.assertIn("press release", query)
        self.assertNotIn("filetype:pdf", query)
        self.assertNotIn("技术报告", query)

    def test_technology_search_query_uses_technical_terms(self):
        outline = ContentOutline(
            title="2026 年 AI Agent 在企业数字转型中的应用场景与证据边界",
            target_audience="管理者",
            sections=["技术基础：Agent 架构与工具调用能力"],
            key_points=["技术", "证据"],
        )

        query, section_type, cleaned = build_section_search_query(
            outline,
            "技术基础：Agent 架构与工具调用能力",
        )

        self.assertEqual(section_type, "technology")
        self.assertEqual(cleaned, "Agent 架构与工具调用能力")
        self.assertIn("technical report", query)
        self.assertIn("filetype:pdf", query)
        self.assertNotIn("case study", query)

    def test_feedback_search_query_keeps_focused_feedback_terms(self):
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=["案例一：金融合规Agent"],
            key_points=["案例"],
        )

        query, section_type, _cleaned = build_section_search_query(
            outline,
            "案例一：金融合规Agent",
            "缺少公开企业名称和独立验证来源。",
        )

        self.assertEqual(section_type, "case")
        self.assertIn("缺少公开企业名称和独立验证来源", query)
        self.assertIn("annual report", query)

    def test_research_feedback_reruns_all_sections(self):
        researcher = Researcher(llm=Mock(), search_tool=Mock())
        calls = []

        def fake_research_section(outline, section, feedback_note):
            calls.append((section, feedback_note))
            return ResearchMaterial(
                section_name=section,
                raw_data="事实（来源1）。",
                sources=["https://example.com/report"],
            )

        researcher._research_section = fake_research_section
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=["技术基础", "案例一：金融合规Agent", "实施路径"],
            key_points=["事实"],
        )
        feedback = ReviewFeedback(
            is_approved=False,
            suggestions=["补充官方来源。"],
            specific_issues=["案例一：金融合规Agent: 缺少独立验证。"],
            target_agent="researcher",
        )

        report = researcher.conduct_research(outline, feedback=feedback)

        self.assertEqual([section for section, _note in calls], outline.sections)
        self.assertEqual([material.section_name for material in report.materials], outline.sections)
        self.assertTrue(all("补充官方来源" in note for _section, note in calls))

    def test_source_number_normalization_clamps_overflowing_references(self):
        material = ResearchMaterial(
            section_name="案例",
            raw_data="事实A（来源1）；事实B（来源3）。",
            sources=["https://example.com/a", "https://example.com/b"],
            source_quality=["tier_1", "tier_2"],
            source_notes=["官方报告", "权威媒体"],
        )

        with self.assertLogs("content_research.material_processing", level="WARNING"):
            normalized = normalize_source_numbers(material)

        self.assertEqual(normalized.raw_data, "事实A（来源1）；事实B（来源2）。")

    def test_normalize_case_candidates_downgrades_anonymous_or_vendor_claims(self):
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

    def test_normalize_case_candidates_keeps_verified_named_candidate(self):
        material = ResearchMaterial(
            section_name="案例一：供应链智能调度",
            raw_data="Acme 公开案例（来源1）。",
            sources=["https://assets.kpmg.com/content/report.pdf"],
            case_candidates=[
                CaseCandidate(
                    name="Acme",
                    scenario="供应链调度",
                    evidence="公开披露供应链调度自动化",
                    source_url="https://assets.kpmg.com/content/report.pdf",
                    source_tier="tier_1",
                    verification_status="verified",
                    is_writable_case=True,
                )
            ],
        )

        normalized = normalize_case_candidates(material)

        self.assertTrue(normalized.case_candidates[0].is_writable_case)

    def test_extract_material_invokes_llm_once(self):
        response = Mock()
        response.content = """
        {
          "section_name": "案例",
          "raw_data": "关键事实（来源1）。",
          "sources": ["https://example.com/report"],
          "source_quality": ["tier_2"],
          "source_notes": ["权威媒体转述"]
        }
        """
        researcher = Researcher(llm=Mock(), search_tool=Mock())
        researcher.llm.invoke.return_value = response
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=["案例"],
            key_points=["事实"],
        )

        material = researcher._extract_material(
            outline,
            "案例",
            {"results": [{"url": "https://example.com/report", "content": "关键事实"}]},
            "",
        )

        self.assertEqual(material.sources, ["https://example.com/report"])
        self.assertEqual(researcher.llm.invoke.call_count, 1)

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
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=["案例"],
            key_points=["事实"],
        )

        prompt = build_material_user_prompt(
            outline,
            "案例",
            {"results": []},
            "",
        )

        self.assertIn("source_quality_hint", prompt)
        self.assertIn("优先从 tier_1/tier_2 中提炼核心事实", prompt)

    def test_search_section_invokes_tavily_each_time(self):
        researcher = Researcher(llm=Mock(), search_tool=Mock())
        researcher.search_tool.invoke.return_value = {
            "results": [
                {"url": "https://mckinsey.com/report.pdf", "content": "案例资料"}
            ]
        }
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=["案例"],
            key_points=["事实"],
        )

        first = researcher._search_section(outline, "案例", "")
        second = researcher._search_section(outline, "案例", "")

        self.assertEqual(researcher.search_tool.invoke.call_count, 2)
        self.assertEqual(first["results"][0]["url"], second["results"][0]["url"])

if __name__ == "__main__":
    unittest.main()
