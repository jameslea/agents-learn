"""
容错 JSON 解析工具
用于修复 DeepSeek 在 json_mode 下偶发的格式错误（如漏逗号）
"""
import re
import json
from typing import Type, TypeVar
from pydantic import BaseModel
from utils.logging_utils import get_logger, timed_block

T = TypeVar("T", bound=BaseModel)
logger = get_logger(__name__)


def _fix_json(text: str) -> str:
    """尝试修复常见的 JSON 格式错误"""
    # 提取 { } 之间的内容
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        text = match.group(0)

    # 1. 修复：未加引号的键名 (Naked Keys)
    # 例如 { is_approved: true } -> { "is_approved": true }
    text = re.sub(
        r'([{,]\s*)([a-zA-Z_][\w_]*)(\s*:)',
        r'\1"\2"\3',
        text
    )

    # 2. 修复：字段值遗漏引号的情况 (针对字符串值)
    # 例如 "suggestions": [value1, value2] -> "suggestions": ["value1", "value2"]
    # 匹配模式：冒号后接非引号、非数字、非布尔、非左括号的字符，直到逗号或右括号
    text = re.sub(
        r'(:\s*)([^"\[\{\d\-tfn\s][^,\]\}]*?)(?=\s*[,\]\}])',
        r'\1"\2"',
        text,
        flags=re.DOTALL
    )

    # 3. 修复：数组中遗漏引号的项
    # 例如 ["item1", item2, "item3"] -> ["item1", "item2", "item3"]
    text = re.sub(
        r'(,\s*)([^"\[\{\d\-tfn\s][^,\]\}]*?)(?=\s*[,\]])',
        r'\1"\2"',
        text
    )
    # 处理数组第一个项遗漏引号
    text = re.sub(
        r'(\[\s*)([^"\[\{\d\-tfn\s][^,\]\}]*?)(?=\s*[,\]])',
        r'\1"\2"',
        text
    )

    # 4. 修复：字符串值结尾换行后缺少逗号
    text = re.sub(
        r'(")\s*\n(\s*")',
        r'",\n\2',
        text
    )
    return text


def parse_llm_json(raw_text: str, model_class: Type[T]) -> T:
    """
    解析 LLM 返回的 JSON 文本，并映射到 Pydantic 模型。
    自动尝试修复常见格式错误。
    """
    # 先直接尝试
    try:
        with timed_block(logger, f"直接解析 JSON: {model_class.__name__}", slow_after=0.5):
            return model_class.model_validate_json(raw_text)
    except Exception:
        logger.debug("直接解析 JSON 失败，尝试修复: model=%s", model_class.__name__)
        pass

    # 修复后再试
    with timed_block(logger, f"修复 JSON 文本: {model_class.__name__}", slow_after=0.5):
        fixed = _fix_json(raw_text)
    try:
        with timed_block(logger, f"解析修复后 JSON: {model_class.__name__}", slow_after=0.5):
            parsed = model_class.model_validate_json(fixed)
        logger.info("LLM JSON 通过修复后解析成功: model=%s", model_class.__name__)
        return parsed
    except Exception:
        logger.debug("修复后 JSON 解析失败，尝试 json.loads: model=%s", model_class.__name__)
        pass

    # 最后用 json.loads 容错解析
    try:
        with timed_block(logger, f"json.loads 容错解析: {model_class.__name__}", slow_after=0.5):
            obj = json.loads(fixed)
            parsed = model_class.model_validate(obj)
        logger.info("LLM JSON 通过 json.loads 容错解析成功: model=%s", model_class.__name__)
        return parsed
    except Exception as e:
        raise ValueError(
            f"无法解析 LLM 输出为 {model_class.__name__}。\n"
            f"原始输出：\n{raw_text}\n"
            f"修复后：\n{fixed}\n"
            f"错误：{e}"
        )

