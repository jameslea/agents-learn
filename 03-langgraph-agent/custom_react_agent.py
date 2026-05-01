import os
import sys
import time
import logging
import operator
from enum import Enum
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv

# ==========================================
# 0. 配置标准日志模块 (带时间戳输出)
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.llm_factory import build_llm

# ==========================================
# 0.5 架构防腐层：消除魔法字符串的核心常量池
# ==========================================
class NodeName(str, Enum):
    AGENT = "agent"
    TOOLS = "tools"

class RouteCondition(str, Enum):
    CONTINUE = "continue"
    END = "end"


# 1. 明确定义我们的“账单”（全局 State）数据结构
class AgentState(TypedDict):
    # Annotated + operator.add 的组合告诉 LangGraph：
    # "当有新的列表送过来时，别去覆盖掉旧记录，而是拼接到原列表的末尾"
    messages: Annotated[list[BaseMessage], operator.add]

# 2. 准备工具体系和接入大脑
@tool
def get_current_weather(location: str) -> str:
    """获取指定城市的天气"""
    # 模拟外部API真实请求过程
    return f"{location} 今天气温突降，温度是 8°C"

tools = [get_current_weather]
model_name = os.getenv("MODEL_NAME", "deepseek-v4-flash")

# 【重点】我们剥离了造好的大礼包，必须手动给大模型挂上兵器库声明
llm = build_llm(model_name=model_name, temperature=0).bind_tools(tools)

# 3. 定义三大核心车间与调度枢纽（Nodes 与 Conditional Edge）

# 节点A：推理中枢节点
def agent_node(state: AgentState):
    """仅仅负责读取历史账本，驱动大模型深度推理一次"""
    logger.info("➤ [节点开始] 进入推理中枢 (agent_node) ...")
    start_t = time.time()
    
    response = llm.invoke(state["messages"])
    
    cost_t = time.time() - start_t
    logger.info(f"✔ [节点完成] 推理中枢执行完毕 (大模型共耗时: {cost_t:.2f}s)")
    # 只返回这一个阶段产生的新包裹内容，框架会自动把它拼接进系统长河
    return {"messages": [response]}

# 节点B：物理执行节点 (借用 LangGraph 原生写好的工具皮套 ToolNode)
tool_node = ToolNode(tools)

# 调度器枢纽：条件路由判断哨函数
def should_continue(state: AgentState) -> str:
    """
    检查大模型刚产出的最新回包。
    用它来决定流水线下一站该流向【物理执行】还是【结束站】。
    """
    last_message = state["messages"][-1]
    
    # 如果判断出模型带有明确的函数意图：
    if last_message.tool_calls:
        logger.info(f"🚦 [海关路由] 侦测到工具调用意图 ({last_message.tool_calls[0]['name']}) -> 导向 tools 节点")
        return RouteCondition.CONTINUE
    else:
        logger.info("🚦 [海关路由] 任务收尾，未检测到工具任务 -> 导向 END 节点退出")
        return RouteCondition.END


# 4. 在图纸上用打钉子连线组装架构蓝图 (StateGraph 组装)
builder = StateGraph(AgentState)

# 把咱们手敲的两大车间固定在图板上
builder.add_node(NodeName.AGENT, agent_node)
builder.add_node(NodeName.TOOLS, tool_node)

# 设置整个流转生命周期的唯一始发站口
builder.set_entry_point(NodeName.AGENT) 

# 把上面定义的海关调度规则（条件变差）配置在主模型节点之后
builder.add_conditional_edges(
    NodeName.AGENT,  # 起点车间
    should_continue, # 作为路由守卫判断的Python函数
    {
        # 以下规定字典：如果守卫函数返回对应的枚举字符串，引擎该指向哪一列！
        RouteCondition.CONTINUE: NodeName.TOOLS,  # 流向工具执行点
        RouteCondition.END: END                   # 流向系统原生停机节点
    }
)

# 当工具执行节点强力计算完毕后，强行要求把执行结果单向发回给大模型做推理复盘
builder.add_edge(NodeName.TOOLS, NodeName.AGENT)

# 5. 【点睛之笔】大引擎蓝图冻结与静态编译！
graph = builder.compile()

if __name__ == "__main__":
    # 为了直观感受到这一步脱胎换骨的改变，我们把图的链路打印成字符画结构观察
    print("\n========== 你徒手搭建的网络状态机拓扑结构 ==========")
    print(graph.get_graph().draw_ascii())
    print("==================================================\n")
    
    # 注入一个空荡荡干净透明的首发事件
    initial_state = {"messages": [HumanMessage(content="北京最近天气怎么样？出行需要带毛衣吗？")]}
    
    logger.info("▶️ 开始触发流水线运转...")
    global_start_t = time.time()
    
    # 用 .stream 以每次图流转事件为粒度持续捕获产出节点
    for event in graph.stream(initial_state):
        # 记录每个流传抛出点，为保持日志清爽，我们只在各节点内部详细追踪，此处被动接受事件。
        pass
            
    global_cost = time.time() - global_start_t
    logger.info(f"🎉 全局流转正式休眠完毕！任务总耗时: {global_cost:.2f}s\n")
    
    print("========= 【最终解答内容】 =========")
    # 取出事件链里的最后一个节点产生的 message 内容
    final_output = next(iter(event.values()))["messages"][-1].content
    print(final_output)
