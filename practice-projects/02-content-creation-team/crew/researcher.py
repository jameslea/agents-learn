import os
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sop_artifacts import CaseCandidate, ResearchMaterial, ResearchReport, ContentOutline, ReviewFeedback
from utils.json_utils import parse_llm_json
from utils.logging_utils import get_logger, timed_block
from utils.quality import infer_source_tier, source_quality_summary, source_quality_warnings, validate_research_report
from utils.rubric import RESEARCH_RUBRIC
from typing import Optional

load_dotenv()
logger = get_logger(__name__)

MAX_RESEARCH_RETRY_SECTIONS = 2
MAX_GLOBAL_FEEDBACK_ITEMS = 2
MAX_MATERIAL_EXTRACTION_ATTEMPTS = 2
SEARCH_RESULT_LIMIT = 6
SOURCE_TIER_RANK = {"tier_1": 0, "tier_2": 1, "tier_3": 2}
CASE_SECTION_KEYWORDS = ("案例", "场景", "实践", "应用", "落地")
CASE_EVIDENCE_FEEDBACK_KEYWORDS = ("案例", "综合案例", "无法核验", "企业名称", "真实企业", "厂商", "独立验证")


def _shorten(text: str, limit: int = 160) -> str:
    """压缩日志文本，避免搜索词或反馈内容把日志刷得过长。"""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def build_research_feedback_context(
    feedback: Optional[ReviewFeedback],
    sections: list[str],
) -> tuple[dict[str, list[str]], list[str]]:
    """把评审反馈拆成章节级问题和全局调研建议。"""
    section_issues: dict[str, list[str]] = {}
    global_issues: list[str] = []

    if not feedback or feedback.is_approved:
        return section_issues, global_issues

    for suggestion in feedback.suggestions:
        if suggestion:
            global_issues.append(suggestion)

    section_names = set(sections)
    for issue in feedback.specific_issues:
        if ": " not in issue:
            global_issues.append(issue)
            continue

        section_name, problem = issue.split(": ", 1)
        section_name = section_name.strip()
        problem = problem.strip()
        if section_name in section_names:
            section_issues.setdefault(section_name, []).append(problem)
        else:
            global_issues.append(issue)

    return section_issues, global_issues


def select_sections_for_research(
    sections: list[str],
    feedback: Optional[ReviewFeedback],
    existing_report: Optional[ResearchReport] = None,
    max_sections: int = MAX_RESEARCH_RETRY_SECTIONS,
) -> list[str]:
    """选择本轮需要调研的章节，返工时限制范围，避免 Researcher 工作量失控。"""
    if not existing_report or not feedback or feedback.is_approved:
        return sections

    if feedback.target_agent != "researcher":
        return []

    section_issues, global_issues = build_research_feedback_context(feedback, sections)
    if section_issues:
        return [section for section in sections if section in section_issues][:max_sections]

    if global_issues:
        if any(keyword in " ".join(global_issues) for keyword in CASE_EVIDENCE_FEEDBACK_KEYWORDS):
            case_sections = [
                section
                for section in sections
                if any(keyword in section for keyword in CASE_SECTION_KEYWORDS)
            ]
            if case_sections:
                return case_sections[:max_sections]
        return sections[:max_sections]

    return []


def merge_research_materials(
    sections: list[str],
    existing_report: Optional[ResearchReport],
    refreshed_materials: list[ResearchMaterial],
) -> list[ResearchMaterial]:
    """把补查结果合并回旧研究报告，并保持大纲原始章节顺序。"""
    by_section: dict[str, ResearchMaterial] = {}
    if existing_report:
        by_section.update(
            {material.section_name: material for material in existing_report.materials}
        )
    by_section.update(
        {material.section_name: material for material in refreshed_materials}
    )
    return [by_section[section] for section in sections if section in by_section]


def source_number_issues(material: ResearchMaterial) -> list[str]:
    """检查 raw_data 中是否引用了不存在的来源编号。"""
    source_refs = [int(n) for n in re.findall(r"来源\s*(\d+)", material.raw_data)]
    if source_refs and max(source_refs) > len(material.sources):
        return [
            f"{material.section_name}: raw_data 中的来源编号超过 sources 数量。"
        ]
    return []


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


def material_quality_issues(material: ResearchMaterial) -> list[str]:
    """复用研究报告门禁校验单个章节素材，供章节内重试使用。"""
    return validate_research_report(ResearchReport(materials=[material]))


