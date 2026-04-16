import os
import logging
from dotenv import load_dotenv
from smolagents import CodeAgent, OpenAIServerModel, tool

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ==========================================
# 1. 定义模型 (Model)
# ==========================================
# smolagents 认为智能体的本质是“写代码”，所以模型必须支持代码生成。
# 我们使用 OpenAIServerModel 配合项目现有的 DeepSeek 接口。
model = OpenAIServerModel(
    model_id=os.getenv("MODEL_NAME", "deepseek-chat"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_base=os.getenv("OPENAI_BASE_URL"),
)

# ==========================================
# 2. 定义工具 (Tools)
# ==========================================
# 在 smolagents 中，工具通过 Python 函数直接定义。
# 文档字符串 (Docstring) 是必须的，因为 Agent 会读它来理解工具。

@tool
def calculate_complexity(text: str) -> int:
    """
    计算文本的“复杂度分数”。
    规则：文本长度乘以 2，再加上文本中包含的空格数量。
    
    Args:
        text: 需要计算复杂度的源字符串。
    """
    return len(text) * 2 + text.count(" ")

# ==========================================
# 3. 初始化并运行 Agent
# ==========================================
# CodeAgent 是 smolagents 的灵魂：
# 1. 它不生成 JSON 指令。
# 2. 它生成一个 Python 代码块，在内部的安全沙箱中运行逻辑。
agent = CodeAgent(
    tools=[calculate_complexity],
    model=model,
    add_base_tools=False  # 关闭默认搜索工具，专注看代码生成
)

if __name__ == "__main__":
    task = "计算字符串 'Hello Agents Learn' 的复杂度分数，然后告诉我该分数的平方根是多少。"
    
    logger.info(f"🚀 任务开始: {task}")
    
    # 运行 Agent
    # 在终端中，你会看到它不仅仅调用了工具，还自己写了 math.sqrt(...)
    response = agent.run(task)
    
    print("\n" + "="*30)
    print(f"Agent 的最终答案: {response}")
    print("="*30)
