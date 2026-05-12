import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sop_artifacts import ReviewFeedback, DraftContent
from crew.json_utils import parse_llm_json

load_dotenv()

class Reviewer:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "deepseek-chat"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    def review_draft(self, draft: DraftContent) -> ReviewFeedback:
        """从多维度评审初稿，输出章节级具体问题"""
        system_prompt = (
            "你是一名资深商业报告评审专家。请从以下四个维度评审报告：\n"
            "1. 逻辑结构：各章节是否有清晰的分析框架，而非纯数据罗列\n"
            "2. 数据来源：每条关键数据是否有数字编号标注如 [1]，且末尾有 '## 参考资料' 列表\n"
            "3. 案例深度：是否有具体、可信的案例，包括失败案例或教训\n"
            "4. 字数与深度：正文是否达到 3000 字，内容是否翔实\n\n"
            "评审标准：若以上任意一项明显不足，则判定为不通过。\n"
            "specific_issues 必须精确到具体章节，格式为 '章节名: 具体问题描述'。\n"
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
            "注意：若字数低于 2500、缺少来源引用、缺少失败案例，必须判定为不通过。"
        )

        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        return parse_llm_json(response.content, ReviewFeedback)

def reviewer_node(state):
    """LangGraph 节点函数"""
    print("--- 执行：评审员 (Reviewing) ---")
    reviewer = Reviewer()
    feedback = reviewer.review_draft(state["draft"])
    new_count = state.get("review_count", 0) + 1
    status = "通过 ✅" if feedback.is_approved else "拒绝 ❌"
    print(f"  ↳ 第 {new_count} 次评审结果：{status}")
    if not feedback.is_approved:
        print(f"  ↳ 章节级问题 ({len(feedback.specific_issues)} 条):")
        for issue in feedback.specific_issues:
            print(f"      • {issue}")
    return {
        "latest_feedback": feedback,
        "review_count": new_count,
        "history": [f"评审员完成第 {new_count} 次评审：{status}，具体问题 {len(feedback.specific_issues)} 条"]
    }
