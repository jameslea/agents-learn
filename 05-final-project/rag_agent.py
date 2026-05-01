import os
import sys
import logging
from enum import Enum
from pathlib import Path
from typing import List, TypedDict

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Langchain & Langgraph components
from langchain_core.embeddings import FakeEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
from langfuse.langchain import CallbackHandler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.llm_factory import build_llm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==========================================
# 0. 枚举定义 (工程化管理)
# ==========================================

class NodeName(str, Enum):
    """图节点名称枚举"""
    RETRIEVE = "retrieve_node"
    GRADE = "grade_documents_node"
    WEB_SEARCH = "web_search_node"
    GENERATE = "generate_node"

class SearchSignal(str, Enum):
    """搜索信号枚举"""
    YES = "yes"
    NO = "no"

class StateKey(str, Enum):
    """状态键名枚举：确保节点 return 字典时无硬编码字符串"""
    QUESTION = "question"
    GENERATION = "generation"
    WEB_SEARCH = "web_search"
    DOCUMENTS = "documents"

load_dotenv()

# 初始化 Langfuse 监控探针 (自动读取当前环境变量配置)
langfuse_handler = CallbackHandler()

# ==========================================
# 0. 准备基础设施 (模型与向量库)
# ==========================================
model_name = os.getenv("MODEL_NAME", "deepseek-v4-flash")

# 大脑：统一从工厂函数构建，兼容 DeepSeek V4 thinking 配置
llm = build_llm(model_name=model_name, temperature=0)

# 搜索引擎工具 (Tavily)
web_search_tool = TavilySearchResults(max_results=3)

# 向量数据库
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
embeddings = FakeEmbeddings(size=1536)

try:
    vectorstore = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
except Exception as e:
    logger.error(f"⚠️ Chroma DB 加载失败，请确保已经先运行过 data_ingestion.py ! 错误: {e}")
    retriever = None

# ==========================================
# 1. 定义核心状态图数据结构 (State)
# ==========================================
class GraphState(BaseModel):
    """
    状态模型：使用 Pydantic 提供类型校验与属性访问
    """
    question: str = ""          # 用户问题
    generation: str = ""        # 最终生成的答案
    web_search: SearchSignal = SearchSignal.NO  # 标记是否需要外部网络搜索
    documents: List[str] = Field(default_factory=list) # 文档切片内容

# ==========================================
# 2. 定义处理节点 (Nodes)
# ==========================================

def retrieve_node(state: GraphState):
    """
    Node 1: 从内部 Chroma 向量库检索相关文档
    """
    question = state.question
    logger.info(f"🔍 [Retrieve Node] 开始从本地向量库检索主题: {question}")
    
    if retriever:
        docs = retriever.invoke(question)
        docs_text = [d.page_content for d in docs] if docs else []
    else:
        # Fallback 容错处理
        docs_text = []

    logger.info(f"   找到 {len(docs_text)} 块本地文档")
    return {StateKey.DOCUMENTS: docs_text, StateKey.QUESTION: question}


def grade_documents_node(state: GraphState):
    """
    Node 2: 评估检索到的文档是否真的与用户提问相关
    """
    logger.info("⚖️ [Grade Node] 开始对检索到的所有文档片段进行相关性打分...")
    question = state.question
    documents = state.documents
    
    # 构造打分 Prompt
    system = """你是一个评估检索到的文档同用户问题相关性的评分员。 \n 
    如果文档包含了与该问题相关的主题词或语义，将其评定为 related。\n
    这不需要严格的标准，只要能沾边即可。\n
    你只能且必须输出一个纯单词，'yes' 或者是 'no'，来表明文档是否相关。"""
    
    grade_prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", "检索到的文档：\n\n {document} \n\n 用户提问：{question}"),
    ])
    
    retrieval_grader = grade_prompt | llm
    
    
    filtered_docs = []
    web_search = SearchSignal.NO
    
    # 如果 retrieve 阶段完全没查到数据（如 DB 忘了建），直接触发搜索！
    if not documents:
        logger.warning("🚨 [警报] 本地无资料，直接请求外网援助！")
        return {StateKey.DOCUMENTS: [], StateKey.QUESTION: question, StateKey.WEB_SEARCH: SearchSignal.YES}

    for doc in documents:
        score = retrieval_grader.invoke({"question": question, "document": doc})
        grade = score.content.strip().lower()
        
        if SearchSignal.YES in grade:
            logger.info("   [判断] 此片段相关！✅")
            filtered_docs.append(doc)
        else:
            logger.info("   [判断] 此片段不相关！❌")
            # 只要有一个不相关的，我们也可以安全地设置为触发 web search 或全部丢弃。
            # 这里按照 CRAG 逻辑：有一块垃圾资料，我们就去外网搜一点来补缺。
            web_search = SearchSignal.YES
            continue
            
    # 如果被洗光了，全都是垃圾
    if not filtered_docs:
        logger.warning("🚨 [警报] 本地文档质量过差全军覆没，需要请求外网援助！")
        web_search = SearchSignal.YES
        
    return {StateKey.DOCUMENTS: filtered_docs, StateKey.QUESTION: question, StateKey.WEB_SEARCH: web_search}


