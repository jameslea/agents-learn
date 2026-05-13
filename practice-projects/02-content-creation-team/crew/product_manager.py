import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sop_artifacts import ContentOutline
from utils.json_utils import parse_llm_json
from utils.logging_utils import get_logger, timed_block

load_dotenv()
logger = get_logger(__name__)

MIN_OUTLINE_SECTIONS = 6
MAX_OUTLINE_SECTIONS = 10
MAX_OUTLINE_ATTEMPTS = 2
BACKGROUND_KEYWORDS = ("背景", "趋势", "现状", "问题", "概览", "定义")
EVIDENCE_KEYWORDS = ("技术", "架构", "能力", "市场", "数据", "证据", "格局", "基础")
CASE_KEYWORDS = ("案例", "场景", "实践", "应用", "落地")
RISK_KEYWORDS = ("风险", "挑战", "限制", "治理", "合规", "失败", "教训")
ACTION_KEYWORDS = ("实施", "路径", "建议", "策略", "路线图", "展望", "决策")
INDUSTRY_ONLY_KEYWORDS = ("制造", "金融", "医疗", "零售", "物流", "供应链", "教育", "能源", "政务", "人力资源")


def _has_any_keyword(section: str, keywords: tuple[str, ...]) -> bool:
    """判断章节标题是否承担某类结构角色。"""
    return any(keyword in section for keyword in keywords)


def validate_outline(outline: ContentOutline) -> list[str]:
    """检查大纲是否足够支撑一篇深度报告。"""
    issues: list[str] = []
    section_count = len(outline.sections)

    if section_count < MIN_OUTLINE_SECTIONS:
        issues.append(
            f"章节数量 {section_count} 少于 {MIN_OUTLINE_SECTIONS}，容易导致报告过于粗略。"
        )

    if section_count > MAX_OUTLINE_SECTIONS:
        issues.append(
            f"章节数量 {section_count} 超过 {MAX_OUTLINE_SECTIONS}，容易导致调研范围失控。"
        )

    broad_case_sections = [
        section
        for section in outline.sections
        if "案例" in section and any(keyword in section for keyword in ["应用", "业务", "行业", "实践"])
    ]
    if section_count <= MIN_OUTLINE_SECTIONS and broad_case_sections:
        issues.append(
            "案例章节过于宽泛，建议拆成多个可独立调研的行业、场景或对象章节。"
        )

    role_checks = [
        ("背景/趋势/问题定义", BACKGROUND_KEYWORDS),
        ("证据基础/技术基础/市场数据", EVIDENCE_KEYWORDS),
        ("案例/场景/实践分析", CASE_KEYWORDS),
        ("风险/挑战/限制/治理", RISK_KEYWORDS),
        ("实施路径/策略建议/未来展望", ACTION_KEYWORDS),
    ]
    for role_name, keywords in role_checks:
        if not any(_has_any_keyword(section, keywords) for section in outline.sections):
            issues.append(f"缺少“{role_name}”类章节。")

    industry_like_sections = [
        section
        for section in outline.sections
        if _has_any_keyword(section, INDUSTRY_ONLY_KEYWORDS)
    ]
    if len(industry_like_sections) >= max(4, section_count // 2):
        has_synthesis_section = any(
            _has_any_keyword(section, ("比较", "归纳", "模式", "框架", "评估", "总结"))
            for section in outline.sections
        )
        if not has_synthesis_section:
            issues.append("大纲偏行业枚举，缺少横向比较、模式归纳或评估框架章节。")

    return issues


class ProductManager:
    def __init__(self):
        model = os.getenv("MODEL_NAME", "deepseek-chat")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        logger.info("加载 ProductManager LLM: model=%s base_url=%s", model, base_url)
        self.llm = ChatOpenAI(
            model=model,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    def plan_content(self, topic: str) -> ContentOutline:
        """根据主题规划内容大纲"""
        system_prompt = (
            "你是一名资深产品经理和内容策划专家。你的任务是根据用户给出的主题，"
            "规划一份结构严谨、逻辑清晰、便于后续调研和写作的深度报告大纲。"
            "请以 JSON 格式返回，字段值中不得使用双引号，用单引号或中文引号代替。"
        )

        retry_note = ""
        latest_outline = None
        latest_issues = []
        for attempt in range(1, MAX_OUTLINE_ATTEMPTS + 1):
            with timed_block(logger, f"PM LLM 规划大纲 attempt={attempt}", slow_after=8.0):
                response = self.llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=self._outline_user_prompt(topic, retry_note))
                ])
            with timed_block(logger, "解析 PM JSON 输出", slow_after=1.0):
                latest_outline = parse_llm_json(response.content, ContentOutline)

            latest_issues = validate_outline(latest_outline)
            if not latest_issues:
                return latest_outline

            logger.warning(
                "PM 大纲质量门禁发现问题: attempt=%d issues=%s",
                attempt,
                latest_issues,
            )
            retry_note = (
                "\n上一版大纲存在问题："
                + "；".join(latest_issues)
                + "\n请重新规划，避免三段式粗略大纲。"
            )

        raise ValueError(
            "PM 大纲质量门禁未通过：\n"
            + "\n".join(f"- {issue}" for issue in latest_issues)
        )

    def _outline_user_prompt(self, topic: str, retry_note: str = "") -> str:
        """构造大纲规划提示词，避免生成过粗的三段式大纲。"""
        return (
            f"请为以下主题规划一份深度报告大纲：{topic}"
            f"{retry_note}\n\n"
            "大纲要求：\n"
            f"- sections 必须包含 {MIN_OUTLINE_SECTIONS}-{MAX_OUTLINE_SECTIONS} 个主要章节\n"
            "- 章节要便于后续独立调研，避免只给“现状/案例/展望”三段式结构\n"
            "- 大纲应包含明确的结构角色：背景/问题定义、证据或技术基础、案例或场景分析、横向比较或模式归纳、风险挑战、实施建议或结论\n"
            "- 如果主题涉及案例、行业实践或落地应用，应优先按“可独立调研且可核验”的场景拆分，不要为了覆盖行业而机械罗列行业\n"
            "- 案例章节数量建议 2-4 个；如果公开案例可能不足，应设置“证据边界/可验证性/风险限制”类章节承接不确定性\n"
            "- 避免全大纲都是行业列表；需要有比较、归纳、评估或决策框架章节把材料上升为观点\n\n"
            "请严格按照以下 JSON 格式返回，不要添加额外字段：\n"
            "{\n"
            '  "title": "报告标题",\n'
            '  "target_audience": "目标受众描述",\n'
            '  "sections": ["章节1标题", "章节2标题", "章节3标题", "章节4标题", "章节5标题", "章节6标题"],\n'
            '  "key_points": ["核心要点1", "核心要点2", "核心要点3"]\n'
            "}"
        )

def pm_node(state):
    """LangGraph 节点函数"""
    print("--- 执行：产品经理 (Planning) ---")
    logger.info("进入 PM 节点: topic=%s", state["topic"])
    with timed_block(logger, "PM 节点总耗时", slow_after=10.0):
        pm = ProductManager()
        outline = pm.plan_content(state["topic"])
    logger.info("PM 节点完成: title=%s sections=%d", outline.title, len(outline.sections))
    return {"outline": outline, "history": [f"PM 规划了大纲：{outline.title}"]}
