import operator
from pathlib import Path
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
try:
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
except ImportError:
    JsonPlusSerializer = None
from sop_artifacts import (
    ContentOutline,
    DraftContent,
    ResearchMaterial,
    ResearchReport,
    ReviewFeedback,
)
from crew.product_manager import pm_node
from crew.researcher import researcher_node
from crew.writer import writer_node
from crew.reviewer import reviewer_node
from crew.summarizer import summarizer_node
from utils.logging_utils import configure_logging, get_logger, timed_block

configure_logging()
logger = get_logger(__name__)

# 定义状态扩展，方便 LangGraph 使用
class GraphState(TypedDict, total=False):
    topic: str
    outline: ContentOutline
    research_report: ResearchReport
    draft: DraftContent
    draft_history: Annotated[List[DraftContent], operator.add]  # 存储所有版本的 Draft
    latest_feedback: ReviewFeedback
    review_count: int
    history: Annotated[List[str], operator.add]
    history_summary: str  # 压缩后的历史摘要


PROJECT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = PROJECT_DIR / "reports"
MAX_REVIEW_COUNT = 3
CHECKPOINT_ALLOWED_TYPES = [
    ContentOutline,
    ResearchMaterial,
    ResearchReport,
    DraftContent,
    ReviewFeedback,
]

def router(state: GraphState):
    """根据评审反馈进行路由"""
    feedback = state.get("latest_feedback")

    # 达到最大评审次数，强制结束
    if state.get("review_count", 0) >= MAX_REVIEW_COUNT:
        print("!!! 达到最大评审次数，强制结束 !!!")
        logger.warning(
            "达到最大评审次数，强制结束: review_count=%d approved=%s",
            state.get("review_count", 0),
            getattr(feedback, "is_approved", None),
        )
        return "end"

    if not feedback or feedback.is_approved:
        logger.info(
            "路由结束: has_feedback=%s approved=%s",
            bool(feedback),
            getattr(feedback, "is_approved", None),
        )
        return "end"

    # 根据反馈指向特定角色
    if feedback.target_agent == "researcher":
        logger.info("路由到 Researcher: issues=%d", len(feedback.specific_issues))
        return "researcher"
    else:
        logger.info(
            "路由到 Writer: target_agent=%s issues=%d",
            feedback.target_agent,
            len(feedback.specific_issues),
        )
        return "writer"


def should_auto_resume_research_retry(snapshot) -> bool:
    """判断当前断点是否是评审后回到 Researcher 的自动返工断点。"""
    next_nodes = set(snapshot.next or [])
    if "researcher" not in next_nodes:
        return False

    feedback = snapshot.values.get("latest_feedback")
    return bool(feedback and not feedback.is_approved)


def resume_until_finished(app, config):
    """恢复 LangGraph，并自动跨过评审后回 Researcher 的内部返工断点。"""
    final_state = app.invoke(None, config=config)

    for auto_resume_count in range(1, MAX_REVIEW_COUNT + 1):
        snapshot = app.get_state(config)
        if not should_auto_resume_research_retry(snapshot):
            return final_state

        feedback = snapshot.values.get("latest_feedback")
        print("🔁 评审要求补充研究资料，自动恢复 Researcher 返工...")
        logger.info(
            "自动恢复 Researcher 返工断点: auto_resume_count=%d review_count=%d issues=%d",
            auto_resume_count,
            snapshot.values.get("review_count", 0),
            len(getattr(feedback, "specific_issues", [])),
        )
        final_state = app.invoke(None, config=config)

    logger.warning("自动恢复 Researcher 返工达到保护上限，返回当前状态")
    return final_state


def final_status_heading(is_approved: bool, review_count: int) -> str:
    """根据真实结束原因生成终端摘要标题。"""
    if is_approved:
        return "✅ 任务完成！最终状态摘要："
    if review_count >= MAX_REVIEW_COUNT:
        return "⚠️ 达到最大评审次数，报告未通过评审。最终状态摘要："
    return "⚠️ 报告未通过评审。最终状态摘要："


