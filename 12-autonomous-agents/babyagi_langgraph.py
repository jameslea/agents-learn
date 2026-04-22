import os
import json
import operator
from typing import List, Dict, TypedDict, Annotated
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END

# --- 1. 数据模型与状态定义 ---
class Task(BaseModel):
    id: int = Field(description="任务唯一标识符")
    name: str = Field(description="任务名称或简短描述")
    description: str = Field(description="任务的具体执行指令")

class TaskList(BaseModel):
    tasks: List[Task] = Field(description="任务列表")

# 定义图的状态 (State)
class AgentState(TypedDict):
    goal: str
    todo_tasks: List[Task]
    # operator.add 表示后续节点返回 completed_tasks 时，将与原列表进行追加合并
    completed_tasks: Annotated[List[Dict], operator.add] 
    iteration: int
    max_iterations: int

# --- 2. 节点与边逻辑 ---
load_dotenv()
model_name = os.getenv("MODEL_NAME", "deepseek-chat")
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_BASE_URL")

llm = ChatOpenAI(
    model=model_name,
    openai_api_key=api_key,
    openai_api_base=api_base,
    temperature=0.2
)

def init_tasks_node(state: AgentState) -> dict:
    """初始化节点：根据目标生成初始任务队列"""
    print(f"\n[Node: Init] 正在为目标生成初始任务: {state['goal']}")
    parser = PydanticOutputParser(pydantic_object=TaskList)
    prompt = ChatPromptTemplate.from_template(
        "你是一个任务规划专家。用户目标是：{goal}\n"
        "请将该目标拆解为 2-3 个初始的关键步骤任务。\n"
        "{format_instructions}"
    )
    chain = prompt | llm | parser
    result = chain.invoke({
        "goal": state["goal"],
        "format_instructions": parser.get_format_instructions()
    })
    
    for t in result.tasks:
        print(f"  - [{t.id}] {t.name}")
        
    return {"todo_tasks": result.tasks, "completed_tasks": [], "iteration": 0}

def execute_node(state: AgentState) -> dict:
    """执行节点：从队列取出一个任务并执行"""
    if not state["todo_tasks"]:
        return {}
        
    task = state["todo_tasks"][0]
    print(f"\n[Node: Execute] >>> 正在执行任务 #{task.id}: {task.name}")
    
    prompt = ChatPromptTemplate.from_template(
        "你是一个执行者。你的目标是：{goal}\n"
        "当前任务名称：{task_name}\n"
        "任务详细描述：{task_description}\n"
        "请执行该任务并给出详细结果。"
    )
    chain = prompt | llm
    result = chain.invoke({
        "goal": state["goal"],
        "task_name": task.name,
        "task_description": task.description
    })
    
    execution_result = result.content
    print(f"--- 执行结果 ---\n{execution_result[:100]}...\n")
    
    completed_task = {
        "task": task.dict(),
        "result": execution_result
    }
    
    new_iteration = state.get("iteration", 0) + 1
    
    # 状态更新：
    # 1. todo_tasks 移除已执行的任务
    # 2. completed_tasks 增量追加
    # 3. iteration 递增
    return {
        "todo_tasks": state["todo_tasks"][1:], 
        "completed_tasks": [completed_task],
        "iteration": new_iteration
    }

def reflect_update_node(state: AgentState) -> dict:
    """反思更新节点：根据执行结果调整后续队列"""
    print("\n[Node: Reflect & Update] 正在根据执行结果分析后续任务...")
    
    if not state["completed_tasks"]:
        return {}
        
    last_completed = state["completed_tasks"][-1]
    
    parser = PydanticOutputParser(pydantic_object=TaskList)
    prompt = ChatPromptTemplate.from_template(
        "你是一个任务管理专家。用户目标是：{goal}\n"
        "当前剩余待办任务：{current_tasks}\n"
        "上一个任务的执行结果：{last_result}\n\n"
        "请判断是否需要增加新任务。如果目标已接近达成，只需返回原剩余待办任务。\n"
        "返回更新后的完整待办任务列表。\n"
        "{format_instructions}"
    )
    
    current_tasks_str = json.dumps([t.dict() for t in state["todo_tasks"]], ensure_ascii=False)
    
    chain = prompt | llm | parser
    result = chain.invoke({
        "goal": state["goal"],
        "current_tasks": current_tasks_str,
        "last_result": last_completed["result"],
        "format_instructions": parser.get_format_instructions()
    })
    
    print("[队列更新后]")
    for t in result.tasks:
        print(f"  - [{t.id}] {t.name}")
        
    return {"todo_tasks": result.tasks}

def should_continue(state: AgentState) -> str:
    """条件路由：判断是否继续执行循环"""
    print(f"\n[Router] 检查循环条件... (当前迭代: {state['iteration']} / {state['max_iterations']})")
    if not state["todo_tasks"]:
        print("-> 待办任务为空，目标完成，结束循环。")
        return "end"
    if state["iteration"] >= state["max_iterations"]:
        print("-> 达到最大迭代次数，强制结束。")
        return "end"
    print("-> 还有任务待执行，进入下一个循环。")
    return "continue"

# --- 3. 构建图结构 (State Machine) ---
def build_and_run(goal: str):
    workflow = StateGraph(AgentState)
    
    # 1. 注册图节点
    workflow.add_node("init_tasks", init_tasks_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("reflect_update", reflect_update_node)
    
    # 2. 注册普通边 (明确的调用顺序)
    workflow.set_entry_point("init_tasks")
    workflow.add_edge("init_tasks", "execute")
    workflow.add_edge("execute", "reflect_update")
    
    # 3. 注册条件边 (控制循环和退出逻辑)
    workflow.add_conditional_edges(
        "reflect_update",
        should_continue,
        {
            "continue": "execute",
            "end": END
        }
    )
    
    # 4. 编译并运行图
    app = workflow.compile()
    
    initial_state = {
        "goal": goal,
        "todo_tasks": [],
        "completed_tasks": [],
        "iteration": 0,
        "max_iterations": 3 # 演示用，限制 3 次迭代
    }
    
    print(f"========== 启动 BabyAGI 任务循环 (LangGraph 工业级实现) ==========")
    # 触发状态机运行
    app.invoke(initial_state)
    print("========== 任务循环结束 ==========")

if __name__ == "__main__":
    my_goal = os.getenv("AUTONOMOUS_GOAL", "调研 2024 年最流行的 3 个大语言模型框架，并对比它们的优缺点。")
    build_and_run(goal=my_goal)
