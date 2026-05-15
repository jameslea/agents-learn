import os
import re
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.llm_factory import build_llm, resolve_provider_config
from sop_artifacts import DraftContent, ResearchReport, ContentOutline, ReviewFeedback
from utils.cost_utils import tracked_call
from utils.json_utils import parse_llm_json
from utils.logging_utils import get_logger, timed_block
from utils.quality import (
    infer_source_tier,
    normalize_draft_references,
    ranked_source_records,
    source_quality_summary,
    validate_draft,
)
from utils.rubric import WRITING_RUBRIC, build_source_audit_text

load_dotenv()
logger = get_logger(__name__)

MAX_WRITER_QUALITY_REPAIR_ATTEMPTS = 2
CASE_SECTION_KEYWORDS = ("案例", "场景", "实践", "应用", "落地")
NON_CASE_SECTION_KEYWORDS = ("横向", "比较", "对比", "归纳", "风险", "挑战", "实施", "路径", "建议", "证据边界")


def format_case_candidates(material) -> str:
    """把研究员识别的案例候选转成 Writer 可执行的证据边界提示。"""
    if not getattr(material, "case_candidates", None):
        return "无可核验案例候选；本章节不得编造成具体企业案例，只能写场景模式、趋势观察或证据缺口。"

    lines = []
    for candidate in material.case_candidates:
        label = "可写成具体案例" if candidate.is_writable_case else "不可作为核心案例"
        lines.append(
            f"- {label}: {candidate.name} | {candidate.scenario} | {candidate.source_tier} | "
            f"{candidate.verification_status} | {candidate.evidence} | {candidate.source_url}"
        )
    return "\n".join(lines)


def has_writable_case_candidate(material) -> bool:
    """判断研究素材是否包含可写成具体公开案例的候选。"""
    return any(
        getattr(candidate, "is_writable_case", False)
        for candidate in getattr(material, "case_candidates", [])
    )


def is_case_outline_section(section: str) -> bool:
    """判断大纲章节是否以案例/场景承载为主，排除横向比较和风险类章节。"""
    if any(keyword in section for keyword in NON_CASE_SECTION_KEYWORDS):
        return False
    return any(keyword in section for keyword in CASE_SECTION_KEYWORDS)


def downgrade_case_section_title(section: str) -> str:
    """把证据不足的案例章降级为证据边界/趋势观察章，避免主标题继续暗示具体案例。"""
    cleaned = re.sub(r"^\s*(?:案例|场景)[一二三四五六七八九十\d]*[：:、\-\s]*", "", section).strip()
    cleaned = cleaned.replace("实际案例", "应用场景").replace("应用案例", "应用场景").replace("案例", "场景")
    cleaned = cleaned or section
    return f"证据边界与趋势观察：{cleaned}"


def build_evidence_adjusted_outline(
    outline: ContentOutline,
    research: ResearchReport,
) -> tuple[ContentOutline, dict[str, str]]:
    """根据研究结果降级没有可写案例候选的案例章。"""
    material_by_section = {material.section_name: material for material in research.materials}
    adjusted_sections: list[str] = []
    section_aliases: dict[str, str] = {}

    for section in outline.sections:
        material = material_by_section.get(section)
        should_downgrade = (
            material is not None
            and is_case_outline_section(section)
            and not has_writable_case_candidate(material)
        )
        if should_downgrade:
            adjusted = downgrade_case_section_title(section)
            section_aliases[section] = adjusted
            adjusted_sections.append(adjusted)
            continue
        adjusted_sections.append(section)

    if not section_aliases:
        return outline, {}

    adjusted_title = outline.title
    if len(section_aliases) >= 2:
        adjusted_title = (
            adjusted_title
            .replace("实际应用案例", "应用场景与证据边界")
            .replace("应用案例", "应用场景与证据边界")
        )
    logger.info("Writer 降级证据不足案例章: count=%d sections=%s", len(section_aliases), list(section_aliases))
    return outline.model_copy(update={"title": adjusted_title, "sections": adjusted_sections}), section_aliases


