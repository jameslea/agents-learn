import re

from sop_artifacts import ResearchReport
from utils.url_utils import is_valid_url


def validate_research_report(report: ResearchReport) -> list[str]:
    """校验研究素材是否足够给 Writer 使用。"""
    issues: list[str] = []

    if not report.materials:
        return ["研究报告没有任何章节素材。"]

    for material in report.materials:
        section = material.section_name or "未命名章节"
        if not material.raw_data.strip():
            issues.append(f"{section}: raw_data 为空。")

        if not material.sources:
            issues.append(f"{section}: 缺少来源 URL。")
            continue

        invalid_urls = [url for url in material.sources if not is_valid_url(url)]
        if invalid_urls:
            issues.append(f"{section}: 存在无效来源 URL: {', '.join(invalid_urls)}")

        if len(material.source_quality) != len(material.sources):
            issues.append(f"{section}: source_quality 与 sources 数量不一致。")

        if len(material.source_notes) != len(material.sources):
            issues.append(f"{section}: source_notes 与 sources 数量不一致。")

        source_refs = [int(n) for n in re.findall(r"来源\s*(\d+)", material.raw_data)]
        if source_refs and max(source_refs) > len(material.sources):
            issues.append(
                f"{section}: raw_data 中的来源编号超过 sources 数量。"
            )

    return issues
