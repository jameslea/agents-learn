from typing import List, Dict
import pydantic

"""
主要第三方库组件说明：
- pydantic: 用于 Python 的数据验证和设置管理，通过 BaseModel 定义严格的数据结构。
"""

class EvalResult(pydantic.BaseModel):
    """
    评估结果的数据结构。
    """
    score: float      # 分数，通常在 0 到 1 之间
    reasoning: str    # 评分理由或推理过程

class BasicMetrics:
    """
    基础评估指标类，包含常用的文本匹配和检索评估算法。
    """
    @staticmethod
    def exact_match(prediction: str, reference: str) -> float:
        """完全匹配：预测结果与参考答案必须完全一致 (去除首尾空格)"""
        return 1.0 if prediction.strip() == reference.strip() else 0.0

    @staticmethod
    def contains_match(prediction: str, reference: str) -> float:
        """包含匹配：预测结果中必须包含参考答案中的关键信息"""
        return 1.0 if reference.strip() in prediction.strip() else 0.0

    @staticmethod
    def retrieval_hit_rate(retrieved_ids: List[str], expected_ids: List[str]) -> float:
        """
        检索命中率 (Hit Rate)：衡量检索系统是否成功召回了目标文档。
        
        计算公式: 命中数 / 期望召回的总数
        """
        if not expected_ids:
            return 0.0
        # 计算两个集合的交集大小
        hits = len(set(retrieved_ids) & set(expected_ids))
        return hits / len(expected_ids)
