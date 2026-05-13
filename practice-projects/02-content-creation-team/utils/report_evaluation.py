from dataclasses import asdict, dataclass, field
import re

from utils.draft_quality import (
    count_report_units,
    list_item_count,
    numbered_section_blocks,
    numbered_section_count,
    structural_keyword_hits,
    subsection_blocks,
    subsection_count,
)
from utils.references import parse_reference_urls
from utils.source_quality import infer_source_tier


TARGET_MAIN_SECTION_RANGE = (8, 10)
TARGET_SUBSECTION_RANGE = (15, 22)
TARGET_MIN_LIST_ITEMS = 25
TARGET_MIN_REFERENCES = 10
TARGET_MIN_AVG_SUBSECTION_UNITS = 100
TARGET_MAX_THIN_SUBSECTIONS = 2

KEYWORDS = (
    "成功案例",
    "失败案例",
    "失败教训",
    "挑战",
    "横向",
    "纵向",
    "实施路径",
    "最佳实践",
    "建议",
    "综合案例",
    "公开案例",
    "厂商案例",
    "证据边界",
)

CASE_SECTION_HINTS = ("案例", "应用", "客户", "供应链", "运营", "决策", "知识", "合规", "风控")
SUCCESS_HINTS = ("成功案例", "落地", "成效", "价值", "提升", "降低")
FAILURE_HINTS = ("失败", "挑战", "教训", "风险", "边界")
ANALYSIS_HINTS = ("横向", "纵向", "对比", "比较", "归纳", "分析")


@dataclass
class ReportQualityMetrics:
    """确定性报告质量指标，用于比较生成结果是否稳定变好。"""

    name: str
    units: int
    main_sections: int
    subsections: int
    list_items: int
    references: int
    table_count: int
    avg_subsection_units: float
    thin_subsections: int
    later_structured_sections: int
    case_rhythm_sections: int
    keyword_counts: dict[str, int] = field(default_factory=dict)
    source_tiers: dict[str, int] = field(default_factory=dict)
    editorial_score: int = 0
    evidence_score: int = 0
    total_score: int = 0
    strengths: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_report_quality(markdown: str, name: str = "") -> ReportQualityMetrics:
    """评估一篇 Markdown 报告的结构密度、编辑节奏和证据基础。"""
    body = _body(markdown)
    subsection_unit_values = [
        count_report_units(block)
        for _heading, block in subsection_blocks(markdown)
    ]
    reference_urls = parse_reference_urls(markdown)
    source_tiers = _source_tier_summary(reference_urls)

    metrics = ReportQualityMetrics(
        name=name,
        units=count_report_units(body),
        main_sections=numbered_section_count(markdown),
        subsections=subsection_count(markdown),
        list_items=list_item_count(markdown),
        references=len(reference_urls),
        table_count=_table_count(body),
        avg_subsection_units=_average(subsection_unit_values),
        thin_subsections=sum(1 for value in subsection_unit_values if value < 80),
        later_structured_sections=_later_structured_sections(markdown),
        case_rhythm_sections=_case_rhythm_sections(markdown),
        keyword_counts={keyword: body.count(keyword) for keyword in KEYWORDS},
        source_tiers=source_tiers,
    )

    metrics.editorial_score = _editorial_score(metrics)
    metrics.evidence_score = _evidence_score(metrics)
    metrics.total_score = metrics.editorial_score + metrics.evidence_score
    metrics.strengths = _strengths(metrics)
    metrics.issues = _issues(metrics)
    return metrics


def compare_reports(markdowns: dict[str, str]) -> list[ReportQualityMetrics]:
    """批量评估并按总分降序返回。"""
    return sorted(
        (
            evaluate_report_quality(markdown, name=name)
            for name, markdown in markdowns.items()
        ),
        key=lambda item: (item.total_score, item.editorial_score, item.evidence_score),
        reverse=True,
    )


def _body(markdown: str) -> str:
    return markdown.split("## 参考资料", 1)[0]


