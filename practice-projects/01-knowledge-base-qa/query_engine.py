import time
import logging
import sys

# 立即配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger("query_engine")

logger.info("正在启动 [查询引擎]，准备加载系统模块...")
start_import_time = time.time()

import os
import chromadb
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
from dotenv import load_dotenv

# 计算导入耗时
import_duration = time.time() - start_import_time
logger.info(f"[查询引擎] 模块加载完成，耗时: {import_duration:.2f} 秒")

"""
主要第三方库组件说明：
- chromadb: 向量数据库客户端，用于连接和操作持久化的向量数据。
- VectorStoreIndex: 从向量存储中加载数据并构建可查询索引。
- StorageContext: 存储配置上下文。
- Settings: 全局模型配置（LLM 和 Embedding）。
- ChromaVectorStore: 连接 LlamaIndex 与 ChromaDB 的适配器。
- HuggingFaceEmbedding: 本地向量化模型封装。
- OpenAILike: 兼容 OpenAI 协议的 LLM 接口。
"""

# 加载环境变量
load_dotenv()

# 向量数据库持久化路径 (需与 ingestion.py 保持一致)
CHROMA_DB_PATH = "./practice-projects/01-knowledge-base-qa/chroma_db"

def setup_settings():
    """
    配置全局模型设置。
    检索时必须使用与索引构建时相同的 Embedding 模型，否则无法正确计算相似度。
    """
    # 避免重复初始化
    if Settings.callback_manager and Settings.callback_manager.handlers:
        for handler in Settings.callback_manager.handlers:
            if isinstance(handler, LlamaDebugHandler):
                return handler

    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    Settings.llm = OpenAILike(
        model=os.getenv("MODEL_NAME", "deepseek-v4-flash"),
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        is_chat_model=True
    )
    
    # 添加可观测性组件：用于记录各环节耗时
    llama_debug = LlamaDebugHandler(print_trace_on_end=False)
    Settings.callback_manager = CallbackManager([llama_debug])
    return llama_debug

from reranker import get_reranker

def get_query_engine():
    """
    加载持久化的索引并创建查询引擎。
    """
    setup_settings()
    
    # 1. 连接到本地 ChromaDB 数据库
    db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    chroma_collection = db.get_or_create_collection("kb_qa_collection")
    
    # 2. 包装为 VectorStore 并加载索引
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(vector_store)
    
    # 3. 创建查询引擎
    # 粗排：similarity_top_k=10，先从库里捞出 10 个最像的
    # 精排：使用 reranker 对这 10 个结果进行二次打分，保留最相关的 2 个给 LLM
    reranker = get_reranker(top_n=2)
    
    query_engine = index.as_query_engine(
        similarity_top_k=10,
        node_postprocessors=[reranker]
    )
    return query_engine

if __name__ == "__main__":
    # 脚本入口：执行一次测试查询
    logger.info("=== 查询引擎单次测试启动 ===")
    
    # 1. 设置全局配置并获取调试处理器
    # 注意：setup_settings 会被 get_query_engine 调用，这里我们手动调用一次以获取处理器
    from llama_index.core.callbacks import CBEventType
    llama_debug = setup_settings()
    
    # 2. 初始化引擎
    engine = get_query_engine()
    
    query_text = "Project X 的核心指标是什么？"
    
    # 3. 执行查询
    start_time = time.time()
    response = engine.query(query_text)
    total_duration = time.time() - start_time
    
    # 4. 提取各环节耗时 (从调试处理器中获取)
    # get_event_time_info 返回的是 EventStats 对象
    retrieval_stats = llama_debug.get_event_time_info(CBEventType.RETRIEVE)
    retrieval_time = retrieval_stats.total_secs if hasattr(retrieval_stats, 'total_secs') else 0
    
    # 获取重排事件耗时 (Cross-Encoder)
    rerank_stats = llama_debug.get_event_time_info(CBEventType.RERANKING)
    rerank_time = rerank_stats.total_secs if hasattr(rerank_stats, 'total_secs') else 0
    
    # 获取 LLM 合成回答耗时
    llm_stats = llama_debug.get_event_time_info(CBEventType.LLM)
    llm_time = llm_stats.total_secs if hasattr(llm_stats, 'total_secs') else 0
    
    print("-" * 30)
    print(f"Query: {query_text}")
    print(f"Response: {response}")
    print("-" * 30)
    print(f"性能评估 (Performance Evaluation):")
    print(f"  - 初始检索 (Bi-Encoder): {retrieval_time:.4f} 秒")
    print(f"  - 语义重排 (Cross-Encoder): {rerank_time:.4f} 秒")
    print(f"  - LLM 回答生成: {llm_time:.4f} 秒")
    print(f"  - 总耗时: {total_duration:.4f} 秒")
    print("-" * 30)
    
    logger.info("=== 查询引擎单次测试结束 ===")
