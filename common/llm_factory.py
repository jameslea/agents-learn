"""
统一的 LLM 构建入口。

职责：
- 为项目中的 LangChain `ChatOpenAI` 初始化提供单一出口
- 兼容 DeepSeek 旧模型别名到 V4 模型的迁移
- 统一处理 `thinking` / `reasoning_effort` 这类 DeepSeek V4 特有参数

设计约束：
- 调用方只关心业务参数，如 `temperature`、`model_name`
- 模型兼容细节收敛在这里，避免散落在各示例脚本中
- 默认对 DeepSeek V4 显式写入 `thinking`，避免依赖服务端默认行为
"""

import os
from typing import Any

from langchain_openai import ChatOpenAI

# 旧别名将在 DeepSeek 侧弃用，这里统一映射到 V4 模型与显式 thinking 配置。
DEEPSEEK_CHAT_ALIAS = "deepseek-chat"
DEEPSEEK_REASONER_ALIAS = "deepseek-reasoner"
DEEPSEEK_FLASH_MODEL = "deepseek-v4-flash"
DEFAULT_MODEL_NAME = DEEPSEEK_FLASH_MODEL
DEFAULT_THINKING_MODE = "disabled"


def _normalize_thinking_mode(thinking: str | None) -> str | None:
    """规范化 thinking 开关，避免将非法值传给模型网关。"""
    if thinking is None or thinking == "":
        return None

    normalized = thinking.strip().lower()
    if normalized not in {"enabled", "disabled"}:
        raise ValueError("thinking must be 'enabled' or 'disabled'")
    return normalized


def _resolve_model_settings(
    model_name: str,
    thinking: str | None,
) -> tuple[str, str | None]:
    """统一解析模型名与 thinking 模式，兼容旧别名与新的 V4 配置。"""
    explicit_thinking = _normalize_thinking_mode(thinking)

    if model_name == DEEPSEEK_CHAT_ALIAS:
        return DEEPSEEK_FLASH_MODEL, "disabled"

    if model_name == DEEPSEEK_REASONER_ALIAS:
        return DEEPSEEK_FLASH_MODEL, "enabled"

    if model_name.startswith("deepseek-v4-"):
        env_thinking = os.getenv("DEEPSEEK_THINKING", DEFAULT_THINKING_MODE)
        resolved_thinking = explicit_thinking or _normalize_thinking_mode(env_thinking)
        return model_name, resolved_thinking

    return model_name, explicit_thinking


def build_llm(
    *,
    temperature: float = 0,
    model_name: str | None = None,
    thinking: str | None = None,
    **kwargs: Any,
) -> ChatOpenAI:
    """
    创建项目统一使用的 ChatOpenAI 实例。

    约定：
    - 优先读取调用方显式传入的 model_name / thinking
    - 未显式传入时，回退到环境变量
    - 对 DeepSeek V4 显式注入 thinking，避免依赖服务端默认行为
    """
    selected_model = model_name or os.getenv("MODEL_NAME", DEFAULT_MODEL_NAME)
    resolved_model, resolved_thinking = _resolve_model_settings(
        selected_model,
        thinking,
    )

    # DeepSeek 的 thinking 开关属于额外请求体字段，不属于通用 OpenAI 参数。
    extra_body = dict(kwargs.pop("extra_body", {}) or {})
    if resolved_thinking and resolved_model.startswith("deepseek-v4-"):
        extra_body["thinking"] = {"type": resolved_thinking}
        if resolved_thinking == "enabled":
            # 仅在思考模式下透传 reasoning_effort，避免给非思考模式增加无效参数。
            reasoning_effort = kwargs.pop(
                "reasoning_effort",
                os.getenv("DEEPSEEK_REASONING_EFFORT"),
            )
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

    llm_kwargs = {
        "model": resolved_model,
        "temperature": temperature,
        **kwargs,
    }
    if extra_body:
        llm_kwargs["extra_body"] = extra_body

    return ChatOpenAI(**llm_kwargs)
