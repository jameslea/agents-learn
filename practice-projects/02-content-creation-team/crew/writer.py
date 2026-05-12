import os
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sop_artifacts import DraftContent, ResearchReport, ContentOutline, ReviewFeedback
from crew.json_utils import parse_llm_json

load_dotenv()

class Writer:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "deepseek-chat"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    def write_draft(
        self,
        outline: ContentOutline,
        research: ResearchReport,
        feedback: Optional[ReviewFeedback] = None,
        history_summary: str = ""
    ) -> DraftContent:
        """根据大纲和研究素材撰写初稿，参考历史摘要和评审反馈"""
        system_prompt = (
            "你是一名专业的商业分析师和深度报告作家。你的任务是根据大纲和研究素材，"
            "撰写一份专业、深度、数据翔实的 Markdown 报告。\n"
            "严格要求：\n"
            "1. 正文不少于 3000 字，内容充实，要有分析和解读。\n"
            "2. **引用格式**：正文中使用数字编号标注来源，如 [1], [2]。不得在正文直接出现 URL。\n"
            "3. **末尾索引**：在报告末尾增加 '## 参考资料' 章节，按编号列出对应的完整 URL。\n"
            "4. 报告需包含失败案例或落地教训，不能只写成功案例。\n"
            "5. 每个章节需要有横向对比或纵向分析，而非单纯罗列。\n"
            "请以 JSON 格式返回，字段值不得使用双引号，用单引号或中文引号代替。"
        )

        # 整合素材，带来源绑定
        context_parts = []
        source_pool = []
        for m in research.materials:
            context_parts.append(
                f"### {m.section_name}\n"
                f"内容: {m.raw_data}\n"
                f"该章节可用来源: {m.sources}"
            )
            source_pool.extend(m.sources)
        context = "\n\n".join(context_parts)

        # 评审反馈与历史摘要处理
        history_info = f"\n## 历史执行摘要\n{history_summary}\n" if history_summary else ""
        feedback_section = ""
        if feedback and not feedback.is_approved:
            feedback_section = (
                "\n## 上一版评审意见（必须全部修复）\n"
                f"整体建议:\n" +
                "\n".join(f"- {s}" for s in feedback.suggestions) +
                "\n\n章节级具体问题:\n" +
                "\n".join(f"- {i}" for i in feedback.specific_issues) +
                "\n\n请在本次修改中逐条解决以上所有问题。\n"
            )

        user_prompt = (
            f"报告标题: {outline.title}\n"
            f"目标受众: {outline.target_audience}\n"
            f"大纲结构: {outline.sections}\n"
            f"{history_info}"
            f"{feedback_section}\n"
            f"研究素材（包含数据和对应的来源池）:\n{context}\n\n"
            "请撰写完整报告初稿（不少于 3000 字），要求：\n"
            "- 逻辑连贯，每章有分析深度，不仅罗列数据\n"
            "- 包含至少 1 个失败案例或落地挑战\n"
            "- **正文引用标记为 [1], [2] 等**\n"
            "- **报告末尾必须有 '## 参考资料' 列表**\n"
            "- citations 字段仅需列出所有去重后的 URL 列表\n\n"
            "严格按照以下 JSON 格式返回：\n"
            "{\n"
            '  "title": "报告标题",\n'
            '  "content_markdown": "完整 Markdown 正文（含末尾参考资料，不少于 3000 字，不得含双引号）",\n'
            '  "word_count": 正文字数整数,\n'
            '  "citations": ["URL1", "URL2", ...]\n'
            "}"
        )

        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        return parse_llm_json(response.content, DraftContent)

def writer_node(state):
    """LangGraph 节点函数"""
    print("--- 执行：撰稿人 (Writing) ---")
    writer = Writer()
    feedback = state.get("latest_feedback")
    history_summary = state.get("history_summary", "")
    if feedback and not feedback.is_approved:
        print(f"  ↳ 接收评审反馈与历史摘要进行修改")
    draft = writer.write_draft(
        state["outline"], 
        state["research_report"], 
        feedback=feedback, 
        history_summary=history_summary
    )
    print(f"  ↳ 生成初稿，字数: {draft.word_count}，引用来源: {len(draft.citations)} 条")
    return {
        "draft": draft, 
        "draft_history": [draft],
        "history": [f"撰稿人生成了初稿（{draft.word_count} 字）"]
    }