def build_writer_editorial_contract(outline: ContentOutline) -> str:
    """生成稳定的写作契约，减少同一大纲下的版式随机波动。"""
    section_count = len(outline.sections)
    case_sections = [section for section in outline.sections if is_case_outline_section(section)]
    case_section_hint = "、".join(case_sections[:4]) or "案例或应用章节"
    return (
        "## 编辑契约（优先遵守，用来稳定报告节奏）\n"
        f"- 本报告大纲有 {section_count} 个主章节，目标写成主编式深度报告，而不是逐章填空。\n"
        "- 目标结构密度参考高质量样本：全文通常 15-19 个有效三级小节、28-40 条列表项、"
        "多数三级小节应有 2 段以上正文或正文+清单支撑。\n"
        "- 列表项不是越多越好；如果全文列表超过 50 条，应合并为段落分析、紧凑表格或更厚的小节。\n"
        "- 不要把“格式丰富”理解成增加更多短标题；如果只能写一两句，就合并到相邻小节并写厚分析。\n"
        f"- 案例节奏重点覆盖：{case_section_hint}。每个核心案例章优先形成"
        "“成功或可行模式 -> 挑战/失败教训 -> 横向或纵向分析”的编辑节奏，"
        "但不要机械复制完全相同的小标题。\n"
        "- 当案例证据较弱时，优先写成一个较厚的案例分析小节并集中说明证据边界，"
        "不要把弱证据拆成多个短小节反复解释。\n"
        "- 后半部分必须继续有内部结构：风险/证据边界、实施路径、评估框架、组织建议中至少 2 个主章节应拆出三级小节。\n"
        "- 至少安排 1 个紧凑对比表或矩阵，用于比较场景、部署模式、风险等级、实施阶段或决策条件；表格要服务判断，不能只是装饰。\n"
        "- 清单应优先放在价值归纳、风险边界、实施路径、最佳实践和高管建议中，避免整篇只有连续段落。\n"
        "- 写作时保持证据克制：强来源支撑具体结论，弱来源只支撑趋势观察或边界说明。\n"
    )


def build_quality_repair_feedback(
    quality_issues: list[str],
    previous_feedback: Optional[ReviewFeedback] = None,
) -> ReviewFeedback:
    """把确定性质量门禁问题转成 Writer 可直接吸收的本地修复反馈。"""
    suggestions = ["先修复程序化质量门禁发现的结构化问题，再保持原有内容质量。"]
    specific_issues = [f"质量门禁: {issue}" for issue in quality_issues]

    if previous_feedback and not previous_feedback.is_approved:
        suggestions.extend(previous_feedback.suggestions)
        specific_issues.extend(previous_feedback.specific_issues)

    return ReviewFeedback(
        is_approved=False,
        suggestions=suggestions,
        specific_issues=specific_issues,
        target_agent="writer",
    )


