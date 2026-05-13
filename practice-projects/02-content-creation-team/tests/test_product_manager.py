import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from crew.product_manager import ProductManager, validate_outline  # noqa: E402
from sop_artifacts import ContentOutline  # noqa: E402
from utils.outline_selection import OutlineJudgeRankingItem, OutlineJudgeResult  # noqa: E402


class FakeJudge:
    def judge(self, topic, metrics):
        return OutlineJudgeResult(
            ranking=[
                OutlineJudgeRankingItem(
                    candidate="sample_2",
                    rank=1,
                    editorial_score=93,
                    strengths=["更适合写作"],
                    risks=[],
                    recommendation="推荐",
                )
            ],
            best_candidate="sample_2",
            selection_reason="最后一个候选更好。",
        )


class ProductManagerTests(unittest.TestCase):
    def test_validate_outline_rejects_three_part_outline(self):
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=[
                "技术发展现状与趋势",
                "企业业务流程中的应用案例",
                "应用效果评估与未来展望",
            ],
            key_points=["趋势", "案例", "建议"],
        )

        issues = validate_outline(outline)

        self.assertTrue(any("章节数量" in issue for issue in issues))
        self.assertTrue(any("案例章节过于宽泛" in issue for issue in issues))

    def test_validate_outline_accepts_deep_report_outline(self):
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=[
                "行业背景与核心趋势",
                "技术架构与能力边界",
                "案例一：客户服务场景",
                "案例二：供应链场景",
                "案例三：风险管理场景",
                "实施路径与组织保障",
                "风险挑战与治理建议",
                "未来展望与行动建议",
            ],
            key_points=["趋势", "案例", "建议"],
        )

        self.assertEqual(validate_outline(outline), [])

    def test_validate_outline_rejects_outline_without_risk_section(self):
        outline = ContentOutline(
            title="测试报告",
            target_audience="管理者",
            sections=[
                "行业背景与核心趋势",
                "技术架构与能力边界",
                "市场数据与证据基础",
                "案例一：客户服务场景",
                "案例二：供应链场景",
                "实施路径与组织保障",
            ],
            key_points=["趋势", "案例", "建议"],
        )

        issues = validate_outline(outline)

        self.assertTrue(any("风险/挑战/限制/治理" in issue for issue in issues))

    def test_validate_outline_rejects_industry_listing_without_synthesis(self):
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

        issues = validate_outline(outline)

        self.assertTrue(any("行业枚举" in issue for issue in issues))

    def test_plan_content_retries_when_outline_is_too_shallow(self):
        shallow_response = Mock()
        shallow_response.content = """
        {
          "title": "测试报告",
          "target_audience": "管理者",
          "sections": ["现状", "应用案例", "未来展望"],
          "key_points": ["趋势", "案例", "建议"]
        }
        """
        good_response = Mock()
        good_response.content = """
        {
          "title": "测试报告",
          "target_audience": "管理者",
            "sections": [
              "行业背景与核心趋势",
              "技术架构与能力边界",
              "市场数据与证据基础",
              "案例一：客户服务场景",
              "案例二：供应链场景",
              "案例三：风险管理场景",
              "横向比较与模式归纳",
              "风险挑战与治理建议",
              "实施路径与组织保障"
            ],
          "key_points": ["趋势", "案例", "建议"]
        }
        """

        with patch("crew.product_manager.ChatOpenAI") as chat_openai:
            chat_openai.return_value.invoke.side_effect = [shallow_response, good_response]
            pm = ProductManager()
            outline = pm.plan_content("测试主题")

        self.assertEqual(len(outline.sections), 9)
        self.assertEqual(chat_openai.return_value.invoke.call_count, 2)

    def test_plan_outline_candidates_returns_llm_judge_default_choice(self):
        first_response = Mock()
        first_response.content = """
        {
          "title": "候选一",
          "target_audience": "管理者",
          "sections": [
            "背景与问题定义",
            "技术基础与能力边界",
            "案例一：智能客服Agent在零售行业的应用",
            "案例二：供应链Agent在制造业的库存优化",
            "案例三：金融合规Agent在银行业的动态风控",
            "横向比较与价值模式归纳",
            "风险挑战与治理边界",
            "实施路径与行动建议"
          ],
          "key_points": ["价值", "风险", "路径"]
        }
        """
        second_response = Mock()
        second_response.content = """
        {
          "title": "候选二",
          "target_audience": "管理者",
          "sections": [
            "背景与问题定义",
            "技术基础与能力边界",
            "案例一：智能客服Agent在零售行业的应用",
            "案例二：供应链Agent在制造业的库存优化",
            "案例三：金融合规Agent在银行业的动态风控",
            "横向比较与价值模式归纳",
            "价值量化框架：投资回报与隐藏成本",
            "风险挑战与治理边界",
            "实施路径与行动建议"
          ],
          "key_points": ["价值", "风险", "路径"]
        }
        """

        with patch("crew.product_manager.ChatOpenAI") as chat_openai, patch(
            "crew.product_manager.judge_outline_candidates",
            side_effect=lambda topic, metrics: FakeJudge().judge(topic, metrics),
        ):
            chat_openai.return_value.invoke.side_effect = [first_response, second_response]
            pm = ProductManager()
            outline, candidates, metrics, judge = pm.plan_outline_candidates(
                "测试主题",
                samples=2,
                top_n=2,
                llm_judge=True,
            )

        self.assertEqual(outline.title, "候选二")
        self.assertEqual(len(candidates), 2)
        self.assertEqual(len(metrics), 2)
        self.assertEqual(judge.best_candidate, "sample_2")


if __name__ == "__main__":
    unittest.main()
