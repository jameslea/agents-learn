"""Outline candidate ranking and editorial judging helpers."""
import json
import os
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.llm_factory import build_llm, resolve_provider_config
from pydantic import BaseModel, Field

from utils.cost_utils import tracked_call
from utils.json_utils import parse_llm_json
from utils.logging_utils import get_logger, timed_block
from utils.outline_evaluation import OutlineQualityMetrics


logger = get_logger(__name__)


class OutlineJudgeRankingItem(BaseModel):
    candidate: str = Field(..., description="候选大纲名称，例如 sample_1")
    rank: int = Field(..., description="LLM 主编评审排名，1 为最佳")
    editorial_score: int = Field(..., description="主编判断分数，0-100")
    strengths: list[str] = Field(default_factory=list, description="主编视角下的优势")
    risks: list[str] = Field(default_factory=list, description="主编视角下的风险")
    recommendation: str = Field("", description="推荐或不推荐该候选的理由")


class OutlineJudgeResult(BaseModel):
    ranking: list[OutlineJudgeRankingItem] = Field(default_factory=list)
    best_candidate: str = Field("", description="最终推荐候选名称")
    selection_reason: str = Field("", description="最终选择理由")


class OutlineJudge:
    def __init__(self):
        provider_config = resolve_provider_config()
        logger.info(
            "加载 OutlineJudge LLM: provider=%s model=%s base_url=%s",
            provider_config.name,
            provider_config.model,
            provider_config.base_url,
        )
        self.llm = build_llm(json_mode=True)

    def judge(self, topic: str, metrics: list[OutlineQualityMetrics]) -> OutlineJudgeResult:
        """让 LLM 以主编视角评估候选大纲，不改写大纲。"""
        system_prompt = (
            "你是一名资深商业报告主编。你的任务是评估多个候选大纲，"
            "判断哪个最适合进入后续调研和写作流程。你不能改写大纲，只能排序、评分并说明理由。"
            "请以 JSON 格式返回。"
        )
        user_prompt = build_outline_judge_prompt(topic, metrics)
        with timed_block(logger, "OutlineJudge LLM 评估候选大纲", slow_after=12.0):
            with tracked_call(logger, "OutlineJudge LLM 评估候选大纲", [system_prompt, user_prompt]) as record:
                response = self.llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ])
                record["output_payload"] = response.content
        return parse_llm_json(response.content, OutlineJudgeResult)


def select_top_outline_metrics(
    metrics: list[OutlineQualityMetrics],
    limit: int = 3,
) -> list[OutlineQualityMetrics]:
    """按确定性大纲质量排序，返回前 N 个候选。"""
    if limit <= 0:
        return []

    return sorted(
        metrics,
        key=outline_rank_key,
        reverse=True,
    )[:limit]


def outline_rank_key(metric: OutlineQualityMetrics) -> tuple[Any, ...]:
    return (
        metric.total_score,
        -metric.generic_case_sections,
        metric.case_specificity_ratio,
        metric.decision_value_sections,
        metric.specific_case_sections,
        metric.narrative_order_score,
        metric.searchability_score,
        metric.case_sections,
        -metric.broad_case_sections,
        -metric.industry_listing_sections,
    )


def judge_outline_candidates(
    topic: str,
    metrics: list[OutlineQualityMetrics],
    judge_factory: type[OutlineJudge] = OutlineJudge,
) -> OutlineJudgeResult:
    """对已筛选候选进行 LLM 主编评审。"""
    return judge_factory().judge(topic, metrics)


def build_outline_judge_prompt(topic: str, metrics: list[OutlineQualityMetrics]) -> str:
    """构造 LLM 主编评审提示词，要求只排序不改写。"""
    candidates = []
    for metric in metrics:
        candidates.append(
            {
                "candidate": metric.name,
                "title": metric.title,
                "target_audience": metric.target_audience,
                "local_score": metric.total_score,
                "section_count": metric.section_count,
                "case_sections": metric.case_sections,
                "specific_case_sections": metric.specific_case_sections,
                "generic_case_sections": metric.generic_case_sections,
                "case_specificity_ratio": metric.case_specificity_ratio,
                "decision_value_sections": metric.decision_value_sections,
                "narrative_order_score": metric.narrative_order_score,
                "searchability_score": metric.searchability_score,
                "strengths": metric.strengths,
                "issues": metric.issues,
                "sections": metric.sections,
            }
        )
    return (
        f"报告主题：{topic}\n\n"
        "下面是经过本地确定性评估筛选后的候选大纲。"
        "本地分数只反映结构、角色覆盖、叙事顺序和可检索性；"
        "你需要补充主编判断，评估哪个大纲最可能产出高质量深度报告。\n\n"
        "评估重点：\n"
        "1. 是否具备清晰叙事线：背景 -> 证据基础 -> 多场景案例 -> 横向归纳 -> 风险边界 -> 实施建议。\n"
        "2. 案例章节是否具体、可调研、可核验，避免泛泛的“应用案例”。\n"
        "3. 是否能支撑一篇 3000 字以上的深度报告，而不是章节填空。\n"
        "4. 是否对企业高管或数字化负责人有决策价值。\n"
        "5. 是否保留风险、失败教训和证据边界，而不是只写成功叙事。\n"
        "6. 是否存在标题漂亮但搜索困难、证据难找、结构机械的问题。\n\n"
        "约束：\n"
        "- 不要改写大纲，不要新增候选。\n"
        "- ranking 必须只包含输入中的 candidate 名称。\n"
        "- editorial_score 使用 0-100 的整数。\n"
        "- rank 从 1 开始，1 是最推荐。\n\n"
        "候选大纲 JSON：\n"
        f"{json.dumps(candidates, ensure_ascii=False, indent=2)}\n\n"
        "请严格按以下 JSON 格式返回：\n"
        "{\n"
        '  "ranking": [\n'
        "    {\n"
        '      "candidate": "sample_1",\n'
        '      "rank": 1,\n'
        '      "editorial_score": 92,\n'
        '      "strengths": ["优势1", "优势2"],\n'
        '      "risks": ["风险1"],\n'
        '      "recommendation": "推荐或不推荐理由"\n'
        "    }\n"
        "  ],\n"
        '  "best_candidate": "sample_1",\n'
        '  "selection_reason": "最终选择理由"\n'
        "}"
    )
