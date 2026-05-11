import json
import logging
import os
import hashlib
from typing import Dict, Any, List
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import DuckDuckGoSearchResults
from pydantic import BaseModel

logger = logging.getLogger("task_executor")

# 本地搜索缓存文件路径，存放在当前脚本所在目录下
CACHE_FILE = os.path.join(os.path.dirname(__file__), "search_cache.json")

class TaskExecutor:
    """
    负责执行具体的调研子任务（如联网搜索）。
    考虑到 Tavily 免费额度有限，内置了本地缓存机制。
    如果预算耗尽或需要免费方案，可无缝回退到 DuckDuckGo。
    """
    def __init__(self, use_tavily: bool = True, use_cache: bool = True):
        self.use_tavily = use_tavily
        self.use_cache = use_cache
        self.cache = self._load_cache()
        
        if self.use_tavily and os.getenv("TAVILY_API_KEY"):
            logger.info("🔧 初始化搜索工具: Tavily Search")
            self.search_tool = TavilySearchResults(max_results=3)
        else:
            logger.info("🔧 初始化搜索工具: DuckDuckGo (免费方案回退)")
            self.search_tool = DuckDuckGoSearchResults(num_results=3)

    def _load_cache(self) -> Dict[str, Any]:
        if not os.path.exists(CACHE_FILE):
            return {}
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"无法加载搜索缓存: {e}")
            return {}

    def _save_cache(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"无法保存搜索缓存: {e}")

    def _get_cache_key(self, query: str) -> str:
        # 使用查询字符串的 MD5 作为缓存 Key
        return hashlib.md5(query.encode("utf-8")).hexdigest()

    def search(self, query: str) -> str:
        """
        执行搜索操作。优先命中本地缓存。
        """
        logger.info(f"🔎 正在搜索: '{query}'")
        
        cache_key = self._get_cache_key(query)
        
        if self.use_cache and cache_key in self.cache:
            logger.info("✅ 命中本地搜索缓存，省下一次 API 调用！")
            return self.cache[cache_key]

        try:
            # 执行真实搜索
            # langchain tools 通常支持 .invoke() 
            results = self.search_tool.invoke({"query": query})
            
            # 简单清洗并格式化结果
            if isinstance(results, list):
                # Tavily 通常返回包含 url 和 content 的字典列表
                formatted_results = "\n".join([f"来源: {r.get('url', '未知')}\n内容摘要: {r.get('content', '无内容')}\n" for r in results])
            else:
                # DuckDuckGo 返回字符串
                formatted_results = str(results)
                
            if not formatted_results.strip():
                 formatted_results = "未找到相关结果。"

            # 写入缓存
            if self.use_cache:
                self.cache[cache_key] = formatted_results
                self._save_cache()
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 搜索执行失败: {e}")
            return f"搜索失败: {str(e)}"

# 测试代码
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    from dotenv import load_dotenv
    load_dotenv()
    
    executor = TaskExecutor()
    res = executor.search("2026年 AI Agent 最新进展")
    print("\n--- 搜索结果 ---")
    print(res)
