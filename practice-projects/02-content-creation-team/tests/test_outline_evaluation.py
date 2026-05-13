import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from evaluate_outlines import generate_and_evaluate_outlines  # noqa: E402
from sop_artifacts import ContentOutline  # noqa: E402
from utils.outline_evaluation import evaluate_outline_quality, validate_outline  # noqa: E402


class FakePlanner:
    def generate_outline_once(self, topic: str) -> ContentOutline:
        return self.plan_content(topic)

    def plan_content(self, topic: str) -> ContentOutline:
        return ContentOutline(
            title=f"{topic}：价值、边界与路径",
            target_audience="企业高管和数字化负责人",
            sections=[
                "第一章：技术背景与企业转型问题定义",
                "第二章：能力架构、市场数据与证据基础",
                "第三章：客户服务场景中的AI Agent落地案例",
                "第四章：供应链与运营流程中的AI Agent实践案例",
                "第五章：数据驱动决策与知识管理场景案例",
                "第六章：横向比较与规模化落地模式归纳",
                "第七章：风险挑战、治理边界与失败教训",
                "第八章：实施路径、组织策略与高管行动建议",
            ],
            key_points=["价值判断", "证据边界", "实施路径"],
        )


class OutlineEvaluationTests(unittest.TestCase):
    def test_evaluate_outline_quality_scores_editorial_outline(self):
        outline = FakePlanner().plan_content("测试主题")

        metrics = evaluate_outline_quality(outline, name="good")

        self.assertEqual(metrics.name, "good")
        self.assertEqual(metrics.section_count, 8)
        self.assertTrue(all(metrics.role_coverage.values()))
        self.assertGreaterEqual(metrics.total_score, 85)
        self.assertEqual(metrics.issues, [])

    def test_validate_outline_rejects_shallow_outline(self):
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=["现状", "应用案例", "未来展望"],
            key_points=["趋势", "案例", "建议"],
        )

        issues = validate_outline(outline)
        metrics = evaluate_outline_quality(outline)

        self.assertTrue(any("章节数量" in issue for issue in issues))
        self.assertLess(metrics.total_score, 60)

    def test_evaluate_outline_quality_penalizes_industry_listing(self):
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=[
                "行业背景与核心趋势",
                "技术基础与市场数据",
                "制造行业应用案例",
                "金融行业应用案例",
                "医疗行业应用案例",
                "零售行业应用案例",
                "物流行业应用案例",
                "风险挑战与治理建议",
                "实施路径与未来展望",
            ],
            key_points=["趋势", "案例", "建议"],
        )

        metrics = evaluate_outline_quality(outline)

        self.assertTrue(any("行业枚举" in issue for issue in metrics.issues))

    def test_evaluate_outline_quality_does_not_miscount_risk_scenario_as_case(self):
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=[
                "1. 问题界定：AI Agent在数字转型中的角色与价值假设",
                "2. 技术基础：自主决策、工具调用与知识集成能力现状",
                "3. 案例研究一：客户服务Agent——人机协作模式与效能实测",
                "4. 案例研究二：供应链优化Agent——动态调度与异常处理",
                "5. 案例研究三：企业内部知识管理Agent——从检索到自动摘要",
                "6. 横向比较：不同行业场景中Agent应用模式的共性与差异",
                "7. 风险与挑战：可验证性、数据安全与失控场景分析",
                "8. 实施路径：现有系统集成、Agent编排与组织变革建议",
                "9. 前瞻与建议：标准化机遇、伦理框架与生态构建",
            ],
            key_points=["价值判断", "风险边界", "实施路径"],
        )

        metrics = evaluate_outline_quality(outline)

        self.assertEqual(metrics.case_sections, 3)
        self.assertGreaterEqual(metrics.narrative_order_score, 16)
        self.assertFalse(any("叙事顺序" in issue for issue in metrics.issues))

    def test_generate_and_evaluate_outlines_triggers_pm_only_planner(self):
        metrics = generate_and_evaluate_outlines("测试主题", 2, planner_factory=FakePlanner)

        self.assertEqual(len(metrics), 2)
        self.assertEqual([metric.name for metric in metrics], ["sample_1", "sample_2"])
        self.assertTrue(all(metric.total_score >= 85 for metric in metrics))

    def test_generate_and_evaluate_outlines_can_call_raw_llm_path(self):
        metrics = generate_and_evaluate_outlines("测试主题", 1, planner_factory=FakePlanner, raw=True)

        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].name, "sample_1")


if __name__ == "__main__":
    unittest.main()
