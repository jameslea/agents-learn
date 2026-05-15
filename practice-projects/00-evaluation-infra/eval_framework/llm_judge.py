import os
import json
from typing import List
from openai import OpenAI
from common.llm_factory import resolve_provider_config
from .metrics import EvalResult
from dotenv import load_dotenv

"""
主要第三方库组件说明：
- OpenAI: OpenAI 官方 Python 客户端，用于调用兼容 OpenAI 接口的模型（如 GPT-4, DeepSeek 等）。
- EvalResult: 自定义的 Pydantic 数据模型，用于标准化存储评估结果。
- load_dotenv: 从 .env 文件加载环境变量，保护 API Key 等敏感信息。
"""

# 加载环境变量
load_dotenv()

import logging
logger = logging.getLogger("llm_judge")

class LLMJudge:
    """
    LLM 评测类：利用强大的 LLM (如 GPT-4 或 DeepSeek) 作为裁判，
    对另一个 LLM 或 RAG 系统的输出进行自动化评分。
    """
    def __init__(self, model=None):
        """
        初始化 OpenAI 客户端。
        优先读取环境变量中的配置。
        """
        provider_config = resolve_provider_config(model_name=model)
        self.model = provider_config.model
        self.supports_json_mode = provider_config.supports_json_mode
        
        logger.info(
            "LLM Judge 初始化: Provider=%s Model=%s BaseURL=%s",
            provider_config.name,
            self.model,
            provider_config.base_url,
        )
        self.client = OpenAI(api_key=provider_config.api_key, base_url=provider_config.base_url)

    def _chat_json(self, prompt: str):
        request = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.supports_json_mode:
            request["response_format"] = {"type": "json_object"}
        return self.client.chat.completions.create(**request)

    def _parse_eval_result(self, content: str | None) -> EvalResult:
        if not content:
            raise json.JSONDecodeError("empty response", "", 0)
        try:
            return EvalResult(**json.loads(content))
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise
            return EvalResult(**json.loads(content[start : end + 1]))

    def evaluate_faithfulness(self, context: str, answer: str) -> EvalResult:
        """
        评估忠实度 (Faithfulness)：判断回答是否完全基于提供的上下文，而不是凭空捏造 (幻觉)。
        
        参数:
            context: 检索到的原始文档内容。
            answer: 系统生成的回答。
        返回:
            EvalResult: 包含分数 (0-1) 和推理理由。
        """
        prompt = f"""
        你是一个严谨的评估员。请判断以下回答是否完全基于提供的上下文。
        如果回答包含上下文之外的信息，即使该信息是正确的，也请给出低分。
        
        上下文: {context}
        回答: {answer}
        
        请仅以以下 JSON 格式输出，不要包含任何其他文字：
        {{
            "score": 0.0 到 1.0 之间的分数,
            "reasoning": "简短的评估理由"
        }}
        """
        response = self._chat_json(prompt)
        content = response.choices[0].message.content
        try:
            return self._parse_eval_result(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败！原始响应内容: {content}")
            return EvalResult(score=0.0, reasoning=f"JSON 解析失败: {str(e)}")

    def evaluate_relevance(self, query: str, answer: str) -> EvalResult:
        """
        评估相关性 (Relevance)：判断回答是否准确、全面地解决了用户的问题。
        
        参数:
            query: 用户的原始查询。
            answer: 系统生成的回答。
        返回:
            EvalResult: 包含分数 (0-1) 和推理理由。
        """
        prompt = f"""
        请评估以下回答对用户问题的相关性。
        
        用户问题: {query}
        回答: {answer}
        
        请仅以以下 JSON 格式输出，不要包含任何其他文字：
        {{
            "score": 0.0 到 1.0 之间的分数,
            "reasoning": "简短的评估理由"
        }}
        """
        response = self._chat_json(prompt)
        content = response.choices[0].message.content
        try:
            return self._parse_eval_result(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败！原始响应内容: {content}")
            return EvalResult(score=0.0, reasoning=f"JSON 解析失败: {str(e)}")
