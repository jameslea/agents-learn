from dataclasses import asdict, dataclass, field

from sop_artifacts import ContentOutline


MIN_OUTLINE_SECTIONS = 6
MAX_OUTLINE_SECTIONS = 10
TARGET_OUTLINE_SECTIONS = (8, 10)

BACKGROUND_KEYWORDS = ("背景", "趋势", "现状", "问题", "概览", "定义")
EVIDENCE_KEYWORDS = ("技术", "架构", "能力", "市场", "数据", "证据", "格局", "基础")
CASE_KEYWORDS = ("案例", "场景", "实践", "应用", "落地")
SYNTHESIS_KEYWORDS = ("比较", "对比", "归纳", "模式", "框架", "评估", "总结")
RISK_KEYWORDS = ("风险", "挑战", "限制", "治理", "合规", "失败", "教训")
ACTION_KEYWORDS = ("实施", "路径", "建议", "策略", "路线图", "展望", "决策", "高管")
INDUSTRY_ONLY_KEYWORDS = ("制造", "金融", "医疗", "零售", "物流", "供应链", "教育", "能源", "政务", "人力资源")

BROAD_CASE_HINTS = ("应用案例", "业务案例", "行业案例", "企业应用", "实际应用")


@dataclass
class OutlineQualityMetrics:
    """不进入研究和写作流程，单独评估 PM 大纲质量。"""

    name: str
    title: str
    target_audience: str
    section_count: int
    key_point_count: int
    role_coverage: dict[str, bool]
    case_sections: int
    broad_case_sections: int
    industry_listing_sections: int
    narrative_order_score: int
    searchability_score: int
    total_score: int = 0
    strengths: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_outline_quality(outline: ContentOutline, name: str = "") -> OutlineQualityMetrics:
    """给 ContentOutline 打分，便于比较多次 PM LLM 输出是否稳定。"""
    role_coverage = _role_coverage(outline.sections)
    metrics = OutlineQualityMetrics(
        name=name,
        title=outline.title,
        target_audience=outline.target_audience,
        section_count=len(outline.sections),
        key_point_count=len(outline.key_points),
        role_coverage=role_coverage,
        case_sections=_case_section_count(outline.sections),
        broad_case_sections=_broad_case_section_count(outline.sections),
        industry_listing_sections=_count_sections(outline.sections, INDUSTRY_ONLY_KEYWORDS),
        narrative_order_score=_narrative_order_score(outline.sections),
        searchability_score=_searchability_score(outline.sections),
        sections=list(outline.sections),
    )
    metrics.total_score = _total_score(metrics)
    metrics.strengths = _strengths(metrics)
    metrics.issues = _issues(metrics)
    return metrics


def validate_outline(outline: ContentOutline) -> list[str]:
    """PM 门禁仍返回问题列表；评分器用于更细粒度比较。"""
    metrics = evaluate_outline_quality(outline)
    blocking_issues: list[str] = []

    if metrics.section_count < MIN_OUTLINE_SECTIONS:
        blocking_issues.append(
            f"章节数量 {metrics.section_count} 少于 {MIN_OUTLINE_SECTIONS}，容易导致报告过于粗略。"
        )

    if metrics.section_count > MAX_OUTLINE_SECTIONS:
        blocking_issues.append(
            f"章节数量 {metrics.section_count} 超过 {MAX_OUTLINE_SECTIONS}，容易导致调研范围失控。"
        )

    if metrics.section_count <= MIN_OUTLINE_SECTIONS and metrics.broad_case_sections:
        blocking_issues.append("案例章节过于宽泛，建议拆成多个可独立调研的行业、场景或对象章节。")

    role_names = {
        "background": "背景/趋势/问题定义",
        "evidence": "证据基础/技术基础/市场数据",
        "case": "案例/场景/实践分析",
        "risk": "风险/挑战/限制/治理",
        "action": "实施路径/策略建议/未来展望",
    }
    for role_key, role_name in role_names.items():
        if not metrics.role_coverage[role_key]:
            blocking_issues.append(f"缺少“{role_name}”类章节。")

    if _is_industry_listing_without_synthesis(metrics):
        blocking_issues.append("大纲偏行业枚举，缺少横向比较、模式归纳或评估框架章节。")

    return blocking_issues


def _role_coverage(sections: list[str]) -> dict[str, bool]:
    return {
        "background": _has_section(sections, BACKGROUND_KEYWORDS),
        "evidence": _has_section(sections, EVIDENCE_KEYWORDS),
        "case": _case_section_count(sections) > 0,
        "synthesis": _has_section(sections, SYNTHESIS_KEYWORDS),
        "risk": _has_section(sections, RISK_KEYWORDS),
        "action": _has_section(sections, ACTION_KEYWORDS),
    }


def _has_section(sections: list[str], keywords: tuple[str, ...]) -> bool:
    return any(any(keyword in section for keyword in keywords) for section in sections)


def _count_sections(sections: list[str], keywords: tuple[str, ...]) -> int:
    return sum(1 for section in sections if any(keyword in section for keyword in keywords))


def _case_section_count(sections: list[str]) -> int:
    """统计真正承担案例分析的章节，避免把风险/横向比较中的“场景”误算为案例章。"""
    return sum(1 for section in sections if _is_case_section(section))


def _is_case_section(section: str) -> bool:
    if "案例" in section:
        return True
    if "场景" not in section:
        return False
    if any(keyword in section for keyword in SYNTHESIS_KEYWORDS + RISK_KEYWORDS + ACTION_KEYWORDS):
        return False
    return True


