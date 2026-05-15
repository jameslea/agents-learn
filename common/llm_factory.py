"""
统一的 LLM 构建入口。

职责：
- 为项目中的 LangChain `ChatOpenAI` 初始化提供单一出口
- 支持 OpenAI-compatible 多提供商（DeepSeek / OpenAI / MiniMax / custom）
- 将各提供商的 base_url、api_key、模型默认值和特殊参数收敛到一处
- 兼容 DeepSeek 旧模型别名到 V4 模型的迁移，并只对 DeepSeek 注入 thinking 参数

设计约束：
- 调用方只关心业务参数，如 `temperature`、`model_name`、`json_mode`
- 模型兼容细节收敛在这里，避免散落在各示例脚本中
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Literal

from langchain_openai import ChatOpenAI

# 旧别名将在 DeepSeek 侧弃用，这里统一映射到 V4 模型与显式 thinking 配置。
DEEPSEEK_CHAT_ALIAS = "deepseek-chat"
DEEPSEEK_REASONER_ALIAS = "deepseek-reasoner"
DEEPSEEK_FLASH_MODEL = "deepseek-v4-flash"
MINIMAX_DEFAULT_MODEL = "MiniMax-M2.7"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_PROVIDER = "deepseek"
DEFAULT_THINKING_MODE = "disabled"
ProviderName = Literal["deepseek", "openai", "minimax", "custom"]
THINKING_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think>\s*", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    model: str
    api_key: str | None
    base_url: str | None
    supports_json_mode: bool = True
    min_temperature: float | None = None


class ProviderChatOpenAI(ChatOpenAI):
    """ChatOpenAI with small provider-specific response normalization."""

    strip_thinking_blocks: bool = False

    def _generate(self, *args: Any, **kwargs: Any):
        result = super()._generate(*args, **kwargs)
        if not self.strip_thinking_blocks:
            return result

        normalized_generations = []
        for generation in result.generations:
            message = generation.message
            content = _strip_thinking_blocks(message.content)
            if content == message.content:
                normalized_generations.append(generation)
                continue

            normalized_message = message.model_copy(update={"content": content})
            update = {"message": normalized_message}
            if isinstance(content, str):
                update["text"] = content
            normalized_generations.append(generation.model_copy(update=update))

        return result.model_copy(update={"generations": normalized_generations})


def _strip_thinking_blocks(content: Any) -> Any:
    """Remove provider-emitted <think> blocks while preserving the final answer."""
    if isinstance(content, str):
        return THINKING_BLOCK_RE.sub("", content).strip()

    if isinstance(content, list):
        normalized = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                cleaned_text = THINKING_BLOCK_RE.sub("", block["text"]).strip()
                if cleaned_text:
                    normalized.append({**block, "text": cleaned_text})
                continue
            normalized.append(block)
        return normalized

    return content


def _normalize_thinking_mode(thinking: str | None) -> str | None:
    """规范化 thinking 开关，避免将非法值传给模型网关。"""
    if thinking is None or thinking == "":
        return None

    normalized = thinking.strip().lower()
    if normalized not in {"enabled", "disabled"}:
        raise ValueError("thinking must be 'enabled' or 'disabled'")
    return normalized


def _normalize_provider(provider: str | None = None) -> ProviderName:
    selected = (provider or os.getenv("LLM_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    aliases = {
        "deepseek": "deepseek",
        "ds": "deepseek",
        "openai": "openai",
        "minimax": "minimax",
        "mini-max": "minimax",
        "custom": "custom",
        "openai-compatible": "custom",
        "openai_compatible": "custom",
    }
    if selected not in aliases:
        raise ValueError(f"Unsupported LLM_PROVIDER '{selected}'. Use deepseek/openai/minimax/custom.")
    return aliases[selected]  # type: ignore[return-value]


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


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


def resolve_provider_config(
    *,
    provider: str | None = None,
    model_name: str | None = None,
) -> ProviderConfig:
    """Resolve provider-specific OpenAI-compatible connection settings."""
    selected_provider = _normalize_provider(provider)
    legacy_model = os.getenv("MODEL_NAME")
    unified_model = os.getenv("LLM_MODEL")

    if selected_provider == "deepseek":
        model = model_name or os.getenv("DEEPSEEK_MODEL") or unified_model or legacy_model or DEEPSEEK_FLASH_MODEL
        return ProviderConfig(
            name="deepseek",
            model=model,
            api_key=_first_env("DEEPSEEK_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"),
            base_url=_first_env("DEEPSEEK_BASE_URL", "LLM_BASE_URL", "OPENAI_BASE_URL") or "https://api.deepseek.com",
            supports_json_mode=True,
        )

    if selected_provider == "minimax":
        model = model_name or os.getenv("MINIMAX_MODEL") or unified_model or legacy_model or MINIMAX_DEFAULT_MODEL
        return ProviderConfig(
            name="minimax",
            model=model,
            api_key=_first_env("MINIMAX_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"),
            base_url=_first_env("MINIMAX_BASE_URL", "LLM_BASE_URL", "OPENAI_BASE_URL") or "https://api.minimaxi.com/v1",
            supports_json_mode=False,
            min_temperature=0.1,
        )

    if selected_provider == "openai":
        model = model_name or os.getenv("OPENAI_MODEL") or unified_model or legacy_model or OPENAI_DEFAULT_MODEL
        return ProviderConfig(
            name="openai",
            model=model,
            api_key=_first_env("OPENAI_API_KEY", "LLM_API_KEY"),
            base_url=_first_env("OPENAI_BASE_URL", "LLM_BASE_URL"),
            supports_json_mode=True,
        )

    model = model_name or os.getenv("CUSTOM_LLM_MODEL") or unified_model or legacy_model
    if not model:
        raise ValueError("CUSTOM provider requires CUSTOM_LLM_MODEL, LLM_MODEL, MODEL_NAME, or explicit model_name.")
    return ProviderConfig(
        name="custom",
        model=model,
        api_key=_first_env("CUSTOM_LLM_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"),
        base_url=_first_env("CUSTOM_LLM_BASE_URL", "LLM_BASE_URL", "OPENAI_BASE_URL"),
        supports_json_mode=os.getenv("CUSTOM_LLM_SUPPORTS_JSON_MODE", "true").strip().lower() != "false",
    )


def _apply_provider_temperature(provider_config: ProviderConfig, temperature: float) -> float:
    if provider_config.min_temperature is not None and temperature <= 0:
        return provider_config.min_temperature
    return temperature


def build_llm(
    *,
    temperature: float = 0,
    model_name: str | None = None,
    provider: str | None = None,
    thinking: str | None = None,
    json_mode: bool = False,
    **kwargs: Any,
) -> ChatOpenAI:
    """
    创建项目统一使用的 ChatOpenAI 实例。

    约定：
    - 优先读取调用方显式传入的 provider / model_name / thinking
    - 未显式传入时，回退到 LLM_PROVIDER / LLM_MODEL / 各 provider 专属环境变量
    - DeepSeek V4 才注入 thinking，MiniMax/OpenAI/custom 不接收 DeepSeek 专属参数
    - json_mode 只对声明支持的 provider 写入 response_format
    """
    provider_config = resolve_provider_config(provider=provider, model_name=model_name)
    resolved_model = provider_config.model
    resolved_thinking = None
    if provider_config.name == "deepseek":
        resolved_model, resolved_thinking = _resolve_model_settings(provider_config.model, thinking)

    # DeepSeek 的 thinking 开关属于额外请求体字段，不属于通用 OpenAI 参数。
    extra_body = dict(kwargs.pop("extra_body", {}) or {})
    if provider_config.name == "deepseek" and resolved_thinking and resolved_model.startswith("deepseek-v4-"):
        extra_body["thinking"] = {"type": resolved_thinking}
        if resolved_thinking == "enabled":
            # 仅在思考模式下透传 reasoning_effort，避免给非思考模式增加无效参数。
            reasoning_effort = kwargs.pop(
                "reasoning_effort",
                os.getenv("DEEPSEEK_REASONING_EFFORT"),
            )
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

    model_kwargs = dict(kwargs.pop("model_kwargs", {}) or {})
    if json_mode and provider_config.supports_json_mode:
        model_kwargs["response_format"] = {"type": "json_object"}

    llm_kwargs = {
        "model": resolved_model,
        "temperature": _apply_provider_temperature(provider_config, temperature),
        **kwargs,
    }
    if provider_config.api_key:
        llm_kwargs["api_key"] = provider_config.api_key
    if provider_config.base_url:
        llm_kwargs["base_url"] = provider_config.base_url
    if extra_body:
        llm_kwargs["extra_body"] = extra_body
    if model_kwargs:
        llm_kwargs["model_kwargs"] = model_kwargs

    return ProviderChatOpenAI(
        strip_thinking_blocks=provider_config.name == "minimax",
        **llm_kwargs,
    )


def build_llamaindex_llm(
    *,
    temperature: float = 0,
    model_name: str | None = None,
    provider: str | None = None,
    thinking: str | None = None,
    **kwargs: Any,
) -> Any:
    """Create a LlamaIndex OpenAILike LLM with the same provider resolution."""
    from llama_index.llms.openai_like import OpenAILike

    provider_config = resolve_provider_config(provider=provider, model_name=model_name)
    resolved_model = provider_config.model
    resolved_thinking = None
    if provider_config.name == "deepseek":
        resolved_model, resolved_thinking = _resolve_model_settings(provider_config.model, thinking)

    additional_kwargs = dict(kwargs.pop("additional_kwargs", {}) or {})
    if provider_config.name == "deepseek" and resolved_thinking and resolved_model.startswith("deepseek-v4-"):
        additional_kwargs["thinking"] = {"type": resolved_thinking}

    llm_kwargs = {
        "model": resolved_model,
        "api_key": provider_config.api_key,
        "api_base": provider_config.base_url,
        "is_chat_model": True,
        "temperature": _apply_provider_temperature(provider_config, temperature),
        **kwargs,
    }
    if additional_kwargs:
        llm_kwargs["additional_kwargs"] = additional_kwargs

    return OpenAILike(**llm_kwargs)
