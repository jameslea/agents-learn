import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

class Summarizer:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME", "deepseek-chat"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        )

    def summarize_history(self, history: list[str], current_summary: str = "") -> str:
        """将冗长的历史记录压缩为简短的摘要"""
        system_prompt = (
            "你是一个历史记录摘要专家。你的任务是将一组 Agent 协作的历史日志压缩成简短的摘要。"
            "你需要保留：1. 已经完成的重大里程碑；2. 评审发现的核心问题；3. 当前正在尝试的方向。"
            "删除冗余的细节，保持摘要在 300 字以内。"
        )

        history_text = "\n".join(history)
        user_prompt = (
            f"已有摘要: {current_summary}\n\n"
            f"新增历史记录:\n{history_text}\n\n"
            "请生成一份最新的、压缩后的历史摘要。"
        )

        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        return response.content

def summarizer_node(state):
    """摘要节点：压缩历史上下文"""
    print("--- 执行：摘要助手 (Summarizing) ---")
    summarizer = Summarizer()
    # 只有当历史记录较长时才执行真正的 LLM 摘要，否则简单合并
    if len(state.get("history", [])) > 5:
        new_summary = summarizer.summarize_history(
            state["history"], 
            state.get("history_summary", "")
        )
    else:
        new_summary = state.get("history_summary", "") + "\n" + "\n".join(state.get("history", []))
    
    return {"history_summary": new_summary}
