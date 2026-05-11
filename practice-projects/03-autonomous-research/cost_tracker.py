import logging
import tiktoken
from pydantic import BaseModel, Field

logger = logging.getLogger("cost_tracker")

class TokenBudgetTracker(BaseModel):
    """
    用于追踪 LLM 的 Token 消耗并实施预算控制 (防破产机制)。
    解决坑位 C3 (成本失控)。
    """
    max_tokens: int = Field(default=50000, description="整个调研任务允许消耗的最大 Token 总数")
    prompt_tokens: int = Field(default=0, description="已消耗的提示词 Token")
    completion_tokens: int = Field(default=0, description="已消耗的生成词 Token")
    
    # 采用 DeepSeek v2 API 价格估算（元 / 1M tokens）
    # 假设：输入 1元/1M，输出 2元/1M
    price_per_m_prompt: float = 1.0
    price_per_m_completion: float = 2.0

    def add_usage(self, prompt_tokens: int, completion_tokens: int):
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        
        # 检查是否触及熔断红线
        if self.total_tokens() >= self.max_tokens:
            logger.warning(f"🚨 触发熔断！当前消耗 Token ({self.total_tokens()}) 已达到或超过预算上限 ({self.max_tokens})。")
            raise BudgetExceededError(f"Token 消耗超限: {self.total_tokens()}/{self.max_tokens}")

    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
        
    def estimate_cost_cny(self) -> float:
        cost = (self.prompt_tokens / 1_000_000) * self.price_per_m_prompt + \
               (self.completion_tokens / 1_000_000) * self.price_per_m_completion
        return round(cost, 4)
        
    def report(self):
        logger.info("="*30)
        logger.info(f"📊 成本监控报告")
        logger.info(f"   输入 Token: {self.prompt_tokens}")
        logger.info(f"   输出 Token: {self.completion_tokens}")
        logger.info(f"   总计 Token: {self.total_tokens()} / {self.max_tokens}")
        logger.info(f"   预估花费: ￥{self.estimate_cost_cny()}")
        logger.info("="*30)

class BudgetExceededError(Exception):
    """当达到 Token 预算上限时抛出的异常"""
    pass

# 提供一个便捷的方法来通过 tiktoken 本地估算输入 token 数（为了省钱，在发送请求前拦截）
def estimate_tokens(text: str, model_name: str = "cl100k_base") -> int:
    try:
        encoding = tiktoken.get_encoding(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))