class Writer:
    def __init__(self):
        provider_config = resolve_provider_config()
        logger.info(
            "加载 Writer LLM: provider=%s model=%s base_url=%s",
            provider_config.name,
            provider_config.model,
            provider_config.base_url,
        )
        self.llm = build_llm(json_mode=True)

    def write_draft(
        self,
        outline: ContentOutline,
        research: ResearchReport,
        feedback: Optional[ReviewFeedback] = None,
    ) -> DraftContent:
        """根据大纲和研究素材撰写初稿，必要时参考评审反馈。"""
        outline, section_aliases = build_evidence_adjusted_outline(outline, research)
        system_prompt = (
            "你是一名专业的商业分析师和深度报告作家。你的任务是根据大纲和研究素材，"
            "撰写一份专业、深度、数据翔实且自然流畅的 Markdown 报告。"
            "优先保证论证质量、材料取舍和读者可读性；格式要求由用户消息给出。"
            "请以 JSON 格式返回，字段值不得使用双引号，用单引号或中文引号代替。"
        )

        # 整合素材，带来源绑定
        selected_sources = ranked_source_records(research, max_sources=15)
        source_number_by_url = {
            source["url"]: index
            for index, source in enumerate(selected_sources, 1)
        }
        context_parts = []
        for m in research.materials:
            source_details = []
            for index, source in enumerate(m.sources, 1):
                normalized_source = source.strip()
                if normalized_source not in source_number_by_url:
                    continue
                declared_quality = m.source_quality[index - 1] if index - 1 < len(m.source_quality) else "tier_3"
                quality = infer_source_tier(normalized_source, declared_quality)
                note = m.source_notes[index - 1] if index - 1 < len(m.source_notes) else "未提供来源可信度说明"
                source_details.append(
                    f"章节来源{index} -> 全局[{source_number_by_url[normalized_source]}]: {normalized_source} | {quality} | {note}"
                )
            context_parts.append(
                f"### {section_aliases.get(m.section_name, m.section_name)}\n"
                + (f"原始大纲章节: {m.section_name}\n" if m.section_name in section_aliases else "")
                + f"内容: {m.raw_data}\n"
                f"该章节入选来源与可信度:\n" + ("\n".join(source_details) or "无入选来源，避免为该章节引入未给出的具体数字或案例。")
                + "\n该章节案例候选与可写性:\n"
                + format_case_candidates(m)
            )
        source_index = "\n".join(
            f"[{index}] {source['url']} | {source['tier']} | {source['note']}"
            for index, source in enumerate(selected_sources, 1)
        )
        context = "\n\n".join(context_parts)
        source_audit = build_source_audit_text(source_quality_summary(research))
        logger.info(
            "Writer 整合研究素材: materials=%d selected_sources=%d context_chars=%d",
            len(research.materials),
            len(selected_sources),
            len(context),
        )

        # 评审反馈与历史摘要处理
        feedback_section = ""
        if feedback and not feedback.is_approved:
            feedback_section = (
                "\n## 上一版评审意见（优先处理影响通过的问题）\n"
                f"整体建议:\n" +
                "\n".join(f"- {s}" for s in feedback.suggestions) +
                "\n\n章节级具体问题:\n" +
                "\n".join(f"- {i}" for i in feedback.specific_issues) +
                "\n\n请优先解决 specific_issues 中影响可信度、结构或引用闭环的问题；"
                "suggestions 可在不破坏报告自然度的前提下吸收。\n"
            )

        structure_guidance = (
            f"{build_writer_editorial_contract(outline)}\n"
            "## 首轮通过的结构蓝图（生成前先按此规划，不要输出规划过程）\n"
            "1. 三级小节用于承载材料密集或需要分层论证的章节，不要给每个主章节机械套 1.1/1.2/1.3。\n"
            "2. 案例/应用章节通常安排 1-3 个编辑化三级小节；证据充足时可使用："
            "### 成功案例、### 失败教训/挑战与教训、### 横向对比/纵向分析；"
            "证据不足时应合并为厚段落并集中说明限制，不要硬拆。\n"
            "3. 风险、证据边界、实施建议或结论前章节至少选择 2 个进行内部拆分，"
            "但小节标题要服务内容，不要为了凑结构而拆短小节。\n"
            "4. 实施建议类章节可拆成：### 评估框架、### 分阶段路线图、"
            "### 常见错误、### 最佳实践；每个小节要解释原因、适用条件和风险。\n"
            "5. 返回 JSON 前自检：如果某个三级小节只有一两句或一条列表，"
            "应补充分析或合并；全文允许少量短小节，但不能大量短小节。\n"
            "6. 返回 JSON 前自检：如果列表项超过 50 条，说明内容过碎，应把部分清单改写成段落判断或表格。"
        )

        user_prompt = (
            f"报告标题: {outline.title}\n"
            f"目标受众: {outline.target_audience}\n"
            f"大纲结构: {outline.sections}\n"
            f"{feedback_section}\n"
            f"研究素材（包含数据和对应的来源池）:\n{context}\n\n"
            f"{source_audit}\n\n"
            f"可用来源索引（正文和参考资料只能使用这些编号和 URL）:\n{source_index}\n\n"
            f"{structure_guidance}\n"
            "请撰写完整报告初稿。输出需满足：\n"
            f"- 正文不少于 3000 字，以 '# {outline.title}' 开始\n"
            "- 正文主要章节使用编号标题，如 '## 一、行业背景'；'## 参考资料' 不编号\n"
            "- 依据章节内容自然安排写法，避免机械套用同一种小标题或段落顺序；全文应包含适量三级小节和列表化结构\n"
            "- 优先满足编辑契约中的结构密度目标：15-19 个有效三级小节、28-40 条列表项、至少 1 个紧凑对比表或矩阵\n"
            "- 案例或应用章节可拆成 '### 成功案例'、'### 失败教训/挑战与教训'、'### 横向对比/纵向分析' 等内部结构，但材料不足时应合并为厚分析而不是硬拆\n"
            "- 风险、证据边界、实施建议或结论前章节也要有内部小节，避免只有前半篇结构丰富、后半篇变成连续段落\n"
            "- 三级小节下面需要有充分正文或清单支撑；如果只能写一两句，应合并到上级章节\n"
            "- 实施、建议或展望章节应包含清单化的实施路径、最佳实践、常见错误或行动建议\n"
            "- 不只罗列资料，要有分析判断；整篇报告包含必要的风险、限制、失败案例或落地教训\n"
            f"- {WRITING_RUBRIC}\n"
            "- 只有研究素材明确提供且可绑定来源的数字，才能写成具体量化结果\n"
            "- 对【综合案例】只能概括模式、场景和限制，不得补写具体企业、项目时间、精确收益或损失数字\n"
            "- 只有研究素材 case_candidates 中 is_writable_case=true 的候选，才能写成具体公开案例；"
            "is_writable_case=false 的候选只能写成厂商主张、趋势观察、场景模式或证据缺口\n"
            "- 如果某个案例章节没有可写案例候选，不要使用 '成功案例' 小标题；"
            "改用 '可行模式与证据边界'、'公开证据缺口' 或 '趋势观察' 等更克制标题\n"
            "- 如果缺少公开可核验案例，应直接说明“公开案例不足/仅能作为趋势观察”，不要构造案例填充\n"
            "- 不能因为案例不足而缩短报告；应通过证据边界、行业对比、实施前提、KPI设计、风险控制和决策建议展开分析\n"
            "- 正文引用使用 [1], [2] 等编号，不在正文直接写 URL\n"
            "- 末尾必须有 '## 参考资料'，格式必须是 '[1] https://...'，只列正文实际引用过的来源 URL，不得编造来源\n"
            "- citations 字段仅需列出所有去重后的 URL 列表\n\n"
            "严格按照以下 JSON 格式返回：\n"
            "{\n"
            '  "title": "报告标题",\n'
            '  "content_markdown": "完整 Markdown 正文（含末尾参考资料，不少于 3000 字，不得含双引号）",\n'
            '  "word_count": 正文字数整数,\n'
            '  "citations": ["URL1", "URL2", ...]\n'
            "}"
        )

        with timed_block(logger, "Writer LLM 生成初稿", slow_after=25.0):
            with tracked_call(logger, "Writer LLM 生成初稿", [system_prompt, user_prompt]) as record:
                response = self.llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ])
                record["output_payload"] = response.content
        with timed_block(logger, "解析 Writer JSON 输出", slow_after=1.0):
            return parse_llm_json(response.content, DraftContent)

