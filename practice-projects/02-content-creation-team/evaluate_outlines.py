import argparse
import json

from crew.product_manager import ProductManager
from utils.outline_evaluation import OutlineQualityMetrics, evaluate_outline_quality


DEFAULT_TOPIC = "2026年AI Agent在企业数字转型中的实际应用案例：价值、边界与路径"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PM outlines with LLM and evaluate them only.")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="Report topic for PM outline generation.")
    parser.add_argument("--samples", type=int, default=3, help="Number of PM outlines to generate.")
    parser.add_argument("--raw", action="store_true", help="Call PM LLM once per sample without gate retry.")
    parser.add_argument("--json", action="store_true", help="Output full metrics as JSON.")
    args = parser.parse_args()

    metrics = generate_and_evaluate_outlines(args.topic, args.samples, raw=args.raw)

    if args.json:
        print(json.dumps([metric.to_dict() for metric in metrics], ensure_ascii=False, indent=2))
        return

    print(_markdown_table(metrics))
    print()
    for metric in metrics:
        issue_preview = "；".join(metric.issues[:3]) if metric.issues else "无明显确定性问题"
        print(f"- {metric.name}: {metric.title}")
        print(f"  章节: {' / '.join(metric.sections)}")
        print(f"  问题: {issue_preview}")


def generate_and_evaluate_outlines(
    topic: str,
    samples: int,
    planner_factory: type[ProductManager] = ProductManager,
    raw: bool = False,
) -> list[OutlineQualityMetrics]:
    """只触发 PM 的 LLM 大纲生成，不运行研究、写作和评审节点。"""
    metrics: list[OutlineQualityMetrics] = []
    for index in range(1, samples + 1):
        planner = planner_factory()
        if raw:
            outline = planner.generate_outline_once(topic)
        else:
            outline = planner.plan_content(topic)
        metrics.append(evaluate_outline_quality(outline, name=f"sample_{index}"))
    return metrics


def _markdown_table(metrics: list[OutlineQualityMetrics]) -> str:
    headers = [
        "样本",
        "总分",
        "章节",
        "角色",
        "案例章",
        "宽案例",
        "行业枚举",
        "叙事",
        "检索",
    ]
    rows = [
        [
            metric.name,
            str(metric.total_score),
            str(metric.section_count),
            str(sum(1 for covered in metric.role_coverage.values() if covered)),
            str(metric.case_sections),
            str(metric.broad_case_sections),
            str(metric.industry_listing_sections),
            str(metric.narrative_order_score),
            str(metric.searchability_score),
        ]
        for metric in metrics
    ]
    widths = [
        max(len(row[index]) for row in [headers, *rows])
        for index in range(len(headers))
    ]
    header_line = "| " + " | ".join(headers[index].ljust(widths[index]) for index in range(len(headers))) + " |"
    separator = "| " + " | ".join("-" * widths[index] for index in range(len(headers))) + " |"
    body_lines = [
        "| " + " | ".join(row[index].ljust(widths[index]) for index in range(len(headers))) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator, *body_lines])


if __name__ == "__main__":
    main()
