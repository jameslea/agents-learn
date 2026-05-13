import sys
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from evaluate_outlines import (  # noqa: E402
    OutlineJudgeRankingItem,
    OutlineJudgeResult,
    _candidate_detail,
    _display_section_title,
    build_outline_judge_prompt,
    generate_and_evaluate_outlines,
    judge_outline_candidates,
    select_top_outline_metrics,
)
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


class FakeJudge:
    def judge(self, topic, metrics):
        return OutlineJudgeResult(
            ranking=[
                OutlineJudgeRankingItem(
                    candidate=metrics[0].name,
                    rank=1,
                    editorial_score=91,
                    strengths=["叙事完整"],
                    risks=["需要核验案例来源"],
                    recommendation="适合进入调研流程",
                )
            ],
            best_candidate=metrics[0].name,
            selection_reason="章节角色清晰，后续写作承载力更好。",
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

    def test_evaluate_outline_quality_rewards_specific_case_sections(self):
        concrete = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=[
                "行业背景与核心趋势",
                "技术基础与市场数据",
                "案例一：智能客服Agent在零售行业的自动退款与升级投诉处理",
                "案例二：制造业供应链Agent的需求预测与库存动态优化",
                "横向比较与模式归纳",
                "风险挑战与治理边界",
                "实施路径与行动建议",
            ],
            key_points=["价值", "风险", "路径"],
        )
        generic = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=[
                "行业背景与核心趋势",
                "技术基础与市场数据",
                "案例一：行业应用案例",
                "案例二：企业应用案例",
                "横向比较与模式归纳",
                "风险挑战与治理边界",
                "实施路径与行动建议",
            ],
            key_points=["价值", "风险", "路径"],
        )

        concrete_metrics = evaluate_outline_quality(concrete)
        generic_metrics = evaluate_outline_quality(generic)

        self.assertEqual(concrete_metrics.specific_case_sections, 2)
        self.assertEqual(generic_metrics.generic_case_sections, 2)
        self.assertGreater(concrete_metrics.total_score, generic_metrics.total_score)
        self.assertTrue(any("案例标题具备" in strength for strength in concrete_metrics.strengths))
        self.assertTrue(any("案例章节偏泛" in issue for issue in generic_metrics.issues))

    def test_generate_and_evaluate_outlines_triggers_pm_only_planner(self):
        metrics = generate_and_evaluate_outlines("测试主题", 2, planner_factory=FakePlanner)

        self.assertEqual(len(metrics), 2)
        self.assertEqual([metric.name for metric in metrics], ["sample_1", "sample_2"])
        self.assertTrue(all(metric.total_score >= 85 for metric in metrics))

    def test_generate_and_evaluate_outlines_can_call_raw_llm_path(self):
        metrics = generate_and_evaluate_outlines("测试主题", 1, planner_factory=FakePlanner, raw=True)

        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].name, "sample_1")

    def test_generate_and_evaluate_outlines_can_emit_progress(self):
        stderr = StringIO()

        with redirect_stderr(stderr):
            metrics = generate_and_evaluate_outlines("测试主题", 1, planner_factory=FakePlanner, progress=True)

        self.assertEqual(len(metrics), 1)
        self.assertIn("生成候选大纲 1/1", stderr.getvalue())
        self.assertIn("候选 sample_1 评分完成", stderr.getvalue())

    def test_select_top_outline_metrics_ranks_and_limits_candidates(self):
        weak = evaluate_outline_quality(
            ContentOutline(
                title="弱大纲",
                target_audience="管理者",
                sections=["现状", "应用案例", "未来展望"],
                key_points=["趋势", "案例", "建议"],
            ),
            name="weak",
        )
        good = evaluate_outline_quality(FakePlanner().plan_content("测试主题"), name="good")
        medium = evaluate_outline_quality(
            ContentOutline(
                title="中等大纲",
                target_audience="管理者",
                sections=[
                    "行业背景与核心趋势",
                    "技术基础与市场数据",
                    "客户服务场景案例",
                    "供应链运营场景案例",
                    "横向比较与模式归纳",
                    "风险挑战与治理边界",
                    "实施路径与行动建议",
                ],
                key_points=["价值", "风险", "路径"],
            ),
            name="medium",
        )

        selected = select_top_outline_metrics([weak, medium, good], limit=2)

        self.assertEqual([metric.name for metric in selected], ["good", "medium"])

    def test_select_top_outline_metrics_prefers_no_generic_cases_when_scores_tie(self):
        compact_specific = evaluate_outline_quality(
            ContentOutline(
                title="紧凑具体大纲",
                target_audience="管理者",
                sections=[
                    "问题定义：企业数字转型中AI Agent的角色与价值主张",
                    "技术基础：支撑AI Agent落地的关键能力栈与成熟度评估",
                    "案例场景一：智能客服与内部IT支持Agent——效率提升与用户满意度实证",
                    "案例场景二：供应链异常响应Agent——从被动报警到主动协同的转变",
                    "案例场景三：营销内容个性化生成Agent——ROI测算与合规边界",
                    "横向对比：不同部署模式的适用性与成本权衡",
                    "风险与挑战：数据安全、决策可解释性与系统故障的应急机制",
                    "实施路径：从试点到规模化部署的阶段性框架与关键成功因素",
                ],
                key_points=["价值", "风险", "路径"],
            ),
            name="compact_specific",
        )
        broader_with_generic = evaluate_outline_quality(
            ContentOutline(
                title="较宽大纲",
                target_audience="管理者",
                sections=[
                    "问题定义：AI Agent vs 传统自动化——数字转型的新逻辑与关键假设",
                    "技术基础：当前AI Agent的核心能力与能力边界",
                    "案例一：制造业——自主供应链调度Agent在库存优化中的实践与验证",
                    "案例二：金融服务业——多Agent协作在反欺诈与合规审查中的应用与风险",
                    "案例三：客户运营——对话式Agent在售前咨询场景的ROI评估与退化边界",
                    "横向比较：不同部署模式的适用场景与取舍",
                    "风险与约束：Agent行为黑箱、幻觉控制、数据隐私与监管合规的挑战",
                    "证据与可信度：现有案例的可验证性分析——哪些效果可归因Agent？",
                    "实施路径：企业引入AI Agent的成熟度评估与分阶段策略",
                    "未来展望：从工具到协作者——AI Agent演进的争议与共识",
                ],
                key_points=["价值", "风险", "路径"],
            ),
            name="broader_with_generic",
        )

        selected = select_top_outline_metrics([broader_with_generic, compact_specific], limit=2)

        self.assertEqual(compact_specific.generic_case_sections, 0)
        self.assertEqual(broader_with_generic.generic_case_sections, 1)
        self.assertEqual(selected[0].name, "compact_specific")

    def test_select_top_outline_metrics_prefers_decision_value_when_case_quality_ties(self):
        baseline = evaluate_outline_quality(
            ContentOutline(
                title="基础大纲",
                target_audience="管理者",
                sections=[
                    "问题定义：AI Agent在数字转型中的角色与价值主张",
                    "技术基础：架构演进与关键能力",
                    "案例一：智能客服Agent在零售业的应用",
                    "案例二：供应链优化Agent在制造业的实践",
                    "案例三：财务流程自动化Agent在金融业的应用",
                    "横向比较：不同行业Agent应用模式的异同与归纳",
                    "风险挑战：可验证性、可靠性、安全与伦理边界",
                    "实施路径：企业部署AI Agent的决策框架与步骤",
                    "结论与展望：从工具到伙伴的演进与建议",
                ],
                key_points=["价值", "风险", "路径"],
            ),
            name="baseline",
        )
        with_value = evaluate_outline_quality(
            ContentOutline(
                title="价值大纲",
                target_audience="管理者",
                sections=[
                    "背景与问题定义：从自动化到自主决策的转型浪潮",
                    "AI Agent的技术基础与能力演进",
                    "案例一：供应链智能调度Agent在物流行业的实时优化",
                    "案例二：金融领域合规审核与风险控制Agent",
                    "案例三：面向客户服务的自主Agent平台",
                    "横向比较：AI Agent与传统RPA及生成式AI的核心差异",
                    "价值量化框架：如何评估Agent项目的投资回报与隐藏成本",
                    "部署风险与验证边界：幻觉、脆弱性及可审计性挑战",
                    "实施路径与组织准备：从试点到规模化的关键步骤",
                    "结论与展望：企业在Agent时代的竞争格局",
                ],
                key_points=["价值", "风险", "路径"],
            ),
            name="with_value",
        )

        selected = select_top_outline_metrics([baseline, with_value], limit=2)

        self.assertGreater(with_value.decision_value_sections, baseline.decision_value_sections)
        self.assertEqual(selected[0].name, "with_value")

    def test_build_outline_judge_prompt_keeps_llm_as_judge_only(self):
        metric = evaluate_outline_quality(FakePlanner().plan_content("测试主题"), name="sample_1")

        prompt = build_outline_judge_prompt("测试主题", [metric])

        self.assertIn("不要改写大纲", prompt)
        self.assertIn("案例章节是否具体、可调研、可核验", prompt)
        self.assertIn('"candidate": "sample_1"', prompt)
        self.assertIn("editorial_score", prompt)

    def test_judge_outline_candidates_uses_injected_judge(self):
        metric = evaluate_outline_quality(FakePlanner().plan_content("测试主题"), name="sample_1")

        result = judge_outline_candidates("测试主题", [metric], judge_factory=FakeJudge)

        self.assertEqual(result.best_candidate, "sample_1")
        self.assertEqual(result.ranking[0].editorial_score, 91)

    def test_candidate_detail_formats_sections_as_numbered_list(self):
        metric = evaluate_outline_quality(FakePlanner().plan_content("测试主题"), name="sample_1")

        detail = _candidate_detail(metric, "Top 1 (sample_1)")

        self.assertIn("  章节:\n    1. 第一章", detail)
        self.assertNotIn(" / 第二章", detail)

    def test_candidate_detail_strips_existing_numeric_section_prefix(self):
        self.assertEqual(_display_section_title("1. 问题定义：AI Agent"), "问题定义：AI Agent")
        self.assertEqual(_display_section_title("2、技术基础"), "技术基础")


if __name__ == "__main__":
    unittest.main()
