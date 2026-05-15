import os
import logging
import sqlite3
from typing import TypedDict, Annotated, List
import operator

import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from task_queue import ResearchState, TaskStatus, ResearchTask
from task_generator import TaskGenerator
from task_executor import TaskExecutor
from reflector import Reflector
from cost_tracker import TokenBudgetTracker, estimate_tokens
import logging

# 忽略 LangGraph 的反序列化警告
logging.getLogger("langgraph.checkpoint.serde.jsonplus").setLevel(logging.ERROR)

logger = logging.getLogger("research_graph")

# 定义严格类型的图状态，解决字典覆盖丢失字段的问题
class GraphState(TypedDict):
    original_goal: str
    tasks: list
    completed_steps: int
    max_steps: int
    context_memory: str
    final_report: str

# 1. 实例化各个组件
budget = TokenBudgetTracker(max_tokens=100000) # 将预算设置为10万
generator = TaskGenerator()
executor = TaskExecutor()
reflector = Reflector()

# 2. 定义节点函数
def node_generate_plan(state: GraphState) -> dict:
    """初始化节点：从宏大目标生成初始任务"""
    logger.info("===" * 10)
    logger.info("📌 进入节点: Generate Plan")
    
    goal = state.get("original_goal", "")
    tasks = state.get("tasks", [])
    
    if not tasks:
        # 只在没有任务时生成
        new_tasks = generator.generate_initial_tasks(goal)
        budget.add_usage(estimate_tokens(goal), estimate_tokens(str(new_tasks)))
        return {"tasks": new_tasks}
    return {}

def node_execute_and_reflect(state: GraphState) -> dict:
    """
    核心循环节点：领取任务 -> 执行搜索 -> 反思结果 -> 更新状态
    为了简化 Graph 结构，将执行和反思合并到一个节点中。
    """
    logger.info("===" * 10)
    logger.info("📌 进入节点: Execute & Reflect")
    
    # 将字典转换为 Pydantic 对象以使用我们定义的方法
    # 注意：LangGraph 传递的 state 始终是字典（如果使用了 Pydantic 模型，它内部会被转为 dict）
    # 但由于我们在前面用 dict 接收，所以这里手动还原一下以使用方法。
    r_state = ResearchState(**state)
    
    current_task = r_state.get_next_task()
    
    if not current_task:
        logger.info("📭 没有待处理的子任务了。")
        return {"completed_steps": r_state.completed_steps + 1}
        
    logger.info(f"▶️ 开始执行任务: {current_task.description}")
    
    # 1. 执行搜索
    raw_data = executor.search(current_task.description)
    
    # 2. 反思提炼
    reflection = reflector.reflect(r_state.original_goal, current_task.description, raw_data)
    budget.add_usage(estimate_tokens(raw_data), estimate_tokens(str(reflection)))
    
    # 3. 更新状态
    # 更新当前任务状态
    new_tasks_list = []
    for t in r_state.tasks:
        if t.id == current_task.id:
            t.status = TaskStatus.COMPLETED
            t.result = reflection.summary if reflection.is_useful else "无用信息被丢弃"
        new_tasks_list.append(t)
        
    # 提前终止机制：审核员认为目标已达成
    if getattr(reflection, "is_goal_achieved", False):
        logger.info("🎉 质量审核员评估：终极目标已完全达成，提前终止后续调研！")
        for t in new_tasks_list:
            if t.status == TaskStatus.TODO:
                t.status = TaskStatus.COMPLETED
                t.result = "目标已提前达成，此后续任务被自动跳过"
        # 强行置空新任务，防止衍生
        reflection.new_tasks = []

    # 坑 C6/C2 解决：防止无止境地衍生新任务导致无限循环
    # 如果已经非常接近最大步数，强制停止接收新任务，开始收尾
    if reflection.new_tasks:
        if r_state.completed_steps >= r_state.max_steps - 2:
            logger.warning("⚠️ 已接近最大步数限制，为了确保成功收尾，拒绝衍生新任务。")
        else:
            for nt in reflection.new_tasks:
                # 简单降级优先级，防止一直深度优先无限循环
                nt.priority += 1 
                new_tasks_list.append(nt)
            
    # 更新全局上下文 (防超载：只追加有用的 summary)
    new_context = r_state.context_memory
    if reflection.is_useful:
        new_context += f"\n- {reflection.summary}"
        
    return {
        "tasks": new_tasks_list,
        "context_memory": new_context,
        "completed_steps": r_state.completed_steps + 1
    }

def node_generate_report(state: GraphState) -> dict:
    """收尾节点：根据收集到的全局上下文，生成最终报告"""
    logger.info("===" * 10)
    logger.info("📌 进入节点: Generate Report")
    
    goal = state.get("original_goal", "")
    context = state.get("context_memory", "未搜集到任何有用信息。")
    
    logger.info("📝 正在撰写最终报告...")
    
    from langchain_core.prompts import ChatPromptTemplate
    from common.llm_factory import build_llm
    
    llm = build_llm()
    
    prompt = ChatPromptTemplate.from_template("""
你是一位首席行业分析师。
你的研究目标是：{goal}

以下是你团队经过长期调研收集到的压缩知识碎片：
{context}

请基于上述素材，撰写一份结构清晰、专业严谨的深度研究报告。
如果素材中存在冲突，请指出；如果素材信息不足，请客观说明。
""")
    
    result = llm.invoke(prompt.format(goal=goal, context=context))
    budget.add_usage(estimate_tokens(context), estimate_tokens(result.content))
    
    return {"final_report": result.content}

