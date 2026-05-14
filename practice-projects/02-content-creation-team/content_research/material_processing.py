import re

from sop_artifacts import CaseCandidate, ResearchMaterial
from utils.logging_utils import get_logger
from utils.quality import infer_source_tier


logger = get_logger(__name__)
NON_WRITABLE_CASE_NAMES = {"", "未命名", "匿名", "综合案例", "某企业", "某公司"}


def finalize_research_material(material: ResearchMaterial) -> ResearchMaterial:
    """执行 Researcher 输出进入 Writer 前的确定性收尾处理。"""
    material = normalize_source_numbers(material)
    return normalize_case_candidates(material)


def normalize_source_numbers(material: ResearchMaterial) -> ResearchMaterial:
    """兜底修正越界来源编号，避免研究节点因小格式错误直接中断。"""
    if not material.sources:
        return material

    max_source = len(material.sources)

    def replace(match: re.Match[str]) -> str:
        number = int(match.group(1))
        return f"来源{min(number, max_source)}"

    normalized_raw_data = re.sub(r"来源\s*(\d+)", replace, material.raw_data)
    if normalized_raw_data == material.raw_data:
        return material

    logger.warning(
        "规范化研究素材来源编号: section=%s max_source=%d",
        material.section_name,
        max_source,
    )
    return material.model_copy(update={"raw_data": normalized_raw_data})


def normalize_case_candidates(material: ResearchMaterial) -> ResearchMaterial:
    """规范化案例候选来源等级，避免 LLM 误报强来源。"""
    normalized: list[CaseCandidate] = []
    for candidate in material.case_candidates:
        inferred_tier = infer_source_tier(candidate.source_url, candidate.source_tier)
        is_named = candidate.name.strip() not in NON_WRITABLE_CASE_NAMES
        is_independently_useful = (
            candidate.verification_status in {"verified", "aggregate"}
            and inferred_tier in {"tier_1", "tier_2"}
        )
        normalized.append(
            candidate.model_copy(
                update={
                    "source_tier": inferred_tier,
                    "is_writable_case": bool(
                        candidate.is_writable_case
                        and is_named
                        and is_independently_useful
                    ),
                }
            )
        )
    return material.model_copy(update={"case_candidates": normalized})
