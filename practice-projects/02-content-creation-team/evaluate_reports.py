import argparse
import json
from pathlib import Path

from utils.report_evaluation import ReportQualityMetrics, evaluate_report_quality


DEFAULT_REPORTS = (
    "reports/final_report_20260512_144407.md",
    "reports/rejected_report_20260513_094340.md",
    "reports/rejected_report_20260513_113714.md",
    "reports/final_report_20260512_172821.md",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate generated report quality without LLM calls.")
    parser.add_argument("reports", nargs="*", help="Markdown report paths. Uses baseline samples if omitted.")
    parser.add_argument("--json", action="store_true", help="Output full metrics as JSON.")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent
    report_paths = [Path(path) for path in args.reports] or [project_dir / path for path in DEFAULT_REPORTS]
    metrics = [_evaluate_path(path) for path in report_paths]

    if args.json:
        print(json.dumps([metric.to_dict() for metric in metrics], ensure_ascii=False, indent=2))
        return

    print(_markdown_table(metrics))
    print()
    for metric in metrics:
        issue_preview = "；".join(metric.issues[:3]) if metric.issues else "无明显确定性问题"
        print(f"- {metric.name}: {issue_preview}")


def _evaluate_path(path: Path) -> ReportQualityMetrics:
    markdown = path.read_text(encoding="utf-8")
    return evaluate_report_quality(markdown, name=path.name)


def _markdown_table(metrics: list[ReportQualityMetrics]) -> str:
    headers = [
        "报告",
        "总分",
        "编辑",
        "证据",
        "字数",
        "章节",
        "小节",
        "列表",
        "引用",
        "均厚",
        "薄节",
        "案例节奏",
    ]
    rows = [
        [
            metric.name,
            str(metric.total_score),
            str(metric.editorial_score),
            str(metric.evidence_score),
            str(metric.units),
            str(metric.main_sections),
            str(metric.subsections),
            str(metric.list_items),
            str(metric.references),
            f"{metric.avg_subsection_units:.1f}",
            str(metric.thin_subsections),
            str(metric.case_rhythm_sections),
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
