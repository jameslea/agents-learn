from __future__ import annotations

from pydantic import BaseModel, Field


class ContextPolicy(BaseModel):
    """上下文选择策略。

    ContextPolicy 把可变规则从 ContextBuilder 中抽出来。不同 step 或不同
    Agent 可以传入不同 policy，避免把策略写死在构造逻辑里。
    """

    max_recent_steps: int = Field(default=3, description="最多保留最近多少条 step 摘要。")
    max_item_chars: int = Field(default=500, description="单条上下文内容的最大字符数。")
    max_context_chars: int = Field(default=3000, description="整个 ContextBundle 的最大字符预算。")
    min_memory_confidence: float = Field(default=0.6, description="memory 候选进入上下文的最低置信度。")
    include_trace_summary: bool = Field(default=True, description="是否允许 trace summary 进入上下文。")
    allow_untrusted_external_context: bool = Field(
        default=False,
        description="是否允许 untrusted 候选进入模型上下文。默认关闭。",
    )
    exclude_sensitive: bool = Field(default=True, description="是否排除 sensitive 候选。默认开启。")
    required_source_ids: list[str] = Field(
        default_factory=list,
        description="当前 step 必须具备的 source id。缺失时 bundle.ready=False。",
    )
    required_artifact_types: list[str] = Field(
        default_factory=list,
        description="当前 step 必须具备的 artifact type。缺失时 bundle.ready=False。",
    )