def _broad_case_section_count(sections: list[str]) -> int:
    return sum(1 for section in sections if any(hint in section for hint in BROAD_CASE_HINTS))


def _first_index(
    sections: list[str],
    keywords: tuple[str, ...],
    start: int = 0,
    predicate=None,
) -> int | None:
    for index, section in enumerate(sections[start:], start):
        if predicate is not None and not predicate(section):
            continue
        if any(keyword in section for keyword in keywords):
            return index
    return None


def _narrative_order_score(sections: list[str]) -> int:
    background = _first_index(sections, BACKGROUND_KEYWORDS)
    evidence = _first_index(sections, EVIDENCE_KEYWORDS)
    case = _first_index(sections, CASE_KEYWORDS, predicate=_is_case_section)
    after_case = case + 1 if case is not None else 0
    synthesis = _first_index(sections, SYNTHESIS_KEYWORDS, start=after_case)
    risk = _first_index(sections, RISK_KEYWORDS, start=after_case)
    action = _first_index(sections, ACTION_KEYWORDS, start=after_case)

    score = 0
    if background is not None and background <= 1:
        score += 4
    if evidence is not None and case is not None and evidence < case:
        score += 4
    if case is not None and synthesis is not None and case < synthesis:
        score += 4
    if risk is not None and case is not None and risk > case:
        score += 4
    if action is not None and action >= max(0, len(sections) - 3):
        score += 4
    return score


def _searchability_score(sections: list[str]) -> int:
    if not sections:
        return 0

    score = 0
    for section in sections:
        section_score = 0
        if len(section) >= 8:
            section_score += 1
        if any(keyword in section for keyword in CASE_KEYWORDS + EVIDENCE_KEYWORDS + RISK_KEYWORDS + ACTION_KEYWORDS):
            section_score += 1
        if not any(hint in section for hint in ("其他", "相关", "若干", "综合", "概述")):
            section_score += 1
        score += min(section_score, 3)
    return round(score / len(sections) / 3 * 20)


def _total_score(metrics: OutlineQualityMetrics) -> int:
    score = 0
    score += _section_count_score(metrics.section_count)
    score += sum(5 for covered in metrics.role_coverage.values() if covered)
    score += metrics.narrative_order_score
    score += metrics.searchability_score
    score += min(12, metrics.case_sections * 4)
    score -= metrics.broad_case_sections * 6
    if _is_industry_listing_without_synthesis(metrics):
        score -= 12
    return max(0, min(100, score))


def _section_count_score(section_count: int) -> int:
    if TARGET_OUTLINE_SECTIONS[0] <= section_count <= TARGET_OUTLINE_SECTIONS[1]:
        return 18
    if MIN_OUTLINE_SECTIONS <= section_count < TARGET_OUTLINE_SECTIONS[0]:
        return 12
    if MAX_OUTLINE_SECTIONS < section_count <= 12:
        return 10
    return 0


def _is_industry_listing_without_synthesis(metrics: OutlineQualityMetrics) -> bool:
    return (
        metrics.industry_listing_sections >= max(4, metrics.section_count // 2)
        and not metrics.role_coverage["synthesis"]
    )


def _strengths(metrics: OutlineQualityMetrics) -> list[str]:
    strengths: list[str] = []
    if TARGET_OUTLINE_SECTIONS[0] <= metrics.section_count <= TARGET_OUTLINE_SECTIONS[1]:
        strengths.append("章节数量处于 8-10 的目标区间")
    if all(metrics.role_coverage.values()):
        strengths.append("背景、证据、案例、归纳、风险和行动章节齐全")
    if metrics.narrative_order_score >= 16:
        strengths.append("叙事顺序接近背景-证据-案例-归纳-风险-行动")
    if metrics.searchability_score >= 16:
        strengths.append("章节标题具备较好的独立检索性")
    if metrics.case_sections >= 3:
        strengths.append("案例章节数量足以支撑多场景分析")
    return strengths


def _issues(metrics: OutlineQualityMetrics) -> list[str]:
    issues: list[str] = []
    if metrics.section_count < MIN_OUTLINE_SECTIONS:
        issues.append(f"章节数量 {metrics.section_count} 少于 {MIN_OUTLINE_SECTIONS}。")
    if metrics.section_count > MAX_OUTLINE_SECTIONS:
        issues.append(f"章节数量 {metrics.section_count} 超过 {MAX_OUTLINE_SECTIONS}。")

    missing_roles = [
        role_name
        for role_key, role_name in (
            ("background", "背景/问题定义"),
            ("evidence", "证据或技术基础"),
            ("case", "案例或场景分析"),
            ("synthesis", "横向比较或模式归纳"),
            ("risk", "风险挑战或治理边界"),
            ("action", "实施路径或行动建议"),
        )
        if not metrics.role_coverage[role_key]
    ]
    if missing_roles:
        issues.append("缺少结构角色：" + "、".join(missing_roles) + "。")

    if metrics.broad_case_sections:
        issues.append(f"存在 {metrics.broad_case_sections} 个过宽案例章节，后续搜索容易发散。")
    if _is_industry_listing_without_synthesis(metrics):
        issues.append("行业枚举较多但缺少横向比较、模式归纳或评估框架。")
    if metrics.narrative_order_score < 14:
        issues.append("叙事顺序不够清晰，可能无法自然支撑后续写作。")
    if metrics.searchability_score < 14:
        issues.append("部分章节标题过泛，独立检索性不足。")
    return issues
