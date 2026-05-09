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
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    Settings.llm = OpenAILike(
        model=os.getenv("MODEL_NAME", "deepseek-v4-flash"),
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        is_chat_model=True
    )

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
    # 粗排：similarity_top_k=5，先从库里捞出 5 个最像的
    # 精排：使用 reranker 对这 5 个结果进行二次打分，保留最相关的 2 个给 LLM
    reranker = get_reranker(top_n=2)
    
    query_engine = index.as_query_engine(
        similarity_top_k=5,
        node_postprocessors=[reranker]
    )
    return query_engine

if __name__ == "__main__":
    # 脚本入口：执行一次测试查询
    logger.info("=== 查询引擎单次测试启动 ===")
    engine = get_query_engine()
    query_text = "Project X 的核心指标是什么？"
    response = engine.query(query_text)
    
    print(f"Query: {query_text}")
    print(f"Response: {response}")
    logger.info("=== 查询引擎单次测试结束 ===")
