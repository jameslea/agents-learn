from llama_index.core.postprocessor import SentenceTransformerRerank
import logging

logger = logging.getLogger("reranker")

def get_reranker(top_n: int = 2):
    """
    初始化 Cross-Encoder 重排序模型。
    
    使用 BAAI/bge-reranker-base 模型。
    Cross-Encoder 模型会同时输入 (Query, Passage) 对，输出一个 0-1 之间的相关性分数。
    相比传统的向量检索（Bi-Encoder），它的精度更高，能够识别细微的语义差别。
    """
    logger.info(f"正在加载 Reranker 模型: BAAI/bge-reranker-base (Top N: {top_n})...")
    
    # top_n 表示重排序后最终保留几个结果给 LLM
    reranker = SentenceTransformerRerank(
        model="BAAI/bge-reranker-base", 
        top_n=top_n
    )
    return reranker
