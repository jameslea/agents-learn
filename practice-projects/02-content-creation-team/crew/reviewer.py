import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sop_artifacts import ReviewFeedback, DraftContent
from utils.cost_utils import tracked_call
from utils.json_utils import parse_llm_json
from utils.logging_utils import get_logger, timed_block
from utils.quality import validate_draft
from utils.report_evaluation import ReportQualityMetrics, evaluate_report_quality
from utils.rubric import REVIEW_RUBRIC

load_dotenv()
logger = get_logger(__name__)

MAX_QUALITY_ENHANCEMENT_ROUNDS = 1
QUALITY_ENHANCEMENT_MAX_REVIEW_COUNT = 3
HIGH_QUALITY_MIN_UNITS = 3800
HIGH_QUALITY_MIN_CASE_RHYTHM_SECTIONS = 4


def quality_enhancement_issues(metrics: ReportQualityMetrics) -> list[str]:
    """返回通过后仍值得做 Writer 增强的问题，不作为硬性事实拒绝。"""
    issues: list[str] = []

    if metrics.units < HIGH_QUALITY_MIN_UNITS:
        issues.append(
            f"全文有效长度 {metrics.units} 低于高质量目标 {HIGH_QUALITY_MIN_UNITS}，"
            "需要补厚案例过程、证据边界、实施条件或决策建议。"
        )
    if metrics.subsections < 15:
        issues.append(f"三级小节数量 {metrics.subsections} 偏少，后半部分或案例章节可能不够展开。")
    if metrics.subsections > 19:
        issues.append(f"三级小节数量 {metrics.subsections} 偏多，可能存在标题堆叠，应合并薄弱小节。")
    if metrics.list_items < 25:
        issues.append(f"列表项数量 {metrics.list_items} 偏少，实施路径、风险边界或建议部分的信息密度不足。")
    if metrics.list_items > 50:
        issues.append(f"列表项数量 {metrics.list_items} 过多，报告可能过碎，应改写为段落分析或表格。")
    if metrics.avg_subsection_units < 100:
        issues.append(f"小节平均厚度 {metrics.avg_subsection_units} 偏低，需要减少短段落堆叠。")
    if metrics.thin_subsections > 2:
        issues.append(f"过薄小节 {metrics.thin_subsections} 个，需合并或补充分析。")
    if metrics.case_rhythm_sections < HIGH_QUALITY_MIN_CASE_RHYTHM_SECTIONS:
        issues.append(
            f"具备成功/挑战/分析完整节奏的案例章节只有 {metrics.case_rhythm_sections} 个，"
            "案例分析深度仍不足。"
        )

    return issues[:5]


def should_request_quality_enhancement(
    state: dict,
    metrics: ReportQualityMetrics,
    review_count: int,
) -> list[str]:
    """判断 Reviewer 已通过后是否仍应进行一次质量增强轮。"""
    if review_count >= QUALITY_ENHANCEMENT_MAX_REVIEW_COUNT:
        return []
    if state.get("quality_enhancement_count", 0) >= MAX_QUALITY_ENHANCEMENT_ROUNDS:
        return []
    return quality_enhancement_issues(metrics)


def build_quality_enhancement_feedback(issues: list[str]) -> ReviewFeedback:
    return ReviewFeedback(
        is_approved=False,
        suggestions=[
            "报告已达到基本通过线，但尚未达到高质量样本标准；请做一轮 Writer 增强，而不是重新堆砌资料。",
            "增强重点是补厚案例过程、合并碎片化小节、增加证据边界和决策建议；不得新增研究素材之外的事实或数字。",
        ],
        specific_issues=[f"质量增强: {issue}" for issue in issues],
        target_agent="writer",
    )


class Reviewer:
    def __init__(self):
        model = os.getenv("MODEL_NAME", "deepseek-chat")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        logger.info("加载 Reviewer LLM: model=%s base_url=%s", model, base_url)
        self.llm = ChatOpenAI(
            model=model,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    def review_draft(self, draft: DraftContent) -> ReviewFeedback:
        """从多维度评审初稿，输出章节级具体问题"""
        system_prompt = (
            "你是一名资深商业报告评审专家。程序化格式门禁已经提前完成，"
            "你只需要评估内容质量：论证是否成立、来源是否支撑核心结论、"
            "案例是否可信、风险与限制是否充分、文章是否自然而非模板化。"
            "specific_issues 必须精确到具体章节，格式为 '章节名: 具体问题描述'。\n"
            "target_agent 选择规则：资料不足、来源质量弱、案例无法核验、缺少失败案例时选 researcher；"
            "结构混乱、表达浅、论证跳跃或文体模板化时选 writer。"
            f"{REVIEW_RUBRIC}"
            "请以 JSON 格式返回，字段值不得使用双引号，用单引号或中文引号代替。"
        )

        # 检查引用情况
        citation_count = len(draft.citations) if draft.citations else 0
        citation_note = f"当前 citations 字段共 {citation_count} 条来源URL。"

        user_prompt = (
            f"请评审以下报告：\n\n"
            f"标题: {draft.title}\n"
            f"字数: {draft.word_count}\n"
            f"{citation_note}\n"
            f"正文:\n{draft.content_markdown}\n\n"
            "请严格按照以下 JSON 格式返回（所有字段必须填写）：\n"
            "{\n"
            '  "is_approved": true或false,\n'
            '  "suggestions": ["整体建议1", "整体建议2"],\n'
            '  "specific_issues": ["章节A: 具体问题描述", "章节B: 具体问题描述"],\n'
            '  "target_agent": "researcher或writer，若通过则为null"\n'
            "}\n"
            "注意：不要因为局部措辞可优化而拒绝；只有影响可信度、分析深度或报告自然度的问题才写入 specific_issues。"
        )

        with timed_block(logger, "Reviewer LLM 评审初稿", slow_after=18.0):
            with tracked_call(logger, "Reviewer LLM 评审初稿", [system_prompt, user_prompt]) as record:
                response = self.llm.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ])
                record["output_payload"] = response.content
        with timed_block(logger, "解析 Reviewer JSON 输出", slow_after=1.0):
            feedback = parse_llm_json(response.content, ReviewFeedback)

        if feedback.is_approved and feedback.specific_issues:
            logger.info(
                "Reviewer 返回 approved=True 但包含 specific_issues，按改进建议处理: issues=%d",
                len(feedback.specific_issues),
            )
            suggestions = feedback.suggestions + [
                f"可选改进：{issue}" for issue in feedback.specific_issues
            ]
            feedback = feedback.model_copy(
                update={
                    "suggestions": suggestions,
                    "specific_issues": [],
                    "target_agent": None,
                }
            )

        return feedback