# 3. 定义条件边 (决定是继续循环还是结束)
def should_continue(state: GraphState) -> str:
    r_state = ResearchState(**state)
    
    # 坑 C2 解决：超限强制终止
    if r_state.completed_steps >= r_state.max_steps:
        logger.warning(f"🛑 达到最大步数 ({r_state.max_steps})，强制终止循环！")
        return "generate_report"
        
    # 如果还有 TODO 的任务，继续执行
    if r_state.get_next_task() is not None:
        return "execute_and_reflect"
        
    # 任务全部完成，收尾
    logger.info("🏁 所有子任务已完成，准备生成报告。")
    return "generate_report"

# 4. 构建 LangGraph 状态图
# 注意：在 LangGraph 中，状态 (State) 是在节点之间流转的数据血液。
# 这里我们直接使用内置的 `dict` 类型作为 State，
# 这意味着当节点返回新字典时，LangGraph 默认会使用 dict.update() 行为覆盖或新增键值对。
def build_graph(memory=None):
    # 初始化状态图，指定状态类型为 GraphState
    workflow = StateGraph(GraphState)
    
    # 步骤 A：注册图节点 (Nodes)
    # 节点是执行具体工作的实体，它们接收 State，执行逻辑，返回 Update。
    workflow.add_node("generate_plan", node_generate_plan)           # Planner
    workflow.add_node("execute_and_reflect", node_execute_and_reflect) # Executor & Reflector
    workflow.add_node("generate_report", node_generate_report)       # 最终报告生成
    
    # 步骤 B：设置入口点 (Entry Point)
    # 图的执行起点。
    workflow.set_entry_point("generate_plan")
    
    # 步骤 C：定义边 (Edges) 和 条件边 (Conditional Edges)
    # 边决定了控制流的走向。
    
    # 1. 普通边：计划生成后，无条件进入执行反思节点
    workflow.add_edge("generate_plan", "execute_and_reflect")
    
    # 2. 条件边：这是实现“循环 (Loop)”的关键。
    # 执行完一个任务后，调用 should_continue 检查状态：
    # 如果还需要继续，就回到 execute_and_reflect (循环)；如果完成了，就走到 generate_report。
    workflow.add_conditional_edges(
        "execute_and_reflect",
        should_continue,
        {
            "execute_and_reflect": "execute_and_reflect",
            "generate_report": "generate_report"
        }
    )
    
    # 3. 终点边：生成报告后，图执行结束
    workflow.add_edge("generate_report", END)
    
    # 编译图，注入记忆体
    return workflow.compile(checkpointer=memory)


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )
    
    # 初始化状态
    initial_state = ResearchState(
        original_goal="调研 2026 年最具潜力的高级 AI Agent 架构，重点对比多智能体与单一复杂状态机",
        max_steps=10 # 提高步数上限，给智能体足够的空间去执行衍生任务
    ).model_dump()
    
    # 坑 C5 解决：引入 SqliteSaver 实现持久化断点续传
    # Checkpointer 会在每次节点执行完后，自动把 State 保存到数据库中。
    db_path = os.path.join(os.path.dirname(__file__), "research_checkpoints.sqlite")
    
    logger.info("🚀 启动自主调研循环...\n")
    try:
        # SqliteSaver.from_conn_string 是一个上下文管理器
        with SqliteSaver.from_conn_string(db_path) as memory:
            graph = build_graph(memory)
            
            # 从命令行参数获取 thread_id，如果没有提供则默认使用 research_demo_01
            thread_id = sys.argv[1] if len(sys.argv) > 1 else "research_demo_01"
            
            # 配置 thread_id，这是 checkpoint 区分不同任务的关键
            config = {"configurable": {"thread_id": thread_id}}
            logger.info(f"🔑 当前任务 Thread ID: {thread_id}")
            
            # 检查是否有历史存档 (断点检测)
            current_state = graph.get_state(config)
            if current_state and current_state.values:
                logger.info(f"💾 检测到历史存档点 (步骤 {current_state.values.get('completed_steps', 0)})，自动从中断处恢复执行...")
                # 坑 C5 解决：传入 None 触发断点续传
                final_state = graph.invoke(None, config)
            else:
                logger.info("🆕 未检测到存档，开启全新的调研任务...")
                # 传入 initial_state 从头开始
                final_state = graph.invoke(initial_state, config)
            
            print("\n\n" + "="*50)
            print("🎉 最终研究报告已生成 🎉")
            print("="*50)
            report_content = final_state.get("final_report", "未生成报告")
            
            # 将报告保存到文件
            report_path = os.path.join(os.path.dirname(__file__), "final_research_report.md")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            logger.info(f"📄 报告内容已静默保存至: {report_path}")
            
            # 打印财务报表
            budget.report()
            
    except Exception as e:
        logger.error(f"❌ 运行过程中断: {e}")
