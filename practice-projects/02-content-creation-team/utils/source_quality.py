from urllib.parse import urlparse

from sop_artifacts import ResearchReport


HIGH_QUALITY_SOURCE_TIERS = {"tier_1", "tier_2"}
SOURCE_TIER_RANK = {"tier_1": 0, "tier_2": 1, "tier_3": 2}

# 通用弱来源提示。这里不是封杀，只是避免它们被误排到官方/研究报告前面。
WEAK_SOURCE_HINTS = (
    "csdn.net",
    "zhihu.com",
    "juejin.cn",
    "sohu.com",
    "ai-indeed.com",
    "ai-indeed.com/aboutnews",
    "betteryeah.com/blog",
    "meiqia.com/blog",
    "beisen.com/special",
    "fanruan.com/finepedia",
    "caifuhao.eastmoney.com",
    "developer.aliyun.com/article",
    "cloud.tencent.com/developer/article",
    "gd.sina.com.cn",
    "yonyou.com/news",
)

# 权威媒体或新闻转述通常适合作准一手/二手来源。
MEDIA_SOURCE_HINTS = (
    "news.qq.com",
    "thepaper.cn",
    "36kr.com",
    "ifeng.com",
)

# 官方报告、咨询机构、厂商资源页等通常优先级更高。
PRIMARY_SOURCE_HINTS = (
    "kpmg.com",
    "ey.com",
    "mckinsey.com",
    "gartner.com",
    "idc.com",
    "cbinsights.com",
    "huawei.com",
    "cloud.google.com/resources",
    "microsoft.com",
    "amazon.com",
    "ibm.com",
)


def infer_source_tier(url: str, declared_tier: str = "tier_3") -> str:
    """用 URL 形态对 LLM 给出的来源等级做确定性兜底。"""
    normalized_url = url.strip().lower()
    parsed = urlparse(normalized_url)
    host_and_path = f"{parsed.netloc}{parsed.path}"
    declared_rank = SOURCE_TIER_RANK.get(declared_tier, SOURCE_TIER_RANK["tier_3"])

    if any(hint in host_and_path for hint in WEAK_SOURCE_HINTS):
        return "tier_3"

    if any(hint in host_and_path for hint in MEDIA_SOURCE_HINTS):
        return "tier_2" if declared_rank <= SOURCE_TIER_RANK["tier_2"] else declared_tier

    if normalized_url.endswith(".pdf") or any(hint in host_and_path for hint in PRIMARY_SOURCE_HINTS):
        return "tier_1"

    return declared_tier if declared_tier in SOURCE_TIER_RANK else "tier_3"


def ranked_source_records(report: ResearchReport, max_sources: int = 15) -> list[dict[str, str]]:
    """对研究来源去重、按质量排序，并限制提供给 Writer 的来源数量。"""
    records_by_url: dict[str, dict[str, str | int]] = {}
    original_order = 0

    for material in report.materials:
        for index, url in enumerate(material.sources):
            normalized_url = url.strip()
            if not normalized_url:
                continue

            declared_tier = material.source_quality[index] if index < len(material.source_quality) else "tier_3"
            tier = infer_source_tier(normalized_url, declared_tier)
            note = material.source_notes[index] if index < len(material.source_notes) else "未提供来源可信度说明"
            rank = SOURCE_TIER_RANK.get(tier, 3)
            existing = records_by_url.get(normalized_url)
            if existing and int(existing["rank"]) <= rank:
                continue

            records_by_url[normalized_url] = {
                "url": normalized_url,
                "tier": tier,
                "note": note,
                "section": material.section_name,
                "local_source": f"来源{index + 1}",
                "rank": rank,
                "order": original_order if not existing else int(existing["order"]),
            }
            if not existing:
                original_order += 1

    ranked = sorted(
        records_by_url.values(),
        key=lambda record: (int(record["rank"]), int(record["order"])),
    )
    selected = _select_ranked_records_by_section(ranked, report, max_sources)
    return [
        {
            "url": str(record["url"]),
            "tier": str(record["tier"]),
            "note": str(record["note"]),
            "section": str(record["section"]),
            "local_source": str(record["local_source"]),
        }
        for record in selected
    ]


def _select_ranked_records_by_section(
    ranked: list[dict[str, str | int]],
    report: ResearchReport,
    max_sources: int,
) -> list[dict[str, str | int]]:
    """优先保证每个章节至少有一个较好来源，再用全局高质量来源补齐。"""
    selected_urls: set[str] = set()
    selected: list[dict[str, str | int]] = []

    for material in report.materials:
        if len(selected) >= max_sources:
            break
        section_candidates = [
            record
            for record in ranked
            if record["section"] == material.section_name and record["url"] not in selected_urls
        ]
        if not section_candidates:
            continue
        selected.append(section_candidates[0])
        selected_urls.add(str(section_candidates[0]["url"]))

    for record in ranked:
        if len(selected) >= max_sources:
            break
        if record["url"] in selected_urls:
            continue
        selected.append(record)
        selected_urls.add(str(record["url"]))

    return sorted(
        selected,
        key=lambda record: (int(record["rank"]), int(record["order"])),
    )


def source_quality_summary(report: ResearchReport) -> dict[str, int]:
    """统计研究报告中的有效来源等级分布。"""
    summary = {"tier_1": 0, "tier_2": 0, "tier_3": 0, "unknown": 0}
    for material in report.materials:
        for index, tier in enumerate(material.source_quality):
            url = material.sources[index] if index < len(material.sources) else ""
            tier = infer_source_tier(url, tier)
            if tier in summary:
                summary[tier] += 1
            else:
                summary["unknown"] += 1
    return summary


def source_quality_warnings(report: ResearchReport, min_high_quality: int = 3) -> list[str]:
    """给出非阻断的来源质量提醒。"""
    summary = source_quality_summary(report)
    high_quality_count = summary["tier_1"] + summary["tier_2"]
    if high_quality_count >= min_high_quality:
        return []

    return [
        (
            f"一手/准一手来源不足：tier_1+tier_2={high_quality_count}，"
            f"目标至少 {min_high_quality} 条；允许降级，但报告需谨慎使用 tier_3 结论。"
        )
    ]
