import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from utils.report_evaluation import evaluate_report_quality  # noqa: E402


def sample_report(list_items: int = 30, subsections: int = 18) -> str:
    sections = ["# 测试报告\n"]
    for section_index in range(1, 10):
        sections.append(f"## 第{section_index}章：应用案例与路径\n")
        if section_index in {3, 4, 5, 6, 7}:
            sections.append("### 成功案例\n")
            sections.append("成功案例展示了落地成效、价值提升和组织协同。" * 8 + "\n")
            sections.append("### 失败教训\n")
            sections.append("失败教训说明了挑战、风险边界和治理约束。" * 8 + "\n")
            sections.append("### 横向对比\n")
            sections.append("横向对比与纵向分析帮助识别适用条件和实施路径。" * 8 + "\n")
        elif section_index <= subsections:
            sections.append("### 实施路径\n")
            sections.append("最佳实践、建议和证据边界共同构成高管可执行判断。" * 8 + "\n")

    sections.append("\n".join(f"- 建议清单 {index}[1]" for index in range(list_items)))
    sections.append("\n## 参考资料\n")
    sections.append("\n".join(f"[{index}] https://example.com/report-{index}" for index in range(1, 12)))
    return "\n".join(sections)


class ReportEvaluationTests(unittest.TestCase):
    def test_evaluate_report_quality_captures_structural_metrics(self):
        metrics = evaluate_report_quality(sample_report(), name="sample")

        self.assertEqual(metrics.name, "sample")
        self.assertEqual(metrics.main_sections, 9)
        self.assertGreaterEqual(metrics.subsections, 15)
        self.assertGreaterEqual(metrics.list_items, 25)
        self.assertGreaterEqual(metrics.case_rhythm_sections, 3)
        self.assertGreater(metrics.editorial_score, 55)

    def test_evaluate_report_quality_penalizes_thin_title_stacking(self):
        thin_report = (
            "# 测试报告\n\n"
            + "\n".join(
                f"## 第{index}章：案例\n### 成功案例\n短。\n### 失败教训\n短。\n### 横向对比\n短。"
                for index in range(1, 9)
            )
            + "\n\n## 参考资料\n[1] https://example.com/report\n"
        )

        metrics = evaluate_report_quality(thin_report, name="thin")

        self.assertGreater(metrics.thin_subsections, 2)
        self.assertTrue(any("过薄小节" in issue for issue in metrics.issues))

    def test_evaluate_report_quality_warns_about_fragmented_lists(self):
        metrics = evaluate_report_quality(sample_report(list_items=61), name="fragmented")

        self.assertGreater(metrics.list_items, 50)
        self.assertTrue(any("列表项数量 61 过多" in issue for issue in metrics.issues))

    def test_historical_samples_match_reading_order_when_available(self):
        better_path = PROJECT_DIR / "reports/rejected_report_20260513_094340.md"
        worse_path = PROJECT_DIR / "reports/rejected_report_20260513_113714.md"
        if not better_path.exists() or not worse_path.exists():
            self.skipTest("historical generated reports are not available")

        better = evaluate_report_quality(better_path.read_text(encoding="utf-8"), name=better_path.name)
        worse = evaluate_report_quality(worse_path.read_text(encoding="utf-8"), name=worse_path.name)

        self.assertGreater(better.editorial_score, worse.editorial_score)
        self.assertGreater(better.list_items, worse.list_items)
        self.assertGreater(better.avg_subsection_units, worse.avg_subsection_units)

    def test_target_sample_shows_editorial_strength_and_evidence_warning_when_available(self):
        target_path = PROJECT_DIR / "reports/final_report_20260512_144407.md"
        if not target_path.exists():
            self.skipTest("target generated report is not available")

        metrics = evaluate_report_quality(target_path.read_text(encoding="utf-8"), name=target_path.name)

        self.assertGreaterEqual(metrics.main_sections, 8)
        self.assertGreaterEqual(metrics.subsections, 15)
        self.assertGreaterEqual(metrics.list_items, 25)
        self.assertTrue(any("综合案例" in issue for issue in metrics.issues))


if __name__ == "__main__":
    unittest.main()
