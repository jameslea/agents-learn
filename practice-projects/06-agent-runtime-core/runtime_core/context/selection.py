from __future__ import annotations

from pydantic import BaseModel, Field

from runtime_core.context.source import ContextSourceType, ContextTrustLevel, ContextVisibility


class ContextSelection(BaseModel):
    """候选信息的一条选择日志。

    selection log 是 Context Builder 的可解释性基础。它记录候选为什么进入、
    为什么被排除，以及排除是否因为预算、信任、敏感、过期或不相关。
    """

    source_type: ContextSourceType = Field(description="候选来源类型。")
    source_id: str = Field(description="候选来源标识。")
    included: bool = Field(description="该候选是否最终进入 ContextBundle.items。")
    reason: str = Field(description="进入或排除原因，供调试、复盘和测试断言使用。")
    score: float = Field(default=0.0, description="简单相关性分数，目前主要来自 tag overlap。")
    tags: list[str] = Field(default_factory=list, description="候选标签。")
    visibility: ContextVisibility = Field(default=ContextVisibility.LLM_VISIBLE, description="候选可见性。")
    trust_level: ContextTrustLevel = Field(default=ContextTrustLevel.SYSTEM, description="候选信任等级。")
    sensitive: bool = Field(default=False, description="候选是否被标记为敏感。")

class ContextMetrics(BaseModel):
    """一次上下文构造的观测指标。

    Metrics 让上下文工程可以被观察和测试，而不是只看最终 prompt。
    后续可以进入 trace，用于复盘上下文变化对结果的影响。
    """

    total_chars: int = Field(default=0, description="估算上下文字符数。")
    item_count: int = Field(default=0, description="最终进入 ContextBundle.items 的数量。")
    included_count: int = Field(default=0, description="selection_log 中 included=True 的数量。")
    excluded_count: int = Field(default=0, description="selection_log 中 included=False 的数量。")
    source_type_breakdown: dict[str, int] = Field(default_factory=dict, description="按 source_type 统计进入项数量。")
    budget_used_ratio: float = Field(default=0.0, description="字符预算使用比例。")
    sensitive_excluded_count: int = Field(default=0, description="因 sensitive 被排除的候选数量。")
    untrusted_excluded_count: int = Field(default=0, description="因 untrusted 被排除的候选数量。")
    missing_required_count: int = Field(default=0, description="缺失 required context 的数量。")
