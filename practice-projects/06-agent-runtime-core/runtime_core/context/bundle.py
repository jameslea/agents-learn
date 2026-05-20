from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from runtime_core.context.selection import ContextMetrics, ContextSelection
from runtime_core.context.source import ContextSourceType, ContextTrustLevel, ContextVisibility


class ContextItem(BaseModel):
    """最终进入 ContextBundle 的一条上下文内容。

    ContextItem 是已经通过策略筛选、预算裁剪和安全检查的信息。通常会被
    `to_prompt_sections()` 渲染为模型可见上下文。
    """

    source_type: ContextSourceType = Field(description="上下文来源类型。")
    source_id: str = Field(description="来源标识，例如 artifact id、memory id 或 step id。")
    title: str = Field(description="上下文片段标题，用于 prompt section 或调试输出。")
    content: str = Field(description="进入上下文的正文或摘要。")
    visibility: ContextVisibility = Field(
        default=ContextVisibility.LLM_VISIBLE,
        description="可见性。用于区分完整可见、仅摘要可见和 Runtime-only。",
    )
    trust_level: ContextTrustLevel = Field(
        default=ContextTrustLevel.SYSTEM,
        description="信任等级。用于判断外部或不可信内容是否能进入模型上下文。",
    )
    sensitive: bool = Field(default=False, description="是否包含敏感信息。默认策略会排除敏感候选。")
    metadata: dict[str, Any] = Field(default_factory=dict, description="来源相关扩展元数据。")

class ContextBundle(BaseModel):
    """当前 step 的结构化上下文包。

    ContextBundle 是 ContextBuilder 的主要输出。它同时包含模型可见内容、
    选择日志、指标和 required context 检查结果。
    """

    task_id: str = Field(description="任务 ID。")
    task_type: str = Field(description="任务类型。")
    step_id: str = Field(description="当前 step id。")
    goal: str = Field(description="任务目标。")
    current_step: str = Field(description="当前 step 描述。")
    items: list[ContextItem] = Field(default_factory=list, description="最终进入上下文的条目。")
    selection_log: list[ContextSelection] = Field(default_factory=list, description="候选选择日志。")
    metrics: ContextMetrics = Field(default_factory=ContextMetrics, description="上下文构造指标。")
    estimated_chars: int = Field(default=0, description="估算上下文字符数。")
    excluded_count: int = Field(default=0, description="被排除的候选数量。")
    ready: bool = Field(default=True, description="required context 是否满足。False 表示当前 step 不应继续。")
    missing_required_context: list[str] = Field(default_factory=list, description="缺失的 required source 或 artifact type。")
    blocked_reason: str = Field(default="", description="ready=False 时的阻塞原因。")

    def to_prompt_sections(self) -> list[str]:
        """将结构化上下文渲染为稳定的 prompt section。"""
        sections = [
            f"# Goal\n{self.goal}",
            f"# Current Step\n{self.current_step}",
        ]
        for item in self.items:
            sections.append(f"# {item.title}\n{item.content}")
        return sections
