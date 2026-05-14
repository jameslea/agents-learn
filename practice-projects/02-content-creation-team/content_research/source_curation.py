"""Researcher 的搜索结果筛选策略。

Tavily 返回的结果质量参差不齐。这里先用确定性 URL 规则给结果打上来源等级，
再把强来源排到前面，减少后续 LLM 从博客、社区或聚合资讯中提炼核心结论的概率。
"""

from utils.source_quality import SOURCE_TIER_RANK, infer_source_tier


SEARCH_RESULT_LIMIT = 6


def prioritize_search_results(search_results, max_results: int = SEARCH_RESULT_LIMIT):
    """按来源质量对 Tavily 搜索结果排序并标注，降低弱来源被优先提炼的概率。"""
    # Tavily 或测试替身可能返回非标准结构；这里保持透传，避免搜索层误吞异常形态。
    if not isinstance(search_results, dict):
        return search_results

    results = search_results.get("results")
    if not isinstance(results, list):
        return search_results

    annotated_results = []
    for order, result in enumerate(results):
        # 非 dict 结果无法判断 URL，只能按弱来源保守排序，同时保留原始内容。
        if not isinstance(result, dict):
            annotated_results.append((SOURCE_TIER_RANK["tier_3"], order, result))
            continue

        # 来源等级只作为排序和 prompt 提示，不直接删除结果；弱来源仍可作为辅助线索。
        url = str(result.get("url") or result.get("link") or "")
        tier = infer_source_tier(url, "tier_3")
        result_copy = dict(result)
        result_copy["source_quality_hint"] = tier
        result_copy["source_use_guidance"] = _source_use_guidance(tier)
        annotated_results.append((SOURCE_TIER_RANK.get(tier, 3), order, result_copy))

    ranked_results = [
        result
        for _rank, _order, result in sorted(
            annotated_results,
            key=lambda item: (item[0], item[1]),
        )
    ]
    return {
        **search_results,
        "results": ranked_results[:max_results],
        "source_selection_note": (
            "搜索结果已按来源质量排序：tier_1/tier_2 优先；tier_3、博客、社区和聚合资讯仅作辅助线索。"
        ),
    }


def _source_use_guidance(tier: str) -> str:
    if tier in {"tier_1", "tier_2"}:
        return "可优先提炼；适合支撑事实、数据或案例结论。"
    return "弱来源；仅作辅助线索，不能单独支撑核心数字、ROI或可核验案例。"
