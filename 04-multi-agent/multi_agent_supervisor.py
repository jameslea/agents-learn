import os
import sys
import operator
import logging
from enum import Enum
from pathlib import Path
from typing import Annotated, List, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain.agents import create_agent         # ✅ 使用 LangChain v1 推荐的 create_agent
from langgraph.graph import StateGraph, END

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.llm_factory import build_llm

# ==========================================
# 0. 配置日志
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

# ==========================================
# 1. 定义状态与工具
# ==========================================

class Role(str, Enum):
    RESEARCHER = "Researcher"
    ANALYST = "Analyst"
    SUPERVISOR = "Supervisor"

class RouteOption(str, Enum):
    FINISH = "FINISH"

class AgentState(TypedDict):
    # 所有消息的历史记录，使用 operator.add 聚合
    messages: Annotated[List[BaseMessage], operator.add]
    # 下一个执行该任务的角色
    next: str
    # 上一个执行过的角色（用于代码层强制干预、防止死循环）
    last_speaker: str

# 准备 Wikipedia 工具
api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=1000)
wikipedia_tool = WikipediaQueryRun(api_wrapper=api_wrapper)

# ==========================================
# 2. 初始化大模型
# ==========================================

llm = build_llm(
    model_name=os.getenv("MODEL_NAME", "deepseek-v4-flash"),
    temperature=0,
)

# ==========================================
# 3. 定义各角色 Agent
# ==========================================

# 研究员：使用 create_agent 处理工具调用循环（fetch Wikipedia 并自主决定是否继续搜索）
researcher_agent = create_agent(
    model=llm,
    tools=[wikipedia_tool],
    system_prompt="你是一名专业的研究员。你的任务是利用 Wikipedia 搜集事实性信息。请确保信息准确且相关。"
)

# 分析师：不需要工具，直接用核心 LCEL 链
analyst_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名高级数据分析师。你的任务是分析研究员提供的信息，寻找规律，进行对比，并总结出深刻的见解。"),
    MessagesPlaceholder(variable_name="messages"),
])
analyst_agent = analyst_prompt | llm

# ==========================================
# 4. Supervisor (调度枢纽) 核心逻辑
# ==========================================

# Supervisor 的路由指令
# 关键：明确的终止条件是解决 Supervisor 陷入死循环的核心手段
supervisor_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "你是一支研究团队的主管。你的任务是协调团队完成任务。\n"
     "团队成员：\n"
     "- Researcher：负责查资料、收集事实信息\n"
     "- Analyst：负责深度分析、总结归纳\n\n"
     "工作规则：\n"
     "1. 每项任务的标准流程是：Researcher 搜集信息 → Analyst 总结分析 → FINISH\n"
     "2. 一旦 Analyst 已经输出了分析总结，任务即视为完成，你必须输出 FINISH\n"
     "3. 不要重复派遣同一个角色连续执行超过一次\n\n"
     "请在回复的最后一行只输出下一个执行者的名字（Researcher、Analyst 或 FINISH），不要带任何标点。"),
    MessagesPlaceholder(variable_name="messages"),
])

supervisor_chain = supervisor_prompt | llm

# ==========================================
# 5. 定义 Graph 节点函数
# ==========================================

def researcher_node(state: AgentState):
    logger.info("🔍 [Researcher] 正在搜集资料...")
    result = researcher_agent.invoke(state)
    # 取最后一条消息，并打上 name 标签供 Supervisor 识别来源
    msg = result["messages"][-1]
    msg.name = Role.RESEARCHER
    return {"messages": [msg], "last_speaker": Role.RESEARCHER}

def analyst_node(state: AgentState):
    logger.info("📊 [Analyst] 正在分析总结...")
    result = analyst_agent.invoke(state)
    # LCEL 链返回的是 AIMessage 对象。打上 name 标签供 Supervisor 识别来源
    result.name = Role.ANALYST
    return {"messages": [result], "last_speaker": Role.ANALYST}

def supervisor_node(state: AgentState):
    logger.info("👔 [Supervisor] 正在规划下一步...")
    response = supervisor_chain.invoke(state)
    # 取最后一行提取关键字，兼容模型在正文中描述原因的情况
    last_line = response.content.strip().split("\n")[-1]

    if Role.RESEARCHER in last_line:
        next_node = Role.RESEARCHER
    elif Role.ANALYST in last_line:
        next_node = Role.ANALYST
    else:
        next_node = RouteOption.FINISH

    # [代码层强制防护] 如果 LLM 尝试派遣刚执行过的同一个角色，强制转为 FINISH
    # 这是最可靠的方式，不依赖 Prompt 指令题
    last_speaker = state.get("last_speaker", "")
    if next_node == last_speaker and next_node != RouteOption.FINISH:
        logger.warning(
            f"⚠️  [Supervisor] 检测到死循环风险！"
            f"LLM 要求再次派遣 {next_node}（刚刚出场过）。"
            f"强制终止。"
        )
        next_node = RouteOption.FINISH

    logger.info(f"👔 [Supervisor] 决定下一步: {next_node}")
    return {"next": next_node}

# ==========================================
# 6. 组装 Graph
# ==========================================

workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node(Role.RESEARCHER, researcher_node)
workflow.add_node(Role.ANALYST, analyst_node)
workflow.add_node(Role.SUPERVISOR, supervisor_node)

# 成员节点完成后，总是回到 Supervisor 汇报
workflow.add_edge(Role.RESEARCHER, Role.SUPERVISOR)
workflow.add_edge(Role.ANALYST, Role.SUPERVISOR)

# Supervisor 根据 state["next"] 决定分发到哪里
workflow.add_conditional_edges(
    Role.SUPERVISOR,
    lambda x: x["next"],
    {
        Role.RESEARCHER: Role.RESEARCHER,
        Role.ANALYST: Role.ANALYST,
        RouteOption.FINISH: END
    }
)

# 设置入口
workflow.set_entry_point(Role.SUPERVISOR)

graph = workflow.compile()

# ==========================================
# 7. 运行验证
# ==========================================

if __name__ == "__main__":
    print("\n========== 多 Agent 协作网络状态机拓扑 ==========")
    print(graph.get_graph().draw_ascii())
    print("==============================================\n")

    task_input = "简单研究一下 DeepSeek 并在 50 字内总结。"

    inputs = {"messages": [HumanMessage(content=task_input)], "last_speaker": ""}

    logger.info(f"🚀 任务开始: {task_input}")

    last_content_msg = ""
    for output in graph.stream(inputs, {"recursion_limit": 20}):
        if "__end__" not in output:
            key = next(iter(output))
            logger.info(f"-> 进入节点: {key}")

            # 持续记录每个节点产生的最新文本内容，用于最终报告
            node_output = output[key]
            if isinstance(node_output, dict) and "messages" in node_output:
                msgs = node_output["messages"]
                if msgs and hasattr(msgs[-1], "content") and msgs[-1].content:
                    last_content_msg = msgs[-1].content

    print("\n========= 【任务最终报告】 =========")
    if last_content_msg:
        print(last_content_msg)
    else:
        print("任务已完成，但未提取到详细报告内容。")
    print("====================================")
