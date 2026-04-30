"""
为 LM Studio 定制的 LLM 和 Embedding 函数。

关键问题：LightRAG 调用 LLM 函数时，签名约定为
    llm_func(prompt, system_prompt=None, history_messages=[], **kwargs)
即第一个位置参数是 prompt，不是 model。
而 openai_complete_if_cache 的签名是 (model, prompt, ...)。
所以需要适配层来转换。
"""
import numpy as np
from openai import AsyncOpenAI
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import wrap_embedding_func_with_attrs

# LM Studio 配置
LM_STUDIO_BASE = "http://localhost:1234/v1"
LLM_MODEL = "qwen/qwen3-4b-2507"
EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"


async def lm_studio_complete(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list | None = None,
    **kwargs,
) -> str:
    """适配 LightRAG 调用约定的 LLM 函数。

    LightRAG 的调用方式: llm_func(prompt, system_prompt=..., history_messages=...)
    内部转换为 openai_complete_if_cache(model=..., prompt=..., ...)
    """
    # 过滤掉 LightRAG 内部使用的参数，避免传递给 OpenAI API
    filtered_kwargs = {k: v for k, v in kwargs.items()
                       if k not in ("hashing_kv", "_priority")}

    return await openai_complete_if_cache(
        model=LLM_MODEL,
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages or [],
        base_url=LM_STUDIO_BASE,
        api_key="lm-studio",
        **filtered_kwargs,
    )


@wrap_embedding_func_with_attrs(
    embedding_dim=768,
    max_token_size=8192,
    model_name=EMBED_MODEL,
)
async def lm_studio_embed(
    texts: list[str],
    model: str = EMBED_MODEL,
    base_url: str = LM_STUDIO_BASE,
    api_key: str = "lm-studio",
    **kwargs,
) -> np.ndarray:
    """调用 LM Studio 的 Embedding API，返回 768 维向量。"""
    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    response = await client.embeddings.create(model=model, input=texts)
    return np.array([item.embedding for item in response.data])