def writer_node(state):
    """LangGraph 节点函数"""
    print("--- 执行：撰稿人 (Writing) ---")
    logger.info("进入 Writer 节点")
    draft = None
    quality_issues: list[str] = []
    local_repair_count = 0
    with timed_block(logger, "Writer 节点总耗时", slow_after=30.0):
        writer = Writer()
        feedback = state.get("latest_feedback")
        active_feedback = feedback
        if feedback and not feedback.is_approved:
            print(f"  ↳ 接收评审反馈进行修改")
            logger.info(
                "Writer 接收返工反馈: suggestions=%d issues=%d target=%s",
                len(feedback.suggestions),
                len(feedback.specific_issues),
                feedback.target_agent,
            )
        max_attempts = 1 + MAX_WRITER_QUALITY_REPAIR_ATTEMPTS
        for attempt in range(1, max_attempts + 1):
            draft = writer.write_draft(
                state["outline"],
                state["research_report"],
                feedback=active_feedback,
            )
            logger.info(
                "Writer 生成草稿: attempt=%d word_count=%d citations=%d",
                attempt,
                draft.word_count,
                len(draft.citations),
            )
            draft = normalize_draft_references(draft)
            logger.info("Writer 规范化参考资料: citations=%d", len(draft.citations))
            with timed_block(logger, "Writer 本地质量门禁", slow_after=1.0):
                quality_issues = validate_draft(draft)
            if not quality_issues:
                logger.info("Writer 本地质量门禁通过: attempt=%d", attempt)
                break

            logger.warning(
                "Writer 本地质量门禁未通过: attempt=%d issues=%d detail=%s",
                attempt,
                len(quality_issues),
                quality_issues,
            )
            if attempt >= max_attempts:
                break

            local_repair_count += 1
            print(f"  ↳ 本地质量门禁未通过，Writer 自修第 {local_repair_count} 次")
            active_feedback = build_quality_repair_feedback(
                quality_issues,
                previous_feedback=feedback,
            )
    if draft is None:
        raise RuntimeError("Writer 未生成草稿。")

    print(f"  ↳ 生成初稿，字数: {draft.word_count}，引用来源: {len(draft.citations)} 条")
    logger.info("Writer 初稿生成: word_count=%d citations=%d", draft.word_count, len(draft.citations))
    history_msg = f"撰稿人生成了初稿（{draft.word_count} 字）"
    if local_repair_count:
        history_msg += f"，本地质量自修 {local_repair_count} 次"
    if quality_issues:
        logger.warning("初稿质量门禁发现问题: issues=%d detail=%s", len(quality_issues), quality_issues)
        history_msg += f"，质量门禁发现 {len(quality_issues)} 个问题"
        history_msg += "：" + "；".join(quality_issues[:3])
    else:
        logger.info("初稿质量门禁通过")
    return {
        "draft": draft, 
        "draft_history": [draft],
        "history": [history_msg]
    }
