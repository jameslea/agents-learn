import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.llm_factory import build_llm, resolve_provider_config
from sop_artifacts import ReviewFeedback, DraftContent
from utils.cost_utils import tracked_call
from utils.json_utils import parse_llm_json
from utils.logging_utils import get_logger, timed_block
from utils.quality import validate_draft
from utils.rubric import REVIEW_RUBRIC

load_dotenv()
logger = get_logger(__name__)


class Reviewer:
    def __init__(self):
        provider_config = resolve_provider_config()
        logger.info(
            "加载 Reviewer LLM: provider=%s model=%s base_url=%s",
            provider_config.name,
            provider_config.model,
            provider_config.base_url,
        )
        self.llm = build_llm(json_mode=True)

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
