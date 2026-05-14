from typing import Optional

from sop_artifacts import ContentOutline, ReviewFeedback
from utils.rubric import RESEARCH_RUBRIC


def build_material_system_prompt() -> str:
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


def build_material_user_prompt(
    outline: ContentOutline,
    section: str,
    search_results,
    feedback_note: str,
) -> str:
    """构造研究素材提炼的用户提示词。"""
    return (
        f"报告标题: {outline.title}\n"
        f"当前章节: {section}\n"
        f"核心要点: {outline.key_points}\n"
        f"搜索结果: {search_results}"
        f"{feedback_note}"
        "\n\n"
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


def build_feedback_note(feedback: Optional[ReviewFeedback]) -> str:
    """把评审反馈转成全局调研提示。"""
    if not feedback or feedback.is_approved or feedback.target_agent != "researcher":
        return ""
    items = [*feedback.suggestions, *feedback.specific_issues]
    if not items:
        return ""
    return (
        "\n上一轮评审要求本轮调研重点补充：\n"
        + "\n".join(f"- {_shorten(item, 120)}" for item in items[:4])
        + "\n请优先寻找权威机构报告、公司官方案例、可核验失败案例；"
        "避免只使用媒体转载、厂商软文或无法追溯的匿名案例。"
        "如果一手或准一手来源不足，请在 source_notes 中说明降级原因。"
    )


def _shorten(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
