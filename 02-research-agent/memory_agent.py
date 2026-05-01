import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
# 引入 LangGraph 最核心的内存检查点机制
from langgraph.checkpoint.memory import MemorySaver

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.llm_factory import build_llm

# 1. 准备基础模型
model_name = os.getenv("MODEL_NAME", "deepseek-v4-flash")
llm = build_llm(model_name=model_name, temperature=0.7)

# 准备一个简单的工具，演示附带上下文时的调用
@tool
def check_user_balance(username: str) -> str:
    """查询指定用户的账户余额。提示：用户自称的名字（如zhao）即为这里的 username。"""
    balances = {"zhao": "1000 元", "admin": "99999 元"}
    return balances.get(username, "找不到该用户或余额为 0")

tools = [check_user_balance]

# ==========================================
# 2. 核心：初始化持久化内存 (Memory)
# ==========================================

# MemorySaver 相当于一个暂存在运行内存里的“记事本”
# 在真正的企业级生产环境里，这里只需直接替换成 PostgresSaver 或 SqliteSaver 即可自动写入数据库保存
memory = MemorySaver()

# 创建带有 Checkpointer 记忆机制的 Agent
agent_executor = create_react_agent(
    llm, 
    tools,
    checkpointer=memory  # 最核心的区别：注入了记忆外挂！
)

if __name__ == "__main__":
    print("🧠 拥有长期跨轮次记忆的 Agent 已启动！\n")

    # ==========================================
    # 3. 会话配置 (Thread) 机制
    # ==========================================
    # thread_id: "会话ID"（好比你在微信里点开的一个特定的聊天框）。
    # 只要这把钥匙不换，Agent 就会去 memory 记事本里抽出对应的历史剧本。
    
    my_session = {"configurable": {"thread_id": "chat_room_zhao"}}

    print("=== 第一轮：交代背景并执行任务 ===")
    query1 = "你好，我是 zhao，你帮我查查我的余额，然后一定要死死记住我的名字啊！"
    print(f"👦 你: {query1}")
    
    # 划重点：invoke 时除了传话，还要把会话钥匙 config 传进去
    res1 = agent_executor.invoke({"messages": [("user", query1)]}, config=my_session)
    print(f"🤖 AI: {res1['messages'][-1].content}\n")

    print("=== 第二轮：考验“跨轮次记忆”能力 ===")
    query2 = "我刚才说我叫啥来着？我的这点余额，去买一部 5000 块钱的手机够不够？"
    print(f"👦 你: {query2}")
    
    res2 = agent_executor.invoke({"messages": [("user", query2)]}, config=my_session)
    print(f"🤖 AI: {res2['messages'][-1].content}\n")


    print("=== 第三轮：多实例状态隔离测试 ===")
    # 模拟服务器上接入了另一个新用户，开启了一个全新的聊天线程
    stranger_session = {"configurable": {"thread_id": uuid.uuid4().hex}}
    
    query3 = "你好，初次见面，你还记得我是谁以及我的余额吗？"
    print(f"👦 陌生人: {query3}")
    
    res3 = agent_executor.invoke({"messages": [("user", query3)]}, config=stranger_session)
    print(f"🤖 AI: {res3['messages'][-1].content}\n")
