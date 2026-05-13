import re

from sop_artifacts import DraftContent
from utils.references import REFERENCE_HEADING, parse_reference_urls
from utils.url_utils import is_valid_url


NUMBERED_SECTION_RE = re.compile(
    r"^##\s+(?:第?[一二三四五六七八九十百\d]+[章节、.．]|[一二三四五六七八九十百\d]+、)"
)
SUBSECTION_RE = re.compile(r"^###\s+\S+")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+[.)、])\s+\S+")
NUMBERED_SECTION_HEADING_RE = re.compile(
    r"^##\s+(?:第?[一二三四五六七八九十百\d]+[章节、.．]|[一二三四五六七八九十百\d]+、).*$",
    re.MULTILINE,
)

CASE_STRUCTURE_KEYWORDS = ("成功案例", "失败案例", "失败教训", "挑战与教训", "公开案例", "厂商案例", "综合案例")
COMPARISON_KEYWORDS = ("横向对比", "纵向分析", "横向比较", "纵向对比", "模式归纳")
PRACTICE_KEYWORDS = ("实施路径", "最佳实践", "常见错误", "失败教训总结", "行动建议")


def has_report_title(markdown: str) -> bool:
    """判断报告是否以 Markdown 一级标题开头。"""
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return stripped.startswith("# ") and not stripped.startswith("## ")
    return False


def numbered_section_count(markdown: str) -> int:
    """统计正文中的编号一级章节数量，不包含参考资料。"""
    body = markdown.split(REFERENCE_HEADING, 1)[0]
    return sum(
        1
        for line in body.splitlines()
        if NUMBERED_SECTION_RE.match(line.strip())
    )


def subsection_count(markdown: str) -> int:
    """统计正文中的三级小节数量，不包含参考资料。"""
    body = markdown.split(REFERENCE_HEADING, 1)[0]
    return sum(
        1
        for line in body.splitlines()
        if SUBSECTION_RE.match(line.strip())
    )


def list_item_count(markdown: str) -> int:
    """统计正文中的 Markdown 列表项数量，不包含参考资料。"""
    body = markdown.split(REFERENCE_HEADING, 1)[0]
    return sum(
        1
        for line in body.splitlines()
        if LIST_ITEM_RE.match(line.strip())
    )


def structural_keyword_hits(markdown: str) -> dict[str, int]:
    """统计报告是否覆盖案例、对比和实践类结构信号。"""
    body = markdown.split(REFERENCE_HEADING, 1)[0]
    return {
        "case": sum(1 for keyword in CASE_STRUCTURE_KEYWORDS if keyword in body),
        "comparison": sum(1 for keyword in COMPARISON_KEYWORDS if keyword in body),
        "practice": sum(1 for keyword in PRACTICE_KEYWORDS if keyword in body),
    }


