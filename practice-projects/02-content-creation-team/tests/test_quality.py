import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from utils.quality import (  # noqa: E402
    has_report_title,
    infer_source_tier,
    list_item_count,
    normalize_draft_references,
    numbered_section_blocks,
    numbered_section_count,
    parse_reference_urls,
    ranked_source_records,
    source_quality_summary,
    source_quality_warnings,
    structural_keyword_hits,
    subsection_blocks,
    subsection_count,
    unique_urls,
    validate_draft,
    validate_research_report,
)
from sop_artifacts import DraftContent, ResearchMaterial, ResearchReport  # noqa: E402


def valid_report_body(cited_number: int = 1) -> str:
    section_text = f"这是一个有效段落[{cited_number}]。" * 500
    subsection_text = f"该小节补充案例背景、关键指标、约束条件和管理启示[{cited_number}]。" * 8
    return (
        "# 测试报告\n\n"
        f"## 一、背景\n{section_text}\n\n"
        "### 横向对比\n"
        f"{subsection_text}\n"
        f"- 背景判断一[{cited_number}]\n"
        f"- 背景判断二[{cited_number}]\n\n"
        f"## 二、案例\n{section_text}\n\n"
        "### 成功案例\n"
        f"{subsection_text}\n"
        f"- 成功案例指标[{cited_number}]\n"
        f"- 公开案例证据[{cited_number}]\n\n"
        "### 失败教训\n"
        f"{subsection_text}\n"
        f"- 失败教训一[{cited_number}]\n"
        f"- 挑战与教训二[{cited_number}]\n\n"
        f"## 三、分析\n{section_text}\n\n"
        "### 实施路径\n"
        f"{subsection_text}\n"
        f"- 最佳实践一[{cited_number}]\n"
        f"- 行动建议二[{cited_number}]\n"
    )


def flat_report_body(cited_number: int = 1) -> str:
    section_text = f"这是一个只有连续段落的有效段落[{cited_number}]。" * 500
    return (
        "# 测试报告\n\n"
        f"## 一、背景\n{section_text}\n\n"
        f"## 二、案例\n{section_text}\n\n"
        f"## 三、分析\n{section_text}\n"
    )


def imbalanced_report_body(cited_number: int = 1) -> str:
    section_text = f"这是用于撑起长报告的段落[{cited_number}]。" * 150
    subsection_text = f"这个小节有足够的信息密度和分析展开[{cited_number}]。" * 10
    sections = []
    for index in range(1, 11):
        sections.append(f"## {index}、章节{index}\n{section_text}\n")
        if index <= 5:
            sections.append(
                "### 成功案例\n"
                f"{subsection_text}\n"
                f"- 公开案例证据[{cited_number}]\n"
                f"- 失败教训总结[{cited_number}]\n"
                "### 横向对比\n"
                f"{subsection_text}\n"
                f"- 最佳实践[{cited_number}]\n"
            )
    return "# 测试报告\n\n" + "\n".join(sections)


def thin_subsection_report_body(cited_number: int = 1) -> str:
    section_text = f"这是用于撑起长报告的段落[{cited_number}]。" * 150
    sections = []
    for index in range(1, 11):
        sections.append(f"## {index}、章节{index}\n{section_text}\n")
        if index in {2, 3, 4, 5, 8, 9}:
            sections.append(
                "### 成功案例\n"
                f"- 公开案例[{cited_number}]\n"
                "### 失败教训\n"
                f"- 风险[{cited_number}]\n"
                "### 横向对比\n"
                f"- 最佳实践[{cited_number}]\n"
            )
    return "# 测试报告\n\n" + "\n".join(sections)


