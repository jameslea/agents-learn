import os
import logging
from dotenv import load_dotenv

from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.embeddings import FakeEmbeddings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

# 目标抓取的知识库 URL (以 LangGraph 官方概念介绍为例)
KNOWLEDGE_URL = "https://langchain-ai.github.io/langgraph/concepts/high_level/"
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

def create_vector_db():
    logger.info(f"🌐 开始从 {KNOWLEDGE_URL} 抓取网页数据...")
    
    # 1. 加载网页内容
    # 注意：如果遇到反爬，可以带上 fake_useragent 或者使用 PlaywrightLoader
    loader = WebBaseLoader(
        web_paths=(KNOWLEDGE_URL,),
    )
    docs = loader.load()
    logger.info(f"✅ 网页提取成功，共加载 {len(docs)} 个原始文档结构。")
    
    # 2. 文本切割
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,   # 每块大约 1000 字符
        chunk_overlap=200, # 原文块之间首尾重叠 200 字符，防语境断裂
        add_start_index=True 
    )
    all_splits = text_splitter.split_documents(docs)
    logger.info(f"✂️ 文本切割完毕，共计生成 {len(all_splits)} 个 Chunk 切片。")
    
    # 3. 嵌入与持久化存储
    logger.info("🧠 正在使用 Fake Embedding 存入本地 Chroma 数据库 (仅测试链路)...")
    embeddings = FakeEmbeddings(size=1536)
    
    # 如果已存在旧的数据库，Chroma 也能覆盖或添加，但这里为了干净先指明路径
    vectorstore = Chroma.from_documents(
        documents=all_splits,
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    )
    
    logger.info(f"🎉 知识库已成功构建！持久化保存在目录: {CHROMA_PATH}")
    return vectorstore

if __name__ == "__main__":
    create_vector_db()
