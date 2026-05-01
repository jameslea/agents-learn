import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 确保在项目中创建了 .env 文件，并写入了 OPENAI_API_KEY=你的密钥
load_dotenv() 

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.llm_factory import build_llm

# 1. 定义一个简单的工具 (Tool)
# Agent 推理时，如果发现自己无法回答，会尝试调用带有明确描述的工具。
@tool
def get_weather(location: str) -> str:
    """获取指定城市的天气状况。"""
    # 这里我们用一个硬性固定的返回值来模拟外部 API 调用
    if "北京" in location:
        return "晴朗，25度"
    elif "上海" in location:
        return "多云，28度"
    return "未知天气"

# 2. 也是 Agent 的大脑 (LLM / Planning)
# 如果你配置了 DeepSeek，推荐使用 deepseek-v4-flash，并通过 DEEPSEEK_THINKING 控制思考模式
model_name = os.getenv("MODEL_NAME", "deepseek-v4-flash")
llm = build_llm(model_name=model_name, temperature=0)

# 工具列表
tools = [get_weather]

# 3. 组装 Agent (这里使用了 langgraph 预制的 react 循坏代理)
# 它自动集成了：接收用户输入 -> LLM 决定动作 -> 调用工具(Action) -> 得到观察结果(Observation) -> 生成最终回答 的闭环。
agent_executor = create_react_agent(llm, tools)

print("=== 单次普通语言模型响应 (没有工具) ===")
# 普通 LLM 本身无法获取实时天气
response_simple = llm.invoke("北京的天气怎么样？")
print("普通 LLM 回答:", response_simple.content)

print("\n=== Agent 的闭环执行 (有工具) ===")
# Agent 会根据规划，自主拆解并调用工具
response_agent = agent_executor.invoke({"messages": [("user", "北京的天气怎么样？")]})

# 打印出 Agent 思考和执行的过程中产生的所有消息
for message in response_agent["messages"]:
    message.pretty_print()