def create_checkpointer():
    """Create a checkpointer that explicitly allows project artifact types."""
    if JsonPlusSerializer is None:
        logger.info("JsonPlusSerializer 不可用，使用默认 MemorySaver")
        return MemorySaver()

    serde = JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_ALLOWED_TYPES)
    try:
        logger.info("创建 MemorySaver: 使用显式 msgpack allowlist")
        return MemorySaver(serde=serde)
    except TypeError:
        logger.info("MemorySaver 构造器不支持 serde 参数，回退为实例属性注入")
        memory = MemorySaver()
        memory.serde = serde
        return memory

def create_team_graph():
    """构建内容创作团队的 LangGraph"""
    logger.info("开始构建 LangGraph 内容团队工作流")
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
    with timed_block(logger, "创建 LangGraph checkpointer", slow_after=1.0):
        memory = create_checkpointer()

    # 编译图时设置断点：在研究员开始工作前（即 PM 规划大纲后）暂停
    with timed_block(logger, "编译 LangGraph 工作流", slow_after=2.0):
        app = workflow.compile(
            checkpointer=memory,
            interrupt_before=["researcher"]
        )
    logger.info("LangGraph 工作流构建完成: interrupt_before=researcher")
    return app

if __name__ == "__main__":
    logger.info("启动内容创作团队 CLI")
    with timed_block(logger, "初始化团队图", slow_after=2.0):
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
    with timed_block(logger, "首次 invoke：PM 到人工断点", slow_after=20.0):
        state = app.invoke(initial_state, config=config)
    
    # 检查是否因为断点停止
    with timed_block(logger, "读取 LangGraph 状态快照", slow_after=1.0):
        snapshot = app.get_state(config)
    if snapshot.next and "researcher" in snapshot.next:
        logger.info("流程进入人工审核断点: next=%s", snapshot.next)
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
        with timed_block(logger, "恢复 invoke：Researcher 到结束", slow_after=120.0):
            final_state = resume_until_finished(app, config)
    else:
        logger.info("流程未触发人工审核断点，直接使用首次 invoke 状态")
        final_state = state

    draft = final_state["draft"]
    latest_feedback = final_state.get("latest_feedback")
    is_approved = bool(getattr(latest_feedback, "is_approved", False))
    logger.info(
        "流程结束: title=%s word_count=%d citations=%d review_count=%d approved=%s",
        draft.title,
        draft.word_count,
        len(draft.citations),
        final_state["review_count"],
        is_approved,
    )
    print("\n" + "="*60)
    print(final_status_heading(is_approved, final_state["review_count"]))
    print(f"  标题     : {draft.title}")
    print(f"  字数     : {draft.word_count}")
    print(f"  引用来源 : {len(draft.citations)} 条")
    print(f"  评审次数 : {final_state['review_count']}")
    if latest_feedback and not is_approved:
        print("  未通过原因 :")
        for issue in latest_feedback.specific_issues[:5]:
            print(f"    - {issue}")
        for suggestion in latest_feedback.suggestions[:3]:
            print(f"    - 建议：{suggestion}")
    print(f"  流程历史 :")
    for step in final_state["history"]:
        print(f"    - {step}")
    print("="*60)

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    REPORTS_DIR.mkdir(exist_ok=True)
    report_prefix = "final_report" if is_approved else "rejected_report"
    citations_prefix = "citations" if is_approved else "rejected_citations"
    report_filename = REPORTS_DIR / f"{report_prefix}_{timestamp}.md"
    citations_filename = REPORTS_DIR / f"{citations_prefix}_{timestamp}.md"

    # 保存正文
    with timed_block(logger, f"保存最终报告: {report_filename.name}", slow_after=1.0):
        with report_filename.open("w", encoding="utf-8") as f:
            f.write(draft.content_markdown)
    print(f"📝 最终报告已保存至 {report_filename}")

    # 保存引用列表
    if draft.citations:
        with timed_block(logger, f"保存引用列表: {citations_filename.name}", slow_after=1.0):
            with citations_filename.open("w", encoding="utf-8") as f:
                f.write("# 参考来源\n\n")
                for i, url in enumerate(draft.citations, 1):
                    f.write(f"{i}. {url}\n")
        print(f"🔗 引用来源已保存至 {citations_filename}")