class QualityTests(unittest.TestCase):
    def test_unique_urls_preserves_order(self):
        self.assertEqual(
            unique_urls(["https://a.example", "https://b.example", "https://a.example"]),
            ["https://a.example", "https://b.example"],
        )

    def test_validate_research_report_rejects_missing_sources(self):
        report = ResearchReport(
            materials=[
                ResearchMaterial(
                    section_name="案例",
                    raw_data="关键事实（来源1）",
                    sources=[],
                )
            ]
        )

        issues = validate_research_report(report)

        self.assertTrue(any("缺少来源 URL" in issue for issue in issues))

    def test_validate_research_report_checks_source_number_range(self):
        report = ResearchReport(
            materials=[
                ResearchMaterial(
                    section_name="案例",
                    raw_data="关键事实（来源2）",
                    sources=["https://example.com/report"],
                )
            ]
        )

        issues = validate_research_report(report)

        self.assertTrue(any("来源编号超过 sources 数量" in issue for issue in issues))

    def test_parse_reference_urls(self):
        references = parse_reference_urls(
            "## 参考资料\n[1] https://example.com/a\n[2] https://example.com/b\n"
        )

        self.assertEqual(
            references,
            {1: "https://example.com/a", 2: "https://example.com/b"},
        )

    def test_validate_draft_accepts_reference_closure(self):
        body = valid_report_body(1)
        draft = DraftContent(
            title="测试报告",
            content_markdown=body + "\n\n## 参考资料\n[1] https://example.com/report\n",
            word_count=3200,
            citations=["https://example.com/report"],
        )

        self.assertEqual(validate_draft(draft), [])

    def test_validate_draft_rejects_flat_long_report_structure(self):
        body = flat_report_body(1)
        draft = DraftContent(
            title="测试报告",
            content_markdown=body + "\n\n## 参考资料\n[1] https://example.com/report\n",
            word_count=3200,
            citations=["https://example.com/report"],
        )

        issues = validate_draft(draft)

        self.assertTrue(any("三级小节数量" in issue for issue in issues))
        self.assertTrue(any("列表项数量" in issue for issue in issues))
        self.assertTrue(any("案例结构不足" in issue for issue in issues))

    def test_structure_helpers_count_subsections_lists_and_keywords(self):
        body = valid_report_body(1)

        self.assertGreaterEqual(subsection_count(body), 4)
        self.assertGreaterEqual(list_item_count(body), 5)
        self.assertEqual(len(numbered_section_blocks(body)), 3)
        self.assertEqual(len(subsection_blocks(body)), 4)
        self.assertEqual(
            structural_keyword_hits(body),
            {"case": 4, "comparison": 1, "practice": 3},
        )

    def test_validate_draft_rejects_imbalanced_subsection_distribution(self):
        body = imbalanced_report_body(1)
        draft = DraftContent(
            title="测试报告",
            content_markdown=body + "\n\n## 参考资料\n[1] https://example.com/report\n",
            word_count=4200,
            citations=["https://example.com/report"],
        )

        issues = validate_draft(draft)

        self.assertTrue(any("后半部分" in issue for issue in issues))

    def test_validate_draft_rejects_thin_subsections(self):
        body = thin_subsection_report_body(1)
        draft = DraftContent(
            title="测试报告",
            content_markdown=body + "\n\n## 参考资料\n[1] https://example.com/report\n",
            word_count=4200,
            citations=["https://example.com/report"],
        )

        issues = validate_draft(draft)

        self.assertTrue(any("三级小节内容过薄过多" in issue for issue in issues))

    def test_validate_draft_rejects_missing_reference_entry(self):
        body = valid_report_body(2)
        draft = DraftContent(
            title="测试报告",
            content_markdown=body + "\n\n## 参考资料\n[1] https://example.com/report\n",
            word_count=3200,
            citations=["https://example.com/report"],
        )

        issues = validate_draft(draft)

        self.assertTrue(any("缺少参考资料条目" in issue for issue in issues))

    def test_normalize_draft_references_removes_unused_references(self):
        body = valid_report_body(1)
        draft = DraftContent(
            title="测试报告",
            content_markdown=(
                body
                + "\n\n## 参考资料\n"
                + "[1] https://example.com/used\n"
                + "[2] https://example.com/unused\n"
            ),
            word_count=3200,
            citations=["https://example.com/used", "https://example.com/unused"],
        )

        normalized = normalize_draft_references(draft)

        self.assertIn("[1] https://example.com/used", normalized.content_markdown)
        self.assertNotIn("[2] https://example.com/unused", normalized.content_markdown)
        self.assertEqual(normalized.citations, ["https://example.com/used"])
        self.assertEqual(validate_draft(normalized), [])

    def test_normalize_draft_references_renumbers_references(self):
        section_text = "这是一个有效段落[4]，还有一个事实[10]。" * 500
        subsection_text = "这个小节补充分析背景、证据限制、案例启示和后续行动建议[4][10]。" * 8
        body = (
            "# 测试报告\n\n"
            f"## 一、背景\n{section_text}\n\n"
            "### 横向对比\n"
            f"{subsection_text}\n"
            "- 背景判断[4]\n"
            "- 演进分析[10]\n\n"
            f"## 二、案例\n{section_text}\n\n"
            "### 成功案例\n"
            f"{subsection_text}\n"
            "- 公开案例指标[4]\n"
            "- 成功案例限制[10]\n\n"
            "### 失败教训\n"
            f"{subsection_text}\n"
            "- 挑战与教训[4]\n"
            "- 失败教训总结[10]\n\n"
            f"## 三、分析\n{section_text}\n\n"
            "### 实施路径\n"
            f"{subsection_text}\n"
            "- 最佳实践[4]\n"
            "- 行动建议[10]\n"
        )
        draft = DraftContent(
            title="测试报告",
            content_markdown=(
                body
                + "\n\n## 参考资料\n"
                + "[4] https://example.com/four\n"
                + "[10] https://example.com/ten\n"
            ),
            word_count=3200,
            citations=["https://example.com/four", "https://example.com/ten"],
        )

        normalized = normalize_draft_references(draft)

        self.assertIn("[1] https://example.com/four", normalized.content_markdown)
        self.assertIn("[2] https://example.com/ten", normalized.content_markdown)
        self.assertNotIn("[4] https://example.com/four", normalized.content_markdown)
        self.assertEqual(normalized.citations, ["https://example.com/four", "https://example.com/ten"])
        self.assertEqual(validate_draft(normalized), [])

    def test_normalize_draft_references_numbers_bare_reference_urls(self):
        body = valid_report_body(1)
        draft = DraftContent(
            title="测试报告",
            content_markdown=(
                body
                + "\n\n## 参考资料\n"
                + "https://example.com/used\n"
                + "https://example.com/unused\n"
            ),
            word_count=3200,
            citations=["https://example.com/used", "https://example.com/unused"],
        )

        normalized = normalize_draft_references(draft)

        self.assertIn("[1] https://example.com/used", normalized.content_markdown)
        self.assertNotIn("https://example.com/unused", normalized.content_markdown)
        self.assertEqual(normalized.citations, ["https://example.com/used"])
        self.assertEqual(validate_draft(normalized), [])

    def test_source_quality_summary_and_warning(self):
        report = ResearchReport(
            materials=[
                ResearchMaterial(
                    section_name="案例",
                    raw_data="事实（来源1）",
                    sources=["https://example.com/a", "https://example.com/b"],
                    source_quality=["tier_1", "tier_3"],
                    source_notes=["官方报告", "博客辅助"],
                )
            ]
        )

        self.assertEqual(
            source_quality_summary(report),
            {"tier_1": 1, "tier_2": 0, "tier_3": 1, "unknown": 0},
        )
        self.assertTrue(source_quality_warnings(report, min_high_quality=3))

    def test_report_title_and_numbered_section_helpers(self):
        markdown = valid_report_body(1) + "\n\n## 参考资料\n[1] https://example.com/report\n"

        self.assertTrue(has_report_title(markdown))
        self.assertEqual(numbered_section_count(markdown), 3)

    def test_ranked_source_records_prioritizes_source_quality_and_caps(self):
        report = ResearchReport(
            materials=[
                ResearchMaterial(
                    section_name="第一节",
                    raw_data="事实（来源1）（来源2）",
                    sources=["https://example.com/blog", "https://example.com/official"],
                    source_quality=["tier_3", "tier_1"],
                    source_notes=["博客", "官方报告"],
                ),
                ResearchMaterial(
                    section_name="第二节",
                    raw_data="事实（来源1）（来源2）",
                    sources=["https://example.com/media", "https://example.com/vendor"],
                    source_quality=["tier_2", "tier_3"],
                    source_notes=["权威媒体", "厂商文章"],
                ),
            ]
        )

        records = ranked_source_records(report, max_sources=2)

        self.assertEqual(
            [(record["url"], record["tier"]) for record in records],
            [
                ("https://example.com/official", "tier_1"),
                ("https://example.com/media", "tier_2"),
            ],
        )

    def test_infer_source_tier_downgrades_community_sources(self):
        self.assertEqual(
            infer_source_tier("https://blog.csdn.net/example/article/details/1", "tier_1"),
            "tier_3",
        )

    def test_infer_source_tier_downgrades_vendor_and_aggregator_sources(self):
        weak_urls = [
            "https://caifuhao.eastmoney.com/news/20260416145351071897050",
            "https://www.meiqia.com/blog/2026nian-ai-agentfa-zhan-qu-shi",
            "https://www.beisen.com/special/242.html",
            "https://www.yonyou.com/news/4298",
        ]

        for url in weak_urls:
            with self.subTest(url=url):
                self.assertEqual(infer_source_tier(url, "tier_1"), "tier_3")

    def test_infer_source_tier_upgrades_report_like_sources(self):
        self.assertEqual(
            infer_source_tier("https://assets.kpmg.com/content/report.pdf", "tier_3"),
            "tier_1",
        )

    def test_ranked_source_records_uses_effective_source_tier(self):
        report = ResearchReport(
            materials=[
                ResearchMaterial(
                    section_name="案例",
                    raw_data="事实（来源1）（来源2）",
                    sources=[
                        "https://blog.csdn.net/example/article/details/1",
                        "https://assets.kpmg.com/content/report.pdf",
                    ],
                    source_quality=["tier_1", "tier_3"],
                    source_notes=["模型误标高等级", "模型误标低等级"],
                )
            ]
        )

        records = ranked_source_records(report)

        self.assertEqual(
            [(record["url"], record["tier"]) for record in records],
            [
                ("https://assets.kpmg.com/content/report.pdf", "tier_1"),
                ("https://blog.csdn.net/example/article/details/1", "tier_3"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
