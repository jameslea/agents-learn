import time
import logging
import sys

# 立即配置基础日志，以便在加载重型库之前就能输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger("ingestion")

logger.info("正在启动 [数据摄入] 程序，准备加载系统模块...")
start_import_time = time.time()

# 开始加载重型库
import os
import chromadb
from datetime import datetime
from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader, 
    StorageContext,
    Settings
)
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from dotenv import load_dotenv

# 计算导入耗时
import_duration = time.time() - start_import_time
# 输出导入耗时
logger.info(f"[数据摄入] 模块加载完成，耗时: {import_duration:.2f} 秒")

"""
主要第三方库组件说明：
- chromadb: 一个开源的向量数据库，用于存储文档的向量表示及其元数据。
- VectorStoreIndex: LlamaIndex 的核心组件，用于构建、存储和查询向量索引。
- SimpleDirectoryReader: 简单高效的本地目录读取器，支持多种文件格式。
- StorageContext: 用于配置 LlamaIndex 的存储后端（如内存、磁盘或向量库）。
- Settings: LlamaIndex 的全局配置中心，用于定义默认的 LLM 和 Embedding 模型。
- ChromaVectorStore: 将 ChromaDB 适配为 LlamaIndex 的向量存储引擎。
- SentenceSplitter: 文本切分器，按句子边界将文档拆分为固定大小的块。
- HuggingFaceEmbedding: 封装了 HuggingFace 上的开源向量模型。
- OpenAILike: 兼容 OpenAI API 格式的 LLM 封装类，适用于对接 DeepSeek 等第三方服务。
"""

# 加载环境变量 (.env 文件)，包含 API Key 和基础配置
load_dotenv()

# 数据源目录和向量数据库持久化路径
DATA_DIR = "./practice-projects/01-knowledge-base-qa/data"
CHROMA_DB_PATH = "./practice-projects/01-knowledge-base-qa/chroma_db"

def setup_settings():
    """
    配置 LlamaIndex 的全局设置，包括 Embedding 模型和 LLM。
    """
    # 1. 配置 Embedding 模型：使用本地 HuggingFace 模型
    # BAAI/bge-small-zh-v1.5 是一个轻量且强大的中文向量模型，适合本地运行
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    
    # 2. 配置 LLM：对接兼容 OpenAI 接口的服务 (如 DeepSeek)
    Settings.llm = OpenAILike(
        model=os.getenv("MODEL_NAME", "deepseek-v4-flash"),
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        is_chat_model=True
    )

def ingest_documents():
    """
    执行文档摄入流程：读取文档 -> 切分文本 -> 构建索引 -> 持久化存储。
    """
    setup_settings()
    
    # 1. 加载文档：从指定目录读取所有文件
    logger.info(f"正在从 {DATA_DIR} 加载文档...")
    reader = SimpleDirectoryReader(input_dir=DATA_DIR)
    documents = reader.load_data()
    logger.info(f"成功加载 {len(documents)} 个原始文档。")
    
    # 2. 文本切分：将大文档切分为固定大小的块 (Node)
    logger.info("正在进行语义切分...")
    node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    nodes = node_parser.get_nodes_from_documents(documents)
    logger.info(f"切分完成，共生成 {len(nodes)} 个文本块 (Nodes)。")
    
    # 3. 初始化向量数据库 (ChromaDB)
    db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    chroma_collection = db.get_or_create_collection("kb_qa_collection")
    
    # 4. 设置 LlamaIndex 的存储上下文
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # 5. 构建并保存索引
    logger.info("正在计算向量并存入 ChromaDB (首次运行会加载/下载模型，请稍候)...")
    index = VectorStoreIndex(
        nodes, 
        storage_context=storage_context,
        show_progress=True # 开启内置进度条
    )
    
    logger.info("索引构建完成！数据已持久化到磁盘。")
    return index

if __name__ == "__main__":
    logger.info("=== 知识库摄入脚本启动 ===")
    ingest_documents()
    logger.info("=== 知识库摄入脚本运行结束 ===")