def count_report_units(markdown: str) -> int:
    """估算报告长度：中文按字计，英文/数字按词计。"""
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", markdown)
    ascii_words = re.findall(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*", markdown)
    return len(cjk_chars) + len(ascii_words)


def numbered_section_blocks(markdown: str) -> list[tuple[str, str]]:
    """按编号二级章节切分正文，不包含参考资料。"""
    body = markdown.split(REFERENCE_HEADING, 1)[0]
    matches = list(NUMBERED_SECTION_HEADING_RE.finditer(body))
    blocks: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        blocks.append((match.group(0).strip(), body[match.end():next_start]))

    return blocks


def subsection_blocks(markdown: str) -> list[tuple[str, str]]:
    """按三级小节切分正文，小节内容截止到下一个二级或三级标题。"""
    body = markdown.split(REFERENCE_HEADING, 1)[0]
    matches = list(re.finditer(r"^###\s+(.+)$", body, re.MULTILINE))
    blocks: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        search_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        next_major = re.search(r"^##\s+\S+.*$", body[match.end():search_end], re.MULTILINE)
        end = match.end() + next_major.start() if next_major else search_end
        blocks.append((match.group(1).strip(), body[match.end():end]))

    return blocks


def validate_draft(draft: DraftContent, min_units: int = 3000) -> list[str]:
    """校验草稿的确定性质量要求，供 Writer/Reviewer 门禁使用。"""
    issues: list[str] = []
    content = draft.content_markdown
    actual_units = count_report_units(content)

    if not has_report_title(content):
        issues.append("报告缺少一级标题，如 '# 报告标题'。")

    if draft.word_count < min_units:
        issues.append(f"正文声明字数 {draft.word_count} 低于 {min_units}。")

    if actual_units < min_units:
        issues.append(f"正文估算字数 {actual_units} 低于 {min_units}。")

    if REFERENCE_HEADING not in content:
        issues.append("缺少 '## 参考资料' 章节。")

    if numbered_section_count(content) < 3:
        issues.append("正文缺少编号章节，主要章节应使用 '## 一、章节标题' 这类格式。")

    issues.extend(_structure_richness_issues(content))

    body = content.split(REFERENCE_HEADING, 1)[0]
    cited_numbers = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    if not cited_numbers:
        issues.append("正文没有发现数字编号引用，如 [1]。")

    reference_urls = parse_reference_urls(content)
    if not reference_urls:
        issues.append("参考资料章节没有可解析的编号 URL。")

    issues.extend(_reference_closure_issues(cited_numbers, reference_urls))
    issues.extend(_url_consistency_issues(draft, reference_urls))
    return issues


def _structure_richness_issues(content: str) -> list[str]:
    """检查报告是否具备深度报告应有的章节内部结构。"""
    issues: list[str] = []
    units = count_report_units(content)

    if units < 2500:
        return issues

    min_subsections = 4
    actual_subsections = subsection_count(content)
    if actual_subsections < min_subsections:
        issues.append(
            f"正文三级小节数量 {actual_subsections} 少于 {min_subsections}，"
            "案例或实施章节应拆出成功案例、失败教训、横向/纵向分析等内部结构。"
        )

    min_list_items = 5
    actual_list_items = list_item_count(content)
    if actual_list_items < min_list_items:
        issues.append(
            f"正文列表项数量 {actual_list_items} 少于 {min_list_items}，"
            "关键价值、挑战、路径或建议应使用清单增强信息密度。"
        )

    keyword_hits = structural_keyword_hits(content)
    if keyword_hits["case"] < 2:
        issues.append("案例结构不足：至少应明确覆盖成功案例、失败案例/失败教训或案例标签。")
    if keyword_hits["comparison"] < 1:
        issues.append("缺少横向或纵向分析结构，报告应包含跨场景比较或演进分析。")
    if keyword_hits["practice"] < 1:
        issues.append("缺少实施路径、最佳实践或行动建议类结构。")

    issues.extend(_section_balance_issues(content))
    issues.extend(_subsection_depth_issues(content))
    return issues


def _section_balance_issues(content: str) -> list[str]:
    """检查结构化小节是否集中在前半篇，避免后半篇重新变成连续段落。"""
    sections = numbered_section_blocks(content)
    if len(sections) < 8:
        return []

    midpoint = len(sections) // 2
    later_sections = sections[midpoint:]
    structured_later_count = sum(
        1
        for _heading, block in later_sections
        if subsection_count(block) > 0
    )
    min_structured_later_sections = 2
    if structured_later_count >= min_structured_later_sections:
        return []

    return [
        (
            f"后半部分只有 {structured_later_count} 个主章节包含三级小节，"
            f"至少需要 {min_structured_later_sections} 个；风险、证据边界、实施建议或结论前章节也应有内部结构。"
        )
    ]


def _subsection_depth_issues(content: str) -> list[str]:
    """检查是否存在大量只有标题和短句的三级小节。"""
    blocks = subsection_blocks(content)
    if not blocks:
        return []

    min_subsection_units = 80
    thin_subsections = [
        f"{heading}({count_report_units(block)})"
        for heading, block in blocks
        if count_report_units(block) < min_subsection_units
    ]
    allowed_thin_count = max(2, len(blocks) // 4)
    if len(thin_subsections) <= allowed_thin_count:
        return []

    preview = "、".join(thin_subsections[:4])
    return [
        (
            f"三级小节内容过薄过多：{preview}；"
            f"共有 {len(thin_subsections)}/{len(blocks)} 个三级小节少于 {min_subsection_units} 个估算字/词，"
            f"允许最多 {allowed_thin_count} 个短小节。请减少机械拆分，合并薄弱小节或补充分析。"
        )
    ]


def _reference_closure_issues(
    cited_numbers: set[int],
    reference_urls: dict[int, str],
) -> list[str]:
    """检查正文引用编号和参考资料编号是否闭环。"""
    issues: list[str] = []
    missing_refs = sorted(cited_numbers - set(reference_urls))
    if missing_refs:
        issues.append(f"正文引用编号缺少参考资料条目: {missing_refs}")

    unused_refs = sorted(set(reference_urls) - cited_numbers)
    if unused_refs:
        issues.append(f"参考资料编号未在正文中使用: {unused_refs}")

    invalid_ref_urls = [
        f"[{number}] {url}"
        for number, url in reference_urls.items()
        if not is_valid_url(url)
    ]
    if invalid_ref_urls:
        issues.append(f"参考资料存在无效 URL: {', '.join(invalid_ref_urls)}")
    return issues


def _url_consistency_issues(
    draft: DraftContent,
    reference_urls: dict[int, str],
) -> list[str]:
    """检查 citations 字段与参考资料章节 URL 是否一致。"""
    issues: list[str] = []
    invalid_citations = [url for url in draft.citations if not is_valid_url(url)]
    if not draft.citations:
        issues.append("citations 字段为空。")

    if invalid_citations:
        issues.append(f"citations 字段存在无效 URL: {', '.join(invalid_citations)}")

    reference_url_set = set(reference_urls.values())
    missing_citations = [
        url for url in draft.citations if url and url not in reference_url_set
    ]
    if missing_citations:
        issues.append(
            "citations 字段中的 URL 未出现在参考资料章节: "
            + ", ".join(missing_citations)
        )

    citation_url_set = set(draft.citations)
    missing_from_citations = [
        url for url in reference_urls.values() if url not in citation_url_set
    ]
    if missing_from_citations:
        issues.append(
            "参考资料章节中的 URL 未出现在 citations 字段: "
            + ", ".join(missing_from_citations)
        )
    return issues
