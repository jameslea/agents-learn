import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import SystemMessage, HumanMessage
from sop_artifacts import ResearchMaterial, ResearchReport, ContentOutline, ReviewFeedback
from crew.json_utils import parse_llm_json
from typing import Optional

load_dotenv()

class Researcher:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "deepseek-chat"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        self.search_tool = TavilySearchResults(max_results=5)  # 增加搜索结果数量

    def conduct_research(
        self,
        outline: ContentOutline,
        feedback: Optional[ReviewFeedback] = None
    ) -> ResearchReport:
        """根据大纲逐个章节进行研究，若有评审反馈则针对性补充"""
        materials = []

        # 从评审反馈中提取章节级问题，用于定向补充
        section_issues = {}
        if feedback and feedback.specific_issues:
            for issue in feedback.specific_issues:
                if ": " in issue:
                    sec, problem = issue.split(": ", 1)
                    section_issues[sec.strip()] = problem.strip()

        for section in outline.sections:
            print(f"正在研究章节: {section}...")

            # 1. 搜索（若有针对该章节的反馈，加入改进关键词）
            issue_hint = section_issues.get(section, "")
            search_query = f"{outline.title} {section} 深度资料 行业数据 实际案例"
            if issue_hint:
                search_query += f" {issue_hint}"
                print(f"  ↳ 针对评审问题补充搜索: {issue_hint}")

            search_results = self.search_tool.invoke(search_query)

            # 2. 提炼素材，强制绑定数据与来源
            system_prompt = (
                "你是一名专业的互联网研究员。你的任务是针对特定报告章节，"
                "从搜索结果中提炼高质量、有事实支撑的素材。"
                "关键要求：每条数据或事实后必须在括号内标注来源序号，如（来源1）（来源2）。"
                "sources 列表中的 URL 需与 raw_data 中的序号一一对应。"
                "请以 JSON 格式返回，字段值中不得使用双引号，用单引号或中文引号代替。"
            )

            feedback_note = ""
            if issue_hint:
                feedback_note = f"\n评审员指出本章节问题：{issue_hint}\n请重点补充相关内容。"

            user_prompt = (
                f"报告标题: {outline.title}\n"
                f"当前章节: {section}\n"
                f"核心要点: {outline.key_points}\n"
                f"搜索结果: {search_results}"
                f"{feedback_note}\n\n"
                "请提取最相关的核心事实和数据，严格按照以下 JSON 格式返回：\n"
                "{\n"
                '  "section_name": "章节名称",\n'
                '  "raw_data": "数据1（来源1）数据2（来源2）...（不得含双引号）",\n'
                '  "sources": ["来源1的完整URL", "来源2的完整URL"]\n'
                "}"
            )

            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            material = parse_llm_json(response.content, ResearchMaterial)
            materials.append(material)

        return ResearchReport(materials=materials)

def researcher_node(state):
    """LangGraph 节点函数"""
    print("--- 执行：研究员 (Researching) ---")
    researcher = Researcher()
    feedback = state.get("latest_feedback")
    report = researcher.conduct_research(state["outline"], feedback=feedback)
    
    # B4: 中间质量门禁 (Quality Gate)
    warnings = []
    for m in report.materials:
        if not m.sources or len(m.sources) < 1:
            warnings.append(f"章节 '{m.section_name}' 搜集到的素材过少，请注意。")
    
    history_msg = "研究员完成了全章节资料搜集"
    if warnings:
        history_msg += f"（注意：{len(warnings)} 个章节素材质量可能不足）"
        
    return {"research_report": report, "history": [history_msg]}