def reviewer_node(state):
    """LangGraph 节点函数"""
    print("--- 执行：评审员 (Reviewing) ---")
    logger.info("进入 Reviewer 节点")
    with timed_block(logger, "确定性质量门禁", slow_after=1.0):
        deterministic_issues = validate_draft(state["draft"])
    if deterministic_issues:
        new_count = state.get("review_count", 0) + 1
        print(f"  ↳ 第 {new_count} 次评审结果：拒绝 ❌（质量门禁）")
        logger.warning(
            "Reviewer 质量门禁拒绝: round=%d issues=%d detail=%s",
            new_count,
            len(deterministic_issues),
            deterministic_issues,
        )
        feedback = ReviewFeedback(
            is_approved=False,
            suggestions=["先修复程序化质量门禁发现的结构化问题。"],
            specific_issues=[f"质量门禁: {issue}" for issue in deterministic_issues],
            target_agent="writer",
        )
        return {
            "latest_feedback": feedback,
            "review_count": new_count,
            "history": [
                f"评审员完成第 {new_count} 次评审：拒绝 ❌，质量门禁问题 {len(deterministic_issues)} 条："
                + "；".join(deterministic_issues[:3])
            ]
        }

    with timed_block(logger, "Reviewer 节点 LLM 评审路径", slow_after=25.0):
        reviewer = Reviewer()
        feedback = reviewer.review_draft(state["draft"])
    new_count = state.get("review_count", 0) + 1

    if feedback.is_approved:
        metrics = evaluate_report_quality(state["draft"].content_markdown, name=state["draft"].title)
        enhancement_issues = should_request_quality_enhancement(state, metrics, new_count)
        if enhancement_issues:
            feedback = build_quality_enhancement_feedback(enhancement_issues)
            status = "需增强 🔁"
            print(f"  ↳ 第 {new_count} 次评审结果：通过但质量增强 🔁")
            logger.info(
                "Reviewer 通过后触发质量增强: round=%d units=%d subsections=%d list_items=%d issues=%s",
                new_count,
                metrics.units,
                metrics.subsections,
                metrics.list_items,
                enhancement_issues,
            )
            return {
                "latest_feedback": feedback,
                "review_count": new_count,
                "quality_enhancement_count": state.get("quality_enhancement_count", 0) + 1,
                "history": [
                    f"评审员完成第 {new_count} 次评审：{status}，质量增强问题 {len(enhancement_issues)} 条："
                    + "；".join(enhancement_issues[:3])
                ],
            }

    status = "通过 ✅" if feedback.is_approved else "拒绝 ❌"
    print(f"  ↳ 第 {new_count} 次评审结果：{status}")
    logger.info(
        "Reviewer LLM 评审完成: round=%d approved=%s target=%s suggestions=%d issues=%d",
        new_count,
        feedback.is_approved,
        feedback.target_agent,
        len(feedback.suggestions),
        len(feedback.specific_issues),
    )
    if not feedback.is_approved:
        logger.warning(
            "Reviewer LLM 拒绝详情: round=%d suggestions=%s issues=%s",
            new_count,
            feedback.suggestions,
            feedback.specific_issues,
        )
    if not feedback.is_approved:
        print(f"  ↳ 章节级问题 ({len(feedback.specific_issues)} 条):")
        for issue in feedback.specific_issues:
            print(f"      • {issue}")
    history_msg = f"评审员完成第 {new_count} 次评审：{status}，具体问题 {len(feedback.specific_issues)} 条"
    if not feedback.is_approved and feedback.specific_issues:
        history_msg += "：" + "；".join(feedback.specific_issues[:3])
    return {
        "latest_feedback": feedback,
        "review_count": new_count,
        "history": [history_msg]
    }
