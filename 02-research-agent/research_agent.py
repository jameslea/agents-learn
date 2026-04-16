import os
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# 初始化大模型 (根据外层环境变量自动适配 OpenAI 或 DeepSeek)
model_name = os.getenv("MODEL_NAME", "deepseek-chat")
llm = ChatOpenAI(model=model_name, temperature=0.2)

# ==========================================
# 1. 准备工具箱 (Tools)
# ==========================================

# 替代易被反爬过滤的 DuckDuckGo，我们改用永远免费稳定的 Wikipedia
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper

# 初始化维基百科工具，设置语言为中文
api_wrapper = WikipediaAPIWrapper(top_k_results=3, doc_content_chars_max=1000, lang="zh")
search_tool = WikipediaQueryRun(api_wrapper=api_wrapper)
search_tool.name = "web_search"
search_tool.description = "当你需要获取实体的百科级知识与最新信息时使用。输入应当是明确的名词查询词。"

# 工具 2：保存文件到本地 (自定义工具)
@tool
def save_report_to_file(filename: str, content: str) -> str:
    """将生成的报告或总结保存到本地 Markdown 文件中。
    参数 filename: 文件名（需要包含 .md 后缀）
    参数 content: 要保存的文本内容
    """
    # 确保存储目录存在
    save_dir = "outputs"
    os.makedirs(save_dir, exist_ok=True)
    
    file_path = os.path.join(save_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return f"报告已成功保存至: {file_path}"

# 组装工具列表
tools = [search_tool, save_report_to_file]

# ==========================================
# 2. 创建智能体 (Agent)
# ==========================================

# 很多时候，为了约束大模型不要乱动，我们需要给它一点系统提示词
system_prompt = """你是一个严谨的研究助手。
你的工作流程是：
1. 收到用户想要研究的主题后，首先调用网络搜索工具获取相关信息。
2. 对信息进行提炼和总结。
3. 必须调用保存文件工具，将总结好的内容写入到文件中。
4. 最后告诉用户报告已经生成完毕。"""

agent_executor = create_react_agent(
    llm, 
    tools
)

# ==========================================
# 3. 运行测试
# ==========================================

if __name__ == "__main__":
    print("🤖 研究助手启动！正在执行任务...")
    
    # 我们抛出一个包含收集、总结、落盘的综合任务
    user_query = "搜索一下 DeepSeek V3 模型的发布时间和核心亮点，然后总结成一份报告并保存到 deepseek_v3_report.md 文件中。"
    
    query_msg = {"messages": [
        ("system", system_prompt),
        ("user", user_query)
    ]}
    
    # 采用 .stream() 方法，我们可以清楚地看到它是一步步怎么思考和调用的，而不是干等最后结果
    for step_result in agent_executor.stream(query_msg, stream_mode="values"):
        last_message = step_result["messages"][-1]
        last_message.pretty_print()