def web_search_node(state: GraphState):
    """
    Node 3: 调用搜索引擎执行外部搜索补救
    """
    logger.info("🌐 [Web Search Node] 开始调用搜索引擎执行外网检索...")
    question = state.question
    documents = list(state.documents) # 拷贝一份，避免原地修改风险
    
    try:
        # Tavily 接收纯文本查询
        docs = web_search_tool.invoke({"query": question})
        # 提取结果
        docs_text = [d["content"] for d in docs] if isinstance(docs, list) else [str(docs)]
        logger.info("   获取到最新外网资讯碎片。")
        documents.extend(docs_text)
    except Exception as e:
        logger.error(f"网络搜索请求失败：{e}")
        documents.append("【搜索引擎由于网络原因断开，这部分外部资料未能搜到】")
    
    return {StateKey.DOCUMENTS: documents}


def generate_node(state: GraphState):
    """
    Node 4: 拿着最终提纯的文档(不管是从本地还是外网来的)，生成完美回复
    """
    logger.info("✍️ [Generate Node] 发起最终润色与汇总生成...")
    question = state.question
    documents = state.documents
    
    # 常规的 RAG Prompt
    prompt = ChatPromptTemplate.from_template(
        "你是一名得力的知识库问答助手。请仅使用以下提供的【上下文片段】来回答问题。\n"
        "如果你无法从上下文中找到答案，就直接说你不知道，不要自己编撰。\n\n"
        "问题: {question}\n\n"
        "上下文片段: {context}\n\n"
        "你的回答:"
    )
    
    # 组合为一段巨大字符串
    context_str = "\n\n---\n\n".join(documents)
    
    # 标准 LCEL
    rag_chain = prompt | llm
    
    generation = rag_chain.invoke({"context": context_str, "question": question})
    
    return {
        StateKey.DOCUMENTS: documents, 
        StateKey.QUESTION: question, 
        StateKey.GENERATION: generation.content
    }

# ==========================================
# 3. 定义图的条件路由逻辑 (Conditional Edges)
# ==========================================

def decide_to_generate(state: GraphState):
    """
    通过 Grade Node 返回的状态标记，决定是生成报告，还是触发搜索补救
    """
    logger.info(f"🚦 [路由抉择] 检查 Grade 节点结论: 是否需要 Web Search？ -> {state.web_search}")
    
    if state.web_search == SearchSignal.YES:
        logger.info("   -> 决断：信息流失严重，流向 Web Search 节点打外部补丁 🌐")
        return NodeName.WEB_SEARCH
    else:
        logger.info("   -> 决断：内部资料充足且优质，直奔 Generate 节点 ✍️")
        return NodeName.GENERATE


# ==========================================
# 4. 组装 Graph (The Builder)
# ==========================================

workflow = StateGraph(GraphState)

workflow.add_node(NodeName.RETRIEVE.value, retrieve_node)
workflow.add_node(NodeName.GRADE.value, grade_documents_node)
workflow.add_node(NodeName.WEB_SEARCH.value, web_search_node)
workflow.add_node(NodeName.GENERATE.value, generate_node)

workflow.set_entry_point(NodeName.RETRIEVE.value)

workflow.add_edge(NodeName.RETRIEVE.value, NodeName.GRADE.value)

workflow.add_conditional_edges(
    NodeName.GRADE.value,
    decide_to_generate,
    {
        NodeName.WEB_SEARCH.value: NodeName.WEB_SEARCH.value,
        NodeName.GENERATE.value: NodeName.GENERATE.value
    }
)

workflow.add_edge(NodeName.WEB_SEARCH.value, NodeName.GENERATE.value)
workflow.add_edge(NodeName.GENERATE.value, END)

app = workflow.compile()


if __name__ == "__main__":
    logger.info("\n" + "="*20 + " Self-RAG 反思图架构 " + "="*20)
    print(app.get_graph().draw_ascii())
    logger.info("="*55)
    # --- 情景 1 ---
    logger.info("\n--- 情境 1: 提问属于知识库内的纯学术问题 ---")
    active_question = "LangGraph 主要是做什么的机制？"
    logger.info(f"🚀 发射普通提问: {active_question}")
    
    last_value = None
    # 使用 StateKey 驱动输入
    for output in app.stream({StateKey.QUESTION: active_question}, config={"callbacks": [langfuse_handler]}):
        for key, value in output.items():
            last_value = value
            
    logger.info("\n" + "="*15 + " 【知识库提取报告】 " + "="*15)
    logger.info(last_value.generation if last_value else "无生成结果")
    logger.info("="*48 + "\n")


    # --- 情景 2 ---
    logger.info("\n--- 情境 2: 提问属于外界实时 or 毫不相关新闻 ---")
    active_question_2 = "今天最热点的新闻大概是啥"
    logger.info(f"🚀 发射超纲提问: {active_question_2}")
    
    last_value = None
    # 重新构造 input，使用 StateKey 确保输入项名称严谨
    for output in app.stream({StateKey.QUESTION: active_question_2, StateKey.DOCUMENTS: []}, config={"callbacks": [langfuse_handler]}):
        for key, value in output.items():
            last_value = value

    logger.info("\n" + "="*15 + " 【全网搜索报告】 " + "="*15)
    logger.info(last_value.generation if last_value else "无生成结果")
    logger.info("="*48 + "\n")
