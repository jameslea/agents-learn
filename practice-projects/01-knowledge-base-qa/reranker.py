from llama_index.core.postprocessor import SentenceTransformerRerank
import logging
import os
from huggingface_hub import snapshot_download, model_info

# 配置日志
logger = logging.getLogger("reranker")

def ensure_model_downloaded(model_name: str):
    """
    检查模型是否已下载，如果没有则进行下载并显示进度。
    """
    logger.info(f"🔍 检查模型本地状态: {model_name}")
    
    try:
        # 首先尝试静默检查本地是否存在
        snapshot_download(repo_id=model_name, local_files_only=True)
        logger.info(f"✅ 模型 {model_name} 已在本地缓存，跳过下载。")
    except Exception:
        # 如果本地不存在，则准备下载
        logger.info(f"🚀 本地未找到模型，准备从 HuggingFace 下载 {model_name}...")
        
        # 尝试获取模型元数据以显示大小
        try:
            info = model_info(repo_id=model_name)
            total_size = sum(f.size for f in info.siblings if f.size)
            if total_size:
                size_mb = total_size / (1024 * 1024)
                if size_mb > 1024:
                    logger.info(f"📊 预计下载大小: {size_mb/1024:.2f} GB")
                else:
                    logger.info(f"📊 预计下载大小: {size_mb:.2f} MB")
        except Exception:
            # 如果获取不到信息（如网络限制），则不显示大小，直接进入下载
            pass

        logger.info("提示：下载进度将显示在下方，请保持网络连接。")
        try:
            snapshot_download(repo_id=model_name, local_files_only=False)
            logger.info(f"✅ 模型 {model_name} 下载成功！")
        except Exception as e:
            logger.error(f"❌ 模型下载失败: {e}")
            logger.error("请检查网络连接或尝试设置环境变量: export HF_ENDPOINT=https://hf-mirror.com")

def get_reranker(top_n: int = 2):
    """
    初始化 Cross-Encoder 重排序模型。
    
    使用 BAAI/bge-reranker-base 模型。
    Cross-Encoder 模型会同时输入 (Query, Passage) 对，输出一个 0-1 之间的相关性分数。
    相比传统的向量检索（Bi-Encoder），它的精度更高，能够识别细微的语义差别。
    """
    model_name = "BAAI/bge-reranker-base"
    
    # 预先检查并下载模型，确保有日志和进度提示
    ensure_model_downloaded(model_name)
    
    logger.info(f"正在加载 Reranker 引擎 (Top N: {top_n})...")
    
    # top_n 表示重排序后最终保留几个结果给 LLM
    reranker = SentenceTransformerRerank(
        model=model_name, 
        top_n=top_n
    )
    
    # 自动识别并打印运行设备
    # 在 LlamaIndex 中，可以通过 reranker._model.device 获取底层 torch 设备
    try:
        import torch
        device = reranker._model.device
        logger.info(f"✨ Reranker 模型运行设备: {device}")
        if "cuda" in str(device):
            logger.info("🚀 已开启 NVIDIA GPU 加速 (CUDA)")
        elif "mps" in str(device):
            logger.info("🚀 已开启 Apple Silicon GPU 加速 (MPS)")
        else:
            logger.info("ℹ️ 当前运行在 CPU 模式 (如果推理较慢，请检查环境配置)")
    except Exception:
        pass
        
    return reranker
