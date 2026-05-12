import operator
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from sop_artifacts import TeamState
from crew.product_manager import pm_node
from crew.researcher import researcher_node
from crew.writer import writer_node
from crew.reviewer import reviewer_node
from crew.summarizer import summarizer_node

# 定义状态扩展，方便 LangGraph 使用
class GraphState(TypedDict):
    topic: str
    outline: Annotated[object, "ContentOutline"]
    research_report: Annotated[object, "ResearchReport"]
    draft: Annotated[object, "DraftContent"]
    draft_history: Annotated[List[object], operator.add]  # 存储所有版本的 Draft
    latest_feedback: Annotated[object, "ReviewFeedback"]
    review_count: int
    history: Annotated[List[str], operator.add]
    history_summary: str  # 压缩后的历史摘要

def router(state: GraphState):
    """根据评审反馈进行路由"""
    feedback = state.get("latest_feedback")

    # 达到最大评审次数，强制结束
    if state.get("review_count", 0) >= 3:
        print("!!! 达到最大评审次数，强制发布 !!!")
        return "end"

    if not feedback or feedback.is_approved:
        return "end"

    # 根据反馈指向特定角色
    if feedback.target_agent == "researcher":
        return "researcher"
    else:
        return "writer"

def create_team_graph():
    """构建内容创作团队的 LangGraph"""
    workflow = StateGraph(GraphState)

    # 添加节点
    workflow.add_node("pm", pm_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("summarizer", summarizer_node)

    # 设置入口
    workflow.set_entry_point("pm")

    # 线性流程开始
    workflow.add_edge("pm", "researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", "reviewer")
    
    # 评审后先进行摘要压缩
    workflow.add_edge("reviewer", "summarizer")

    # 从摘要节点进行条件循环路由
    workflow.add_conditional_edges(
        "summarizer",
        router,
        {
            "researcher": "researcher",
            "writer": "writer",
            "end": END
        }
    )

    # 内存持久化，用于断点恢复
    memory = MemorySaver()

    # 编译图时设置断点：在研究员开始工作前（即 PM 规划大纲后）暂停
    return workflow.compile(
        checkpointer=memory,
        interrupt_before=["researcher"]
    )

if __name__ == "__main__":
    app = create_team_graph()
    config = {"configurable": {"thread_id": "report_001"}}
    
    initial_state = {
        "topic": "2026 年 AI Agent 在企业数字转型中的实际应用案例",
        "review_count": 0,
        "history": ["任务启动"],
        "history_summary": "",
        "draft_history": []
    }

    print("🚀 启动团队协作流程...")
    
    # 第一次尝试运行（会在 researcher 之前中断）
    state = app.invoke(initial_state, config=config)
    
    # 检查是否因为断点停止
    snapshot = app.get_state(config)
    if snapshot.next and "researcher" in snapshot.next:
        print("\n" + "!"*30)
        print("🛑 流程已中断：等待人类审核大纲")
        outline = snapshot.values.get("outline")
        if outline:
            print(f"大纲标题: {outline.title}")
            print(f"章节结构: {outline.sections}")
        
        # 简单的人工交互模拟
        user_input = input("\n请审核大纲。按回车键批准并继续，输入 'exit' 退出: ")
        if user_input.lower() == 'exit':
            print("任务已取消。")
            exit()
        
        print("✅ 人类已批准。正在恢复流程...\n")
        # 恢复运行（不需要传 initial_state，它会从断点恢复）
        final_state = app.invoke(None, config=config)
    else:
        final_state = state

    draft = final_state["draft"]
    print("\n" + "="*60)
    print("✅ 任务完成！最终状态摘要：")
    print(f"  标题     : {draft.title}")
    print(f"  字数     : {draft.word_count}")
    print(f"  引用来源 : {len(draft.citations)} 条")
    print(f"  评审次数 : {final_state['review_count']}")
    print(f"  流程历史 :")
    for step in final_state["history"]:
        print(f"    - {step}")
    print("="*60)

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"final_report_{timestamp}.md"
    citations_filename = f"citations_{timestamp}.md"

    # 保存正文
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(draft.content_markdown)
    print(f"📝 最终报告已保存至 {report_filename}")

    # 保存引用列表
    if draft.citations:
        with open(citations_filename, "w", encoding="utf-8") as f:
            f.write("# 参考来源\n\n")
            for i, url in enumerate(draft.citations, 1):
                f.write(f"{i}. {url}\n")
        print(f"🔗 引用来源已保存至 {citations_filename}")
