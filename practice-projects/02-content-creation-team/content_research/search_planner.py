"""Researcher 的搜索规划策略。

这个模块只负责把“报告大纲章节”翻译成“适合 Tavily 的搜索词”：
先识别章节角色，再清洗章节标题，最后拼接与章节角色匹配的搜索补词。
"""

import re

from sop_artifacts import ContentOutline


CASE_SECTION_KEYWORDS = ("案例", "场景", "实践", "应用", "落地")

# 不同章节需要召回的资料类型不同：
# 案例章更需要公司官方案例、新闻稿和年报；技术/比较章更适合报告和 PDF。
SECTION_TYPE_TERMS = {
    "case": (
        "真实企业 客户案例 官方案例 case study customer story implementation "
        "press release annual report company deployment"
    ),
    "technology": (
        "technical report architecture benchmark capability limitation "
        "技术报告 架构 能力评估 白皮书"
    ),
    "risk": (
        "risk governance compliance audit failure incident lessons learned "
        "监管 合规 审计 失败教训"
    ),
    "implementation": (
        "implementation guide deployment framework maturity model ROI best practices "
        "实施指南 成熟度 投资回报 最佳实践"
    ),
    "comparison": (
        "industry comparison benchmark adoption survey report market data "
        "行业对比 调研报告 市场数据"
    ),
    "evidence": (
        "evidence verification attribution methodology source credibility "
        "证据 可验证性 归因 可信度"
    ),
    "general": "深度资料 行业数据 官方报告 研究报告 白皮书 权威来源",
}


def clean_section_for_search(section: str) -> str:
    """把大纲章节标题清洗成更适合搜索的业务关键词。"""
    # 去掉编号和章节角色前缀，避免 Tavily 搜索被“案例一/技术基础”这类结构词带偏。
    cleaned = re.sub(r"^\s*(?:\d+|[一二三四五六七八九十]+)[\.．、]\s*", "", section.strip())
    cleaned = re.sub(r"^\s*(?:案例|场景)[一二三四五六七八九十\d]*[：:、\-\s]*", "", cleaned)
    cleaned = re.sub(
        r"^\s*(?:问题定义|背景|引言|技术基础|能力边界|横向比较|横向对比|路径归纳|风险挑战|风险与挑战|证据边界|实施路径|实施建议|结论|未来展望)[：:]\s*",
        "",
        cleaned,
    )
    cleaned = re.sub(r"[（）()\[\]【】——\-_/|,，；;：:、]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or section.strip()


def classify_research_section(section: str) -> str:
    """按章节角色选择搜索补词，避免所有章节都强行搜索案例。"""
    # 顺序很重要：证据边界、横向比较、实施路径等章节可能也包含“案例/场景”字样，
    # 需要先按更具体的章节角色归类，最后才落到泛案例判断。
    if any(keyword in section for keyword in ("证据", "可验证", "可信", "归因")):
        return "evidence"
    if any(keyword in section for keyword in ("横向", "比较", "对比", "异同", "模式归纳")):
        return "comparison"
    if re.search(r"^\s*(?:\d+|[一二三四五六七八九十]+)?[\.．、]?\s*(?:案例|场景)[一二三四五六七八九十\d]*[：:、\-\s]", section):
        return "case"
    if re.search(r"^\s*(?:\d+|[一二三四五六七八九十]+)?[\.．、]?\s*(?:实施|路径|建议|部署|ROI|投资回报|价值量化)", section):
        return "implementation"
    if any(keyword in section for keyword in ("风险", "挑战", "治理", "合规", "安全", "失败")):
        return "risk"
    if any(keyword in section for keyword in ("技术", "架构", "能力", "模型", "工具调用", "多模态", "规划推理")):
        return "technology"
    if any(keyword in section for keyword in ("实施", "路径", "建议", "部署", "ROI", "投资回报", "成熟度", "试点")):
        return "implementation"
    if any(keyword in section for keyword in CASE_SECTION_KEYWORDS):
        return "case"
    return "general"


def build_section_search_query(
    outline: ContentOutline,
    section: str,
    feedback_note: str = "",
) -> tuple[str, str, str]:
    """生成章节搜索词，返回 query、章节类型和清洗后的章节关键词。"""
    section_type = classify_research_section(section)
    cleaned_section = clean_section_for_search(section)
    search_query = f"{outline.title} {cleaned_section} {SECTION_TYPE_TERMS[section_type]}"

    # PDF 限制只放在报告类资料更可能有效的章节；案例章不加，避免漏掉公司网页案例。
    if section_type in {"technology", "comparison", "general"}:
        search_query += " filetype:pdf"

    # Reviewer 指向 researcher 时不做局部补查，而是把反馈压缩成全局搜索提示。
    if feedback_note:
        search_query += (
            f" {_shorten(feedback_note, 180)} 权威来源 可核验 企业名称 独立验证 "
            "press release annual report"
        )

    return re.sub(r"\s+", " ", search_query).strip(), section_type, cleaned_section


def _shorten(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