def _average(values: list[int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _table_count(markdown: str) -> int:
    lines = markdown.splitlines()
    count = 0
    for index in range(len(lines) - 1):
        if not lines[index].strip().startswith("|"):
            continue
        if re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index + 1]):
            count += 1
    return count


def _later_structured_sections(markdown: str) -> int:
    sections = numbered_section_blocks(markdown)
    if not sections:
        return 0
    later_sections = sections[len(sections) // 2:]
    return sum(1 for _heading, block in later_sections if subsection_count(block) > 0)


def _case_rhythm_sections(markdown: str) -> int:
    count = 0
    for heading, block in numbered_section_blocks(markdown):
        text = f"{heading}\n{block}"
        if not any(hint in heading for hint in CASE_SECTION_HINTS):
            continue
        if (
            any(hint in text for hint in SUCCESS_HINTS)
            and any(hint in text for hint in FAILURE_HINTS)
            and any(hint in text for hint in ANALYSIS_HINTS)
        ):
            count += 1
    return count


def _source_tier_summary(reference_urls: dict[int, str]) -> dict[str, int]:
    summary = {"tier_1": 0, "tier_2": 0, "tier_3": 0, "unknown": 0}
    for url in reference_urls.values():
        tier = infer_source_tier(url, "tier_3")
        if tier in summary:
            summary[tier] += 1
        else:
            summary["unknown"] += 1
    return summary


def _editorial_score(metrics: ReportQualityMetrics) -> int:
    keyword_hits = structural_keyword_hits_from_counts(metrics.keyword_counts)
    score = 0
    score += _band_score(metrics.main_sections, 8, 10, 4, 14, 12)
    score += _band_score(metrics.subsections, 15, 22, 5, 30, 14)
    score += min(14, round(metrics.list_items / TARGET_MIN_LIST_ITEMS * 14))
    score += _band_score(round(metrics.avg_subsection_units), 100, 180, 60, 260, 14)
    score += max(0, 10 - max(0, metrics.thin_subsections - TARGET_MAX_THIN_SUBSECTIONS) * 3)
    score += min(14, metrics.case_rhythm_sections * 4)
    score += min(8, keyword_hits["comparison"] * 3 + keyword_hits["practice"] * 3)
    score += _format_variety_score(metrics)
    return min(score, 80)


def structural_keyword_hits_from_counts(keyword_counts: dict[str, int]) -> dict[str, int]:
    return {
        "comparison": sum(keyword_counts.get(keyword, 0) for keyword in ("横向", "纵向")),
        "practice": sum(keyword_counts.get(keyword, 0) for keyword in ("实施路径", "最佳实践", "建议")),
    }


def _evidence_score(metrics: ReportQualityMetrics) -> int:
    high_quality_sources = metrics.source_tiers.get("tier_1", 0) + metrics.source_tiers.get("tier_2", 0)
    weak_sources = metrics.source_tiers.get("tier_3", 0)
    score = 0
    score += min(10, round(metrics.references / TARGET_MIN_REFERENCES * 10))
    score += min(10, high_quality_sources * 3)
    if metrics.references:
        weak_ratio = weak_sources / metrics.references
        score += max(0, round(5 * (1 - weak_ratio)))
    score += min(5, metrics.keyword_counts.get("证据边界", 0) * 3)
    if metrics.keyword_counts.get("综合案例", 0) > 5 and metrics.keyword_counts.get("公开案例", 0) == 0:
        score -= 5
    if metrics.keyword_counts.get("厂商案例", 0) > 0:
        score -= 3
    return min(max(score, 0), 20)


def _band_score(value: int, ideal_min: int, ideal_max: int, lower: int, upper: int, points: int) -> int:
    if ideal_min <= value <= ideal_max:
        return points
    if lower <= value < ideal_min:
        span = max(1, ideal_min - lower)
        return round(points * (value - lower) / span)
    if ideal_max < value <= upper:
        span = max(1, upper - ideal_max)
        return round(points * (upper - value) / span)
    return 0


def _format_variety_score(metrics: ReportQualityMetrics) -> int:
    score = 0
    if metrics.list_items >= TARGET_MIN_LIST_ITEMS:
        score += 2
    if metrics.subsections >= TARGET_SUBSECTION_RANGE[0]:
        score += 2
    if metrics.case_rhythm_sections >= 3:
        score += 2
    if metrics.later_structured_sections >= 2:
        score += 2
    if metrics.table_count > 0:
        score += 2
    return score


def _strengths(metrics: ReportQualityMetrics) -> list[str]:
    strengths: list[str] = []
    if TARGET_MAIN_SECTION_RANGE[0] <= metrics.main_sections <= TARGET_MAIN_SECTION_RANGE[1]:
        strengths.append("主章节数量接近目标样本")
    if TARGET_SUBSECTION_RANGE[0] <= metrics.subsections <= TARGET_SUBSECTION_RANGE[1]:
        strengths.append("三级小节数量充足且不过度")
    if metrics.list_items >= TARGET_MIN_LIST_ITEMS:
        strengths.append("列表密度较高，信息呈现有变化")
    if metrics.case_rhythm_sections >= 3:
        strengths.append("多个案例章节具备成功、挑战和分析节奏")
    if metrics.later_structured_sections >= 2:
        strengths.append("后半部分仍保留内部结构")
    return strengths


def _issues(metrics: ReportQualityMetrics) -> list[str]:
    issues: list[str] = []
    if metrics.main_sections < TARGET_MAIN_SECTION_RANGE[0] or metrics.main_sections > TARGET_MAIN_SECTION_RANGE[1]:
        issues.append(f"主章节数量 {metrics.main_sections} 偏离 8-10 的目标区间。")
    if metrics.subsections < TARGET_SUBSECTION_RANGE[0]:
        issues.append(f"三级小节数量 {metrics.subsections} 少于目标下限 {TARGET_SUBSECTION_RANGE[0]}。")
    if metrics.subsections > TARGET_SUBSECTION_RANGE[1]:
        issues.append(f"三级小节数量 {metrics.subsections} 高于目标上限 {TARGET_SUBSECTION_RANGE[1]}，可能标题堆叠。")
    if metrics.list_items < TARGET_MIN_LIST_ITEMS:
        issues.append(f"列表项数量 {metrics.list_items} 少于目标下限 {TARGET_MIN_LIST_ITEMS}，格式变化不足。")
    if metrics.avg_subsection_units < TARGET_MIN_AVG_SUBSECTION_UNITS:
        issues.append(f"小节平均厚度 {metrics.avg_subsection_units} 低于目标下限 {TARGET_MIN_AVG_SUBSECTION_UNITS}。")
    if metrics.thin_subsections > TARGET_MAX_THIN_SUBSECTIONS:
        issues.append(f"过薄小节 {metrics.thin_subsections} 个，多于目标上限 {TARGET_MAX_THIN_SUBSECTIONS}。")
    if metrics.case_rhythm_sections < 3:
        issues.append(f"具备成功/挑战/分析节奏的案例章节只有 {metrics.case_rhythm_sections} 个。")
    if metrics.later_structured_sections < 2:
        issues.append(f"后半部分只有 {metrics.later_structured_sections} 个主章节包含三级小节。")
    if metrics.references < TARGET_MIN_REFERENCES:
        issues.append(f"引用来源 {metrics.references} 条少于目标下限 {TARGET_MIN_REFERENCES}。")

    high_quality_sources = metrics.source_tiers.get("tier_1", 0) + metrics.source_tiers.get("tier_2", 0)
    if high_quality_sources < 3:
        issues.append(f"可识别的一手/准一手来源只有 {high_quality_sources} 条。")
    if metrics.keyword_counts.get("综合案例", 0) > 5 and metrics.keyword_counts.get("公开案例", 0) == 0:
        issues.append("综合案例较多且缺少公开案例标注，需要补充证据边界。")
    return issues
