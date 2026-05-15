import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.llm_factory import build_llm, resolve_provider_config

from content_research.material_processing import finalize_research_material
from content_research.prompts import (
    build_feedback_note,
    build_material_system_prompt,
    build_material_user_prompt,
)
from content_research.search_planner import build_section_search_query
from content_research.source_curation import prioritize_search_results
from sop_artifacts import ResearchMaterial, ResearchReport, ContentOutline, ReviewFeedback
from utils.cost_utils import tracked_call
from utils.json_utils import parse_llm_json
from utils.logging_utils import get_logger, timed_block
from utils.quality import source_quality_summary, source_quality_warnings, validate_research_report

load_dotenv()
logger = get_logger(__name__)


def _shorten(text: str, limit: int = 160) -> str:
    """压缩日志文本，避免搜索词或反馈内容把日志刷得过长。"""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


class Researcher:
    def __init__(self, llm=None, search_tool=None):
        self.llm = llm or self._build_llm()
        self.search_tool = search_tool or self._build_search_tool()

    def _build_llm(self):
        """初始化 Researcher 使用的 JSON LLM。"""
        provider_config = resolve_provider_config()
        logger.info(
            "加载 Researcher LLM: provider=%s model=%s base_url=%s",
            provider_config.name,
            provider_config.model,
            provider_config.base_url,
        )
        return build_llm(json_mode=True)

    def _build_search_tool(self):
        """初始化 Researcher 使用的联网搜索工具。"""
        with timed_block(logger, "加载 langchain_tavily.TavilySearch", slow_after=2.0):
            from langchain_tavily import TavilySearch
        logger.info("初始化 TavilySearch: max_results=8 topic=general")
        return TavilySearch(max_results=8, topic="general")

    def conduct_research(
        self,
        outline: ContentOutline,
        feedback: Optional[ReviewFeedback] = None,
    ) -> ResearchReport:
        """根据大纲逐个章节进行研究；返工时也完整重跑，保持控制流简单。"""
        feedback_note = build_feedback_note(feedback)
        materials = [
            self._research_section(
                outline,
                section,
                feedback_note,
            )
            for section in outline.sections
        ]
        return ResearchReport(materials=materials)

    def _research_section(
        self,
        outline: ContentOutline,
        section: str,
        feedback_note: str,
    ) -> ResearchMaterial:
        """完成单个章节的搜索、素材提炼和来源编号兜底修正。"""
        print(f"正在研究章节: {section}...")
        logger.info("开始调研章节: section=%s", section)
        search_results = self._search_section(outline, section, feedback_note)
        material = self._extract_material(
            outline,
            section,
            search_results,
            feedback_note,
        )
        material = finalize_research_material(material)
        logger.info(
            "章节调研完成: section=%s sources=%d case_candidates=%d raw_chars=%d",
            material.section_name,
            len(material.sources),
            len(material.case_candidates),
            len(material.raw_data),
        )
        return material

    def _search_section(
        self,
        outline: ContentOutline,
        section: str,
        feedback_note: str,
    ):
        """执行章节搜索；有评审反馈时把反馈压缩进搜索词。"""
        # 搜索策略放在 content_research.search_planner 中，角色节点只负责调用并记录可观测信息。
        search_query, section_type, cleaned_section = build_section_search_query(
            outline,
            section,
            feedback_note,
        )
        logger.info(
            "搜索词规划: section=%s type=%s cleaned=%s",
            section,
            section_type,
            cleaned_section,
        )
        if feedback_note:
            print(f"  ↳ 针对评审问题补充搜索: {_shorten(feedback_note)}")
            logger.info(
                "章节调研带反馈: section=%s",
                section,
            )
        logger.info(
            "执行 Tavily 搜索: section=%s query=%s",
            section,
            _shorten(search_query, 220),
        )
        # tracked_call 记录搜索输入输出，用于后续分析成本、耗时和搜索质量。
        search_payload = {
            "query": search_query,
            "max_results": 8,
            "tavily_topic": "general",
        }
        with timed_block(logger, f"Tavily 搜索: {section}", slow_after=8.0):
            with tracked_call(logger, f"Tavily 搜索: {section}", search_payload) as record:
                search_results = self.search_tool.invoke({"query": search_query})
                record["output_payload"] = search_results
        # 搜索后先做确定性来源排序，再交给 LLM 提炼，降低弱来源污染素材的概率。
        return prioritize_search_results(search_results)

    def _extract_material(
        self,
        outline: ContentOutline,
        section: str,
        search_results,
        feedback_note: str,
    ) -> ResearchMaterial:
        """调用 LLM 提炼研究素材。"""
        system_prompt = build_material_system_prompt()
        user_prompt = build_material_user_prompt(
            outline,
            section,
            search_results,
            feedback_note,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        with timed_block(
            logger,
            f"Researcher LLM 提炼素材: {section}",
            slow_after=15.0,
        ):
            with tracked_call(logger, f"Researcher LLM 提炼素材: {section}", [system_prompt, user_prompt]) as record:
                response = self.llm.invoke(messages)
                record["output_payload"] = response.content
        with timed_block(logger, f"解析研究素材 JSON: {section}", slow_after=1.0):
            return parse_llm_json(response.content, ResearchMaterial)


def researcher_node(state):
    """LangGraph 节点函数"""
    print("--- 执行：研究员 (Researching) ---")
    logger.info("进入 Researcher 节点")
    with timed_block(logger, "Researcher 节点总耗时", slow_after=30.0):
        researcher = Researcher()
        feedback = state.get("latest_feedback")
        report = researcher.conduct_research(
            state["outline"],
            feedback=feedback,
        )
    
    # B4: 中间质量门禁 (Quality Gate)
    with timed_block(logger, "研究素材质量门禁", slow_after=1.0):
        issues = validate_research_report(report)
    if issues:
        logger.warning("研究素材质量门禁未通过: issues=%d", len(issues))
        issue_text = "\n".join(f"- {issue}" for issue in issues)
        raise ValueError(f"研究素材质量门禁未通过：\n{issue_text}")
    quality_summary = source_quality_summary(report)
    quality_warnings = source_quality_warnings(report)
    logger.info(
        "研究素材质量门禁通过: materials=%d source_quality=%s",
        len(report.materials),
        quality_summary,
    )
    if quality_warnings:
        logger.warning("研究素材来源质量提醒: %s", quality_warnings)
    
    history_msg = "研究员完成了全章节资料搜集"
    if quality_warnings:
        history_msg += "（来源质量提醒：" + "；".join(quality_warnings) + "）"
        
    return {"research_report": report, "history": [history_msg]}