def normalize_case_candidates(material: ResearchMaterial) -> ResearchMaterial:
    """规范化案例候选来源等级，避免 LLM 误报强来源。"""
    normalized: list[CaseCandidate] = []
    for candidate in material.case_candidates:
        inferred_tier = infer_source_tier(candidate.source_url, candidate.source_tier)
        is_named = candidate.name.strip() not in {"", "未命名", "匿名", "综合案例", "某企业", "某公司"}
        is_independently_useful = candidate.verification_status in {"verified", "aggregate"} and inferred_tier in {"tier_1", "tier_2"}
        normalized.append(
            candidate.model_copy(
                update={
                    "source_tier": inferred_tier,
                    "is_writable_case": bool(candidate.is_writable_case and is_named and is_independently_useful),
                }
            )
        )
    return material.model_copy(update={"case_candidates": normalized})


def prioritize_search_results(search_results, max_results: int = SEARCH_RESULT_LIMIT):
    """按来源质量对 Tavily 搜索结果排序并标注，降低弱来源被优先提炼的概率。"""
    if not isinstance(search_results, dict):
        return search_results

    results = search_results.get("results")
    if not isinstance(results, list):
        return search_results

    annotated_results = []
    for order, result in enumerate(results):
        if not isinstance(result, dict):
            annotated_results.append((SOURCE_TIER_RANK["tier_3"], order, result))
            continue

        url = str(result.get("url") or result.get("link") or "")
        tier = infer_source_tier(url, "tier_3")
        result_copy = dict(result)
        result_copy["source_quality_hint"] = tier
        result_copy["source_use_guidance"] = _source_use_guidance(tier)
        annotated_results.append((SOURCE_TIER_RANK.get(tier, 3), order, result_copy))

    ranked_results = [result for _rank, _order, result in sorted(annotated_results, key=lambda item: (item[0], item[1]))]
    selected_results = ranked_results[:max_results]
    return {
        **search_results,
        "results": selected_results,
        "source_selection_note": (
            "搜索结果已按来源质量排序：tier_1/tier_2 优先；tier_3、博客、社区和聚合资讯仅作辅助线索。"
        ),
    }


def _source_use_guidance(tier: str) -> str:
    if tier in {"tier_1", "tier_2"}:
        return "可优先提炼；适合支撑事实、数据或案例结论。"
    return "弱来源；仅作辅助线索，不能单独支撑核心数字、ROI或可核验案例。"


