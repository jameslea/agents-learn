import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sop_artifacts import ContentOutline
from crew.json_utils import parse_llm_json

load_dotenv()

class ProductManager:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "deepseek-chat"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    def plan_content(self, topic: str) -> ContentOutline:
        """根据主题规划内容大纲"""
        system_prompt = (
            "你是一名资深产品经理和内容策划专家。你的任务是根据用户给出的主题，"
            "规划一份结构严谨、逻辑清晰的深度报告大纲。"
            "请以 JSON 格式返回，字段值中不得使用双引号，用单引号或中文引号代替。"
        )

        user_prompt = (
            f"请为以下主题规划一份深度报告大纲：{topic}\n\n"
            "请严格按照以下 JSON 格式返回，不要添加额外字段：\n"
            "{\n"
            '  "title": "报告标题",\n'
            '  "target_audience": "目标受众描述",\n'
            '  "sections": ["章节1标题", "章节2标题", "章节3标题"],\n'
            '  "key_points": ["核心要点1", "核心要点2", "核心要点3"]\n'
            "}"
        )

        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        return parse_llm_json(response.content, ContentOutline)

def pm_node(state):
    """LangGraph 节点函数"""
    print("--- 执行：产品经理 (Planning) ---")
    pm = ProductManager()
    outline = pm.plan_content(state["topic"])
    return {"outline": outline, "history": [f"PM 规划了大纲：{outline.title}"]}
