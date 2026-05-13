import argparse
import json
import re
import sys

from crew.product_manager import ProductManager
from utils.outline_evaluation import OutlineQualityMetrics, evaluate_outline_quality
from utils.outline_selection import (
    OutlineJudge,
    OutlineJudgeRankingItem,
    OutlineJudgeResult,
    build_outline_judge_prompt,
    judge_outline_candidates as _judge_outline_candidates,
    select_top_outline_metrics as _select_top_outline_metrics,
)


DEFAULT_TOPIC = "2026年AI Agent在企业数字转型中的实际应用案例：价值、边界与路径"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PM outlines with LLM and evaluate them only.")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="Report topic for PM outline generation.")
    parser.add_argument("--samples", type=int, default=3, help="Number of PM outlines to generate.")
    parser.add_argument("--raw", action="store_true", help="Call PM LLM once per sample without gate retry.")
    parser.add_argument("--select-top", type=int, default=0, help="Show only the top N ranked outlines after evaluation.")
    parser.add_argument("--llm-judge", action="store_true", help="Ask an LLM editor to judge the displayed outline candidates.")
    parser.add_argument("--json", action="store_true", help="Output full metrics as JSON.")
    args = parser.parse_args()

    _progress(f"开始生成候选大纲: samples={args.samples} raw={args.raw}")
    metrics = generate_and_evaluate_outlines(args.topic, args.samples, raw=args.raw, progress=True)
    display_metrics = select_top_outline_metrics(metrics, args.select_top) if args.select_top else metrics
    if args.select_top:
        _progress(f"本地排序完成: total={len(metrics)} selected={len(display_metrics)}")
    judge_result = judge_outline_candidates(args.topic, display_metrics, progress=True) if args.llm_judge and display_metrics else None

    if args.json:
        if judge_result:
            output = {
                "local_metrics": [metric.to_dict() for metric in display_metrics],
                "llm_judge": judge_result.model_dump(),
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(json.dumps([metric.to_dict() for metric in display_metrics], ensure_ascii=False, indent=2))
        return

    if args.select_top:
        print(f"已生成 {len(metrics)} 个候选大纲，按质量评分保留 Top {len(display_metrics)}。")
        print()
    print(_markdown_table(display_metrics))
    print()
    for rank, metric in enumerate(display_metrics, 1):
        label = f"Top {rank} ({metric.name})" if args.select_top else metric.name
        print(_candidate_detail(metric, label))

    if judge_result:
        print()
        print(_judge_report(judge_result))


def generate_and_evaluate_outlines(
    topic: str,
    samples: int,
    planner_factory: type[ProductManager] = ProductManager,
    raw: bool = False,
    progress: bool = False,
) -> list[OutlineQualityMetrics]:
    """只触发 PM 的 LLM 大纲生成，不运行研究、写作和评审节点。"""
    metrics: list[OutlineQualityMetrics] = []
    for index in range(1, samples + 1):
        if progress:
            _progress(f"生成候选大纲 {index}/{samples}...")
        planner = planner_factory()
        if raw:
            outline = planner.generate_outline_once(topic)
        else:
            outline = planner.plan_content(topic)
        metric = evaluate_outline_quality(outline, name=f"sample_{index}")
        metrics.append(metric)
        if progress:
            _progress(
                f"候选 {metric.name} 评分完成: score={metric.total_score} "
                f"sections={metric.section_count} cases={metric.case_sections} "
                f"specific={metric.specific_case_sections} generic={metric.generic_case_sections}"
            )
    return metrics


def select_top_outline_metrics(
    metrics: list[OutlineQualityMetrics],
    limit: int = 3,
) -> list[OutlineQualityMetrics]:
    return _select_top_outline_metrics(metrics, limit)


def judge_outline_candidates(
    topic: str,
    metrics: list[OutlineQualityMetrics],
    judge_factory: type[OutlineJudge] = OutlineJudge,
    progress: bool = False,
) -> OutlineJudgeResult:
    """对已筛选候选进行 LLM 主编评审。"""
    if progress:
        _progress(f"开始 LLM 主编评审: candidates={len(metrics)}")
    return _judge_outline_candidates(topic, metrics, judge_factory=judge_factory)


def _judge_report(result: OutlineJudgeResult) -> str:
    lines = ["LLM 主编评审："]
    for item in sorted(result.ranking, key=lambda ranking: ranking.rank):
        strengths = "；".join(item.strengths[:2]) if item.strengths else "未说明"
        risks = "；".join(item.risks[:2]) if item.risks else "未说明"
        lines.append(
            f"- Top {item.rank}: {item.candidate}，主编分 {item.editorial_score}，"
            f"优势：{strengths}；风险：{risks}；建议：{item.recommendation}"
        )
    lines.append(f"最终推荐: {result.best_candidate}")
    lines.append(f"理由: {result.selection_reason}")
    return "\n".join(lines)


def _candidate_detail(metric: OutlineQualityMetrics, label: str) -> str:
    strength_preview = "；".join(metric.strengths[:3]) if metric.strengths else "暂无明显优势"
    issue_preview = "；".join(metric.issues[:3]) if metric.issues else "无明显确定性问题"
    lines = [
        f"- {label}: {metric.title}",
        (
            f"  总分: {metric.total_score}；章节数: {metric.section_count}；"
            f"案例章节: {metric.case_sections}；具体案例章: {metric.specific_case_sections}；"
            f"泛案例章: {metric.generic_case_sections}；具体率: {metric.case_specificity_ratio:.2f}；"
            f"决策价值章: {metric.decision_value_sections}"
        ),
        f"  优点: {strength_preview}",
        "  章节:",
    ]
    lines.extend(
        f"    {section_index}. {_display_section_title(section)}"
        for section_index, section in enumerate(metric.sections, 1)
    )
    lines.append(f"  问题: {issue_preview}")
    return "\n".join(lines)


def _display_section_title(section: str) -> str:
    return re.sub(r"^\s*\d+[\.、]\s*", "", section).strip()


def _markdown_table(metrics: list[OutlineQualityMetrics]) -> str:
    headers = [
        "样本",
        "总分",
        "章节",
        "角色",
        "案例章",
        "具体案例",
        "具体率",
        "决策价值",
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
            str(metric.specific_case_sections),
            f"{metric.case_specificity_ratio:.2f}",
            str(metric.decision_value_sections),
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


def _progress(message: str) -> None:
    print(f"[outline-eval] {message}", file=sys.stderr)


if __name__ == "__main__":
    main()