class Researcher:
    def __init__(self):
        model = os.getenv("MODEL_NAME", "deepseek-chat")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        logger.info("加载 Researcher LLM: model=%s base_url=%s", model, base_url)
        self.llm = ChatOpenAI(
            model=model,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        with timed_block(logger, "加载 langchain_tavily.TavilySearch", slow_after=2.0):
            from langchain_tavily import TavilySearch

        logger.info("初始化 TavilySearch: max_results=8 topic=general")
        self.search_tool = TavilySearch(max_results=8, topic="general")

    def conduct_research(
        self,
        outline: ContentOutline,
        feedback: Optional[ReviewFeedback] = None,
        existing_report: Optional[ResearchReport] = None,
    ) -> ResearchReport:
        """根据大纲逐个章节进行研究，若有评审反馈则针对性补充"""
        section_issues, global_issues = self._prepare_feedback_context(
            feedback,
            outline.sections,
        )
        sections_to_research = self._select_sections_to_research(
            outline.sections,
            feedback,
            existing_report,
        )

        if self._should_reuse_existing_report(existing_report, sections_to_research):
            return existing_report

        refreshed_materials = [
            self._research_section(
                outline,
                section,
                section_issues.get(section, []) + global_issues,
            )
            for section in sections_to_research
        ]
        materials = merge_research_materials(
            outline.sections,
            existing_report,
            refreshed_materials,
        )
        return ResearchReport(materials=materials)

    def _prepare_feedback_context(
        self,
        feedback: Optional[ReviewFeedback],
        sections: list[str],
    ) -> tuple[dict[str, list[str]], list[str]]:
        """提取本轮调研需要关注的反馈，并限制全局反馈数量。"""
        section_issues, global_issues = build_research_feedback_context(
            feedback,
            sections,
        )
        global_issues = global_issues[:MAX_GLOBAL_FEEDBACK_ITEMS]
        if global_issues:
            print(f"  ↳ 接收全局调研改进反馈 {len(global_issues)} 条")
            logger.info("接收全局调研改进反馈: count=%d", len(global_issues))
        return section_issues, global_issues

    def _select_sections_to_research(
        self,
        sections: list[str],
        feedback: Optional[ReviewFeedback],
        existing_report: Optional[ResearchReport],
    ) -> list[str]:
        """选择调研章节，并输出便于排查的路由日志。"""
        selected = select_sections_for_research(
            sections,
            feedback,
            existing_report,
        )
        logger.info(
            "调研章节选择: total_sections=%d selected=%d has_existing=%s target_agent=%s",
            len(sections),
            len(selected),
            bool(existing_report),
            getattr(feedback, "target_agent", None),
        )
        if existing_report and selected:
            print(
                f"  ↳ 本轮选择性补查 {len(selected)} 个章节，"
                "其余章节复用上一轮资料"
            )
        return selected

    def _should_reuse_existing_report(
        self,
        existing_report: Optional[ResearchReport],
        sections_to_research: list[str],
    ) -> bool:
        """判断是否可以直接复用上一轮研究资料。"""
        if existing_report and not sections_to_research:
            print("  ↳ 反馈未指向调研问题，复用上一轮研究资料")
            return True
        return False

    def _research_section(
        self,
        outline: ContentOutline,
        section: str,
        scoped_feedback: list[str],
    ) -> ResearchMaterial:
        """完成单个章节的搜索、素材提炼和来源编号兜底修正。"""
        print(f"正在研究章节: {section}...")
        logger.info("开始调研章节: section=%s", section)
        search_results = self._search_section(outline, section, scoped_feedback)
        material = self._extract_material_with_retry(
            outline,
            section,
            search_results,
            scoped_feedback,
        )
        material = normalize_source_numbers(material)
        material = normalize_case_candidates(material)
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
        scoped_feedback: list[str],
    ):
        """执行章节搜索；有评审反馈时把反馈压缩进搜索词。"""
        search_query = self._build_search_query(outline, section, scoped_feedback)
        logger.info(
            "执行 Tavily 搜索: section=%s query=%s",
            section,
            _shorten(search_query, 220),
        )
        with timed_block(logger, f"Tavily 搜索: {section}", slow_after=8.0):
            search_results = self.search_tool.invoke({"query": search_query})
        return prioritize_search_results(search_results)

    def _build_search_query(
        self,
        outline: ContentOutline,
        section: str,
        scoped_feedback: list[str],
    ) -> str:
        """构造 Tavily 搜索词，兼顾主题、章节和定向返工反馈。"""
        search_query = (
            f"{outline.title} {section} 深度资料 行业数据 实际案例 "
            "真实企业 客户案例 官方案例 case study 官方报告 白皮书 研究报告 filetype:pdf"
        )
        if scoped_feedback:
            search_hint = " ".join(_shorten(item, 80) for item in scoped_feedback[:3])
            search_query += f" {search_hint} 权威来源 可核验案例 失败教训 企业名称 独立验证 press release annual report"
            print(f"  ↳ 针对评审问题补充搜索: {_shorten(search_hint)}")
            logger.info(
                "章节调研带反馈: section=%s feedback_items=%d",
                section,
                len(scoped_feedback),
            )
        return search_query

    def _extract_material_with_retry(
        self,
        outline: ContentOutline,
        section: str,
        search_results,
        scoped_feedback: list[str],
    ) -> ResearchMaterial:
        """调用 LLM 提炼研究素材；章节素材未过门禁时做有限重试。"""
        retry_note = ""
        material: Optional[ResearchMaterial] = None
        feedback_note = self._build_feedback_note(scoped_feedback)

        for attempt in range(1, MAX_MATERIAL_EXTRACTION_ATTEMPTS + 1):
            material = self._extract_material_once(
                outline,
                section,
                search_results,
                feedback_note,
                retry_note,
                attempt,
            )
            issues = material_quality_issues(material)
            if not issues:
                return material

            retry_note = self._build_retry_note(section, attempt, issues)

        if material is None:
            raise RuntimeError(f"章节 {section} 的研究素材提炼未返回结果。")
        return material

    def _extract_material_once(
        self,
        outline: ContentOutline,
        section: str,
        search_results,
        feedback_note: str,
        retry_note: str,
        attempt: int,
    ) -> ResearchMaterial:
        """执行一次素材提炼调用，并解析为 ResearchMaterial。"""
        with timed_block(
            logger,
            f"Researcher LLM 提炼素材: {section} attempt={attempt}",
            slow_after=15.0,
        ):
            response = self.llm.invoke([
                SystemMessage(content=self._material_system_prompt()),
                HumanMessage(
                    content=self._material_user_prompt(
                        outline,
                        section,
                        search_results,
                        feedback_note,
                        retry_note,
                    )
                )
            ])
        with timed_block(logger, f"解析研究素材 JSON: {section}", slow_after=1.0):
            return parse_llm_json(response.content, ResearchMaterial)

    def _material_system_prompt(self) -> str:
        """构造研究素材提炼的系统提示词。"""
        return (
            "你是一名专业的互联网研究员。你的任务是针对特定报告章节，"
            "从搜索结果中提炼高质量、有事实支撑、可被后续写作直接使用的素材。"
            "关键数据、关键事实和案例结论需要在括号内标注来源序号，如（来源1）（来源2）。"
            "sources、source_quality、source_notes 需与 raw_data 中使用的来源序号对应。"
            "同时必须识别 case_candidates：能写成具体案例的候选、只能作为厂商案例或趋势观察的候选都要列出。"
            f"{RESEARCH_RUBRIC}"
            "请以 JSON 格式返回，字段值中不得使用双引号，用单引号或中文引号代替。"
        )

    def _material_user_prompt(
        self,
        outline: ContentOutline,
        section: str,
        search_results,
        feedback_note: str,
        retry_note: str,
    ) -> str:
        """构造研究素材提炼的用户提示词。"""
        return (
            f"报告标题: {outline.title}\n"
            f"当前章节: {section}\n"
            f"核心要点: {outline.key_points}\n"
            f"搜索结果: {search_results}"
            f"{feedback_note}"
            f"{retry_note}\n\n"
            "请提取最相关的核心事实和数据，严格按照以下 JSON 格式返回：\n"
            "{\n"
            '  "section_name": "章节名称",\n'
            '  "raw_data": "数据1（来源1）数据2（来源2）...（不得含双引号）",\n'
            '  "sources": ["来源1的完整URL", "来源2的完整URL"],\n'
            '  "source_quality": ["tier_1", "tier_2"],\n'
            '  "source_notes": ["来源1可信度说明或降级原因", "来源2可信度说明或降级原因"],\n'
            '  "case_candidates": [\n'
            '    {\n'
            '      "name": "企业/机构/产品名称；无法命名写未命名",\n'
            '      "scenario": "业务场景",\n'
            '      "evidence": "能支撑或限制该案例的事实与数据，不得含双引号",\n'
            '      "source_url": "支撑该候选案例的URL",\n'
            '      "source_tier": "tier_1或tier_2或tier_3",\n'
            '      "verification_status": "verified/vendor_claim/aggregate/anonymous/trend_observation",\n'
            '      "is_writable_case": true或false\n'
            '    }\n'
            '  ]\n'
            "}\n"
            "约束：raw_data 中出现的最大来源编号不得超过 sources 数组长度；"
            "sources 不能为空，raw_data 中每个关键事实必须绑定 sources 中的来源编号；"
            "不要为了凑数量保留明显无关或低可信来源；"
            "搜索结果中的 source_quality_hint 和 source_use_guidance 是确定性来源提示，"
            "优先从 tier_1/tier_2 中提炼核心事实，tier_3 只能作辅助线索；"
            "case_candidates 中只有同时具备明确名称、可核验上下文、来源较强且非单纯厂商自述时，"
            "is_writable_case 才能为 true；匿名、综合案例、厂商单方宣传必须为 false。"
        )

    def _build_feedback_note(self, scoped_feedback: list[str]) -> str:
        """把章节级反馈转成补充调研提示。"""
        if not scoped_feedback:
            return ""
        return (
            "\n上一轮评审要求本轮调研重点补充：\n"
            + "\n".join(f"- {item}" for item in scoped_feedback)
            + "\n请优先寻找权威机构报告、公司官方案例、可核验失败案例；"
            "避免只使用媒体转载、厂商软文或无法追溯的匿名案例。"
            "如果一手或准一手来源不足，请在 source_notes 中说明降级原因。"
        )

    def _build_retry_note(
        self,
        section: str,
        attempt: int,
        issues: list[str],
    ) -> str:
        """记录研究素材门禁错误，并生成下一次提炼的纠偏提示。"""
        logger.warning(
            "研究素材门禁未通过，准备重试: section=%s attempt=%d issues=%s",
            section,
            attempt,
            issues,
        )
        issue_text = "；".join(issues)
        return (
            f"\n上一轮输出未通过研究素材门禁：{issue_text}。"
            "请重新提炼该章节素材：sources 必须包含至少 1 个与 raw_data 事实直接相关的完整 URL；"
            "raw_data 中的每个关键事实都必须使用（来源N）标注，且 N <= sources 数量；"
            "source_quality 和 source_notes 必须与 sources 等长。"
        )

def researcher_node(state):
    """LangGraph 节点函数"""
    print("--- 执行：研究员 (Researching) ---")
    logger.info("进入 Researcher 节点")
    with timed_block(logger, "Researcher 节点总耗时", slow_after=30.0):
        researcher = Researcher()
        feedback = state.get("latest_feedback")
        existing_report = state.get("research_report")
        report = researcher.conduct_research(
            state["outline"],
            feedback=feedback,
            existing_report=existing_report,
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
